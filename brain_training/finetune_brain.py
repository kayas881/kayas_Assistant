"""
Fine-tune Mistral 7B or Llama 3 8B as an Action Planner (AI Brain).

This script:
1. Loads training data (user commands → tool calls)
2. Fine-tunes a small LLM with QLoRA (4-bit quantization)
3. Teaches the model to be an expert "Tool User"

GPU Requirements: L4 24GB (2-3 hours training)
Local Inference: Will run on RTX 3050 after training
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer


# ==================== CONFIGURATION ====================
CONFIG = {
    # Model selection (choose one)
    "model_name": "mistralai/Mistral-7B-Instruct-v0.2",  # or "meta-llama/Meta-Llama-3-8B-Instruct"
    
    # Data - ENHANCED MEGA DATASET (8000 high-quality examples)
    "train_data_path": Path(__file__).parent / "training_data" / "mega_brain_dataset_10000_enhanced.jsonl",
    "val_split": 0.1,  # 10% for validation
    
    # Training (optimized for L4 24GB with large dataset)
    "batch_size": 4,  # Increased for larger dataset
    "gradient_accumulation_steps": 4,  # Effective batch = 16
    "num_epochs": 3,
    "learning_rate": 2e-4,
    "max_seq_length": 2048,  # Tool calls are short
    
    # QLoRA settings
    "lora_r": 16,  # LoRA rank
    "lora_alpha": 32,  # LoRA alpha
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    
    # Output
    "output_dir": Path(__file__).parent / "models" / "kayas_brain",
    "save_steps": 100,
    "logging_steps": 10,
}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load JSONL file (one JSON per line)"""
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line.strip()))
    return data


def format_chat_for_training(example: Dict[str, Any], tokenizer) -> str:
    """
    Convert chat messages to training format.
    
    Uses the model's chat template (e.g., Mistral format):
    <s>[INST] system_prompt + user_message [/INST] assistant_response</s>
    """
    messages = example["messages"]
    
    # Apply tokenizer's chat template
    formatted = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False
    )
    
    return formatted


def prepare_dataset(data_path: Path, tokenizer, val_split: float = 0.1):
    """Load and prepare dataset for training"""
    
    print(f"📂 Loading data from {data_path}...")
    raw_data = load_jsonl(data_path)
    print(f"   Loaded {len(raw_data)} examples")
    
    # Format for training
    formatted_texts = []
    for example in raw_data:
        text = format_chat_for_training(example, tokenizer)
        formatted_texts.append({"text": text})
    
    # Create dataset
    dataset = Dataset.from_list(formatted_texts)
    
    # Split into train/val
    split = dataset.train_test_split(test_size=val_split, seed=42)
    train_dataset = split["train"]
    val_dataset = split["test"]
    
    print(f"   Train: {len(train_dataset)} examples")
    print(f"   Val: {len(val_dataset)} examples")
    
    return train_dataset, val_dataset


def setup_model_and_tokenizer(model_name: str):
    """Load model with QLoRA (4-bit quantization)"""
    
    print(f"🤖 Loading model: {model_name}")
    
    # Quantization config (4-bit)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16,
        bnb_4bit_use_double_quant=True,  # Nested quantization for more memory savings
    )
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"  # Important for decoder-only models
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    
    # Prepare for k-bit training
    model = prepare_model_for_kbit_training(model)
    
    print(f"✅ Model loaded in 4-bit")
    print(f"   Parameters: {model.num_parameters() / 1e9:.2f}B")
    
    return model, tokenizer


def setup_lora(model, config: Dict):
    """Setup LoRA adapters"""
    
    print("🔧 Setting up LoRA adapters...")
    
    lora_config = LoraConfig(
        r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        lora_dropout=config["lora_dropout"],
        target_modules=config["target_modules"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    model = get_peft_model(model, lora_config)
    
    # Print trainable parameters
    trainable, total = model.get_nb_trainable_parameters()
    print(f"✅ LoRA configured")
    print(f"   Trainable params: {trainable:,} ({100 * trainable / total:.2f}%)")
    
    return model


def train(config: Dict):
    """Main training function"""
    
    print("=" * 80)
    print("🧠 KAYAS AI BRAIN TRAINING")
    print("=" * 80)
    print(f"\n📋 Configuration:")
    for key, value in config.items():
        if not isinstance(value, (list, dict)):
            print(f"   {key}: {value}")
    print()
    
    # Setup
    model, tokenizer = setup_model_and_tokenizer(config["model_name"])
    model = setup_lora(model, config)
    
    # Load data
    train_dataset, val_dataset = prepare_dataset(
        config["train_data_path"],
        tokenizer,
        config["val_split"]
    )
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(config["output_dir"]),
        num_train_epochs=config["num_epochs"],
        per_device_train_batch_size=config["batch_size"],
        per_device_eval_batch_size=config["batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation_steps"],
        learning_rate=config["learning_rate"],
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        logging_steps=config["logging_steps"],
        save_strategy="steps",
        save_steps=config["save_steps"],
        eval_strategy="steps",
        eval_steps=config["save_steps"],
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=torch.cuda.is_available() and not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        optim="paged_adamw_8bit",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        report_to="none",
        remove_unused_columns=True,
        dataloader_num_workers=4,
        dataloader_pin_memory=True,
    )
    
    print(f"\n⚙️ Training configuration:")
    print(f"   Effective batch size: {config['batch_size'] * config['gradient_accumulation_steps']}")
    print(f"   Total steps: {len(train_dataset) // (config['batch_size'] * config['gradient_accumulation_steps']) * config['num_epochs']}")
    print(f"   Estimated time: ~2-3 hours on L4 24GB")
    print()
    
    # Trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=config["max_seq_length"],
        packing=False,  # Don't pack sequences (keep tool calls intact)
    )
    
    # Train!
    print("🚀 Starting training...")
    print("=" * 80)
    
    try:
        trainer.train()
        
        print("\n" + "=" * 80)
        print("✅ Training complete!")
        
        # Save final model
        final_path = config["output_dir"] / "final"
        trainer.save_model(str(final_path))
        tokenizer.save_pretrained(str(final_path))
        
        print(f"💾 Model saved to: {final_path}")
        print("\n📊 Training metrics:")
        print(f"   Final train loss: {trainer.state.log_history[-2].get('loss', 'N/A')}")
        print(f"   Final eval loss: {trainer.state.log_history[-1].get('eval_loss', 'N/A')}")
        
        print("\n🎉 Your AI Brain is ready!")
        print(f"\n💡 Next steps:")
        print(f"   1. Test the model: python test_brain.py")
        print(f"   2. Copy to local machine (RTX 3050)")
        print(f"   3. Integrate with your assistant")
        
    except KeyboardInterrupt:
        print("\n⚠️ Training interrupted by user")
        print(f"💾 Saving checkpoint...")
        trainer.save_model(str(config["output_dir"] / "interrupted"))
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        raise
    
    finally:
        # Cleanup
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print(f"\n🧹 GPU memory cleared")


if __name__ == "__main__":
    # Check CUDA
    if not torch.cuda.is_available():
        print("⚠️ WARNING: No GPU detected. Training will be extremely slow.")
        print("   This script is designed for GPU training (L4 24GB recommended)")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            exit(0)
    else:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"🎮 GPU detected: {gpu_name} ({gpu_memory:.1f} GB)")
    
    # Check if training data exists
    if not CONFIG["train_data_path"].exists():
        print(f"❌ Training data not found: {CONFIG['train_data_path']}")
        print("   Run: python generate_training_data.py")
        exit(1)
    
    # Start training
    train(CONFIG)
