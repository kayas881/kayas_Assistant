"""
Fine-tune Qwen2-VL-2B for Windows UI Understanding
Optimized for local/Camber GPU training
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime

import torch
from torch.utils.data import Dataset, DataLoader, random_split
from torch.nn import CrossEntropyLoss
from PIL import Image

from transformers import (
    Qwen2VLForConditionalGeneration,
    AutoProcessor,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths
DATA_DIR = Path("training_data_auto")  # Your local dataset folder
OUTPUT_DIR = Path("ui_model_finetuned")  # Where to save the model
MERGED_OUTPUT_DIR = Path("ui_model_merged")  # Merged model export

# Model settings
MODEL_NAME = "Qwen/Qwen2-VL-2B-Instruct"
BATCH_SIZE = 2  # Adjust based on your GPU memory (2-4 for 16GB GPU)
GRADIENT_ACCUMULATION_STEPS = 8  # Effective batch size = BATCH_SIZE * this
NUM_EPOCHS = 3
LEARNING_RATE = 2e-4

# Hardware settings
USE_4BIT = True  # Set to False if you have 24GB+ VRAM
USE_FP16 = torch.cuda.is_available()  # Use mixed precision if GPU available

print("="*70)
print("  Fine-tuning Qwen2-VL-2B for Windows UI Understanding")
print("="*70)
print(f"📂 Data directory: {DATA_DIR}")
print(f"💾 Output directory: {OUTPUT_DIR}")
print(f"🎯 Model: {MODEL_NAME}")
print(f"🔢 Batch size: {BATCH_SIZE} (effective: {BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS})")
print(f"📊 Epochs: {NUM_EPOCHS}")
print(f"⚡ Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
print("="*70 + "\n")

# ============================================================================
# DATASET CLASS
# ============================================================================

class UIDataset(Dataset):
    """Custom dataset for UI screenshots with element detection"""

    def __init__(self, data_dir, processor, max_samples=None):
        self.data_dir = Path(data_dir)
        self.processor = processor

        # Load training data from dataset.json
        dataset_path = self.data_dir / 'dataset.json'
        print(f"📚 Loading dataset from {dataset_path}...")
        
        with open(dataset_path) as f:
            data = json.load(f)

        self.samples = data.get('samples', [])

        if max_samples:
            self.samples = self.samples[:max_samples]

        print(f"✅ Loaded {len(self.samples):,} samples from dataset.json\n")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]

        # Load image
        img_filename = sample.get('screenshot', f"frame_{idx:06d}.png")
        img_path = self.data_dir / img_filename

        if not img_path.exists():
            raise FileNotFoundError(f"Screenshot not found: {img_path}")

        image = Image.open(img_path).convert('RGB')

        # Get UI elements
        elements = sample.get('elements', [])

        # Create training prompt
        if len(elements) > 0:
            element_list = []
            for e in elements[:15]:
                elem_type = e.get('type', 'Control')
                elem_name = e.get('name', '')

                if elem_name:
                    elem_desc = f"{elem_type} '{elem_name}'"
                else:
                    elem_desc = elem_type

                bbox = e.get('bbox', [])
                if bbox:
                    elem_desc += f" at [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]"

                element_list.append(elem_desc)

            instruction = "Describe the UI elements visible in this Windows interface."
            response = f"This interface contains {len(elements)} UI elements. "
            response += f"Key elements include: {'; '.join(element_list[:10])}."

        else:
            instruction = "What do you see in this Windows interface?"
            response = f"This is a Windows interface screenshot showing various UI controls."

        # Format as conversation
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": instruction}
                ]
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": response}]
            }
        ]

        # Process with model processor
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )

        inputs = self.processor(
            text=[text],
            images=[image],
            padding=True,
            return_tensors="pt"
        )

        # Create labels
        input_ids = inputs['input_ids'].squeeze(0)
        labels = input_ids.clone()

        # Mask user prompt (only train on assistant response)
        assistant_start = text.find("assistant\n")
        if assistant_start != -1:
            prompt_text = text[:assistant_start + len("assistant\n")]
            prompt_tokens = self.processor.tokenizer(prompt_text, return_tensors="pt")['input_ids']
            prompt_len = prompt_tokens.shape[1]
            labels[:prompt_len] = -100

        # Return batch
        result = {k: v.squeeze(0) for k, v in inputs.items()}
        result['labels'] = labels

        return result


# ============================================================================
# CUSTOM TRAINER (with manual loss computation)
# ============================================================================

class CustomTrainer(Trainer):
    """Custom trainer to handle Qwen2-VL loss computation"""
    
    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs.get("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")

        loss = None
        if logits is not None and labels is not None:
            loss_fct = CrossEntropyLoss()
            
            # Shift for causal LM
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            
            shift_logits = shift_logits.view(-1, model.config.vocab_size)
            shift_labels = shift_labels.view(-1)
            shift_labels = shift_labels.to(shift_logits.device)
            
            loss = loss_fct(shift_logits, shift_labels)

        if loss is None:
            raise ValueError("Could not compute loss. Logits or labels were None.")

        return (loss, outputs) if return_outputs else loss


# ============================================================================
# MAIN TRAINING FUNCTION
# ============================================================================

def main():
    # Create output directories
    OUTPUT_DIR.mkdir(exist_ok=True)
    MERGED_OUTPUT_DIR.mkdir(exist_ok=True)

    # Check GPU
    if not torch.cuda.is_available():
        print("⚠️  WARNING: No GPU detected! Training will be very slow on CPU.")
        print("   Consider using a GPU for fine-tuning.\n")
    else:
        print(f"✅ GPU detected: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB\n")

    # ========================================================================
    # Load Model
    # ========================================================================
    
    print(f"📥 Loading model: {MODEL_NAME}...\n")

    if USE_4BIT:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    else:
        bnb_config = None

    model = Qwen2VLForConditionalGeneration.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )

    processor = AutoProcessor.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True
    )

    # Prepare for LoRA
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    
    print(f"✅ Model loaded!")
    print(f"📊 Trainable parameters: {trainable_params:,} ({trainable_params/total_params*100:.2f}%)")
    print(f"💾 Memory: ~{torch.cuda.memory_allocated()/1e9:.2f} GB\n")

    # ========================================================================
    # Prepare Dataset
    # ========================================================================

    print("📚 Creating datasets...\n")
    full_dataset = UIDataset(DATA_DIR, processor)

    train_size = int(0.9 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])

    print(f"✅ Train samples: {len(train_dataset):,}")
    print(f"✅ Validation samples: {len(val_dataset):,}\n")

    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=processor.tokenizer,
        model=model,
        padding=True
    )

    # ========================================================================
    # Training Configuration
    # ========================================================================

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=LEARNING_RATE,
        warmup_steps=100,
        logging_steps=50,
        save_steps=500,
        eval_steps=500,
        save_total_limit=3,
        eval_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=USE_FP16,
        optim="paged_adamw_8bit" if USE_4BIT else "adamw_torch",
        report_to="none",
        push_to_hub=False,
        remove_unused_columns=False,
        dataloader_num_workers=2,
    )

    print("⚙️  Training configuration:")
    print(f"   Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS}")
    print(f"   Total epochs: {NUM_EPOCHS}")
    print(f"   Learning rate: {LEARNING_RATE}")
    print(f"   Total steps: {len(train_dataset) // (BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS) * NUM_EPOCHS}\n")

    # ========================================================================
    # Create Trainer and Train
    # ========================================================================

    trainer = CustomTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
    )

    print("\n" + "="*70)
    print(" "*20 + "🚀 STARTING TRAINING")
    print("="*70 + "\n")

    start_time = time.time()

    # Train!
    trainer.train()

    elapsed = time.time() - start_time
    print(f"\n✅ Training complete! Time: {elapsed/3600:.2f} hours")

    # ========================================================================
    # Save Models
    # ========================================================================

    print("\n💾 Saving final model...")
    trainer.save_model(str(OUTPUT_DIR / "final"))
    processor.save_pretrained(str(OUTPUT_DIR / "final"))
    print(f"✅ LoRA model saved to: {OUTPUT_DIR / 'final'}")

    # Merge and save
    print("\n🔄 Merging LoRA weights...")
    merged_model = model.merge_and_unload()
    merged_model.save_pretrained(str(MERGED_OUTPUT_DIR))
    processor.save_pretrained(str(MERGED_OUTPUT_DIR))
    print(f"✅ Merged model saved to: {MERGED_OUTPUT_DIR}")

    print("\n" + "="*70)
    print("🎉 TRAINING COMPLETE!")
    print("="*70)
    print(f"\n📊 Training Summary:")
    print(f"   Duration: {elapsed/3600:.2f} hours")
    print(f"   Samples processed: {len(train_dataset):,}")
    print(f"   Model location: {MERGED_OUTPUT_DIR}")
    print(f"\n💡 Next steps:")
    print(f"   1. Test the model with inference script")
    print(f"   2. Integrate into your voice assistant")
    print(f"   3. Collect more data if needed\n")


if __name__ == "__main__":
    main()
