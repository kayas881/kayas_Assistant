# -*- coding: utf-8 -*-
"""
Kaggle Finetuning Script for Qwen2.5-3B-Instruct

This script is designed to run on Kaggle with free GPU.
It finetunes Qwen2.5-3B-Instruct on the distilled training data.

Steps:
1. Upload distilled_training_data.jsonl to Kaggle dataset
2. Create a new notebook and paste this script
3. Enable GPU (T4 x2 or P100)
4. Run!

Output: A finetuned model exported to GGUF format for local use with Ollama
"""

# ============================================================================
# INSTALL DEPENDENCIES (run this cell first on Kaggle)
# ============================================================================
"""
!pip install -q transformers datasets peft accelerate bitsandbytes trl
!pip install -q llama-cpp-python  # For GGUF export
"""

import os
import json
import torch
from pathlib import Path
from datasets import Dataset, load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

# ============================================================================
# CONFIGURATION
# ============================================================================

MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"  # Good balance of size and capability
OUTPUT_DIR = "./kayas-finetuned"
TRAINING_DATA = "/kaggle/input/kayas-training/distilled_training_data.jsonl"  # Update path

# Training hyperparameters (optimized for Kaggle T4 GPU)
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LEARNING_RATE = 2e-4
BATCH_SIZE = 4
GRADIENT_ACCUMULATION = 4
NUM_EPOCHS = 3
MAX_SEQ_LENGTH = 512


# ============================================================================
# LOAD AND PREPARE DATA
# ============================================================================

def load_training_data(path: str) -> Dataset:
    """Load the distilled training data."""
    examples = []
    
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))
    
    print(f"Loaded {len(examples)} training examples")
    return Dataset.from_list(examples)


def format_for_training(example: dict) -> dict:
    """Format example for instruction tuning."""
    
    # Qwen chat template format
    system_message = """You are Kayas, a helpful AI assistant that controls a Windows computer.
When the user makes a request, respond with a JSON object containing the tool to use and its arguments.
Be precise and extract exactly what the user specified."""
    
    instruction = example["instruction"]
    output = example["output"]
    
    # Format as chat
    text = f"""<|im_start|>system
{system_message}<|im_end|>
<|im_start|>user
{instruction}<|im_end|>
<|im_start|>assistant
{output}<|im_end|>"""
    
    return {"text": text}


# ============================================================================
# MODEL SETUP
# ============================================================================

def setup_model_and_tokenizer():
    """Load model with 4-bit quantization for training."""
    
    # 4-bit quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    
    # Prepare for training
    model = prepare_model_for_kbit_training(model)
    
    # LoRA config
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    return model, tokenizer


# ============================================================================
# TRAINING
# ============================================================================

def train(model, tokenizer, dataset):
    """Run finetuning."""
    
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION,
        learning_rate=LEARNING_RATE,
        weight_decay=0.01,
        warmup_ratio=0.03,
        logging_steps=10,
        save_strategy="epoch",
        fp16=True,
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        report_to="none",  # Disable wandb on Kaggle
    )
    
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_text_field="text",
    )
    
    print("\nStarting training...")
    trainer.train()
    
    # Save the final model
    trainer.save_model(f"{OUTPUT_DIR}/final")
    tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")
    
    print(f"\nModel saved to {OUTPUT_DIR}/final")
    return trainer


# ============================================================================
# EXPORT TO GGUF (for Ollama)
# ============================================================================

def merge_and_export_gguf(model, tokenizer):
    """Merge LoRA weights and export to GGUF format."""
    
    print("\nMerging LoRA weights...")
    
    # Merge LoRA into base model
    merged_model = model.merge_and_unload()
    
    # Save merged model
    merged_path = f"{OUTPUT_DIR}/merged"
    merged_model.save_pretrained(merged_path)
    tokenizer.save_pretrained(merged_path)
    
    print(f"Merged model saved to {merged_path}")
    
    # Convert to GGUF using llama.cpp
    # Note: This requires llama.cpp to be installed
    print("\nTo convert to GGUF for Ollama, run:")
    print(f"python llama.cpp/convert_hf_to_gguf.py {merged_path} --outtype q4_k_m --outfile kayas-3b-q4.gguf")
    
    return merged_path


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("KAYAS MODEL FINETUNING")
    print("=" * 70)
    print(f"Base model: {MODEL_NAME}")
    print(f"Training data: {TRAINING_DATA}")
    print()
    
    # Load data
    print("Loading training data...")
    dataset = load_training_data(TRAINING_DATA)
    dataset = dataset.map(format_for_training)
    
    print(f"Dataset size: {len(dataset)}")
    print(f"Sample: {dataset[0]['text'][:200]}...")
    print()
    
    # Setup model
    print("Loading model with 4-bit quantization...")
    model, tokenizer = setup_model_and_tokenizer()
    
    # Train
    trainer = train(model, tokenizer, dataset)
    
    # Export
    merged_path = merge_and_export_gguf(model, tokenizer)
    
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE!")
    print("=" * 70)
    print(f"\nNext steps:")
    print(f"1. Download the model from {merged_path}")
    print(f"2. Convert to GGUF format")
    print(f"3. Create Ollama modelfile and import")
    print(f"\nSee README for detailed instructions.")


if __name__ == "__main__":
    main()
