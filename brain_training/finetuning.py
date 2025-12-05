#!/usr/bin/env python
import os
import subprocess
import sys
import time

# ================== INSTALL DEPENDENCIES ==================
REQUIRED_PACKAGES = [
    "transformers>=4.45.0",
    "datasets",
    "peft>=0.11.0",
    "accelerate",
    "bitsandbytes",
    "sentencepiece",
    "protobuf<5"
]

def install_packages():
    print("🔧 Checking and installing required packages...")
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-U",
    ] + REQUIRED_PACKAGES
    subprocess.check_call(cmd)
    print("✅ Dependencies installed\n")

install_packages()

# ================== IMPORTS ==================
import gc
import torch
from dataclasses import dataclass
from typing import Dict, List
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training

# ================== ENVIRONMENT ==================
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

# ================== CONFIG ==================
BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DATA_PATH = "mega_brain_dataset_20k.jsonl"  # change if needed
OUTPUT_DIR = "./kayas_qwen_simple"
NUM_EPOCHS = 2  # ← change to 2 or 4 if you want

# ================== MODEL & TOKENIZER ==================
def load_model_and_tokenizer():
    print("📦 Loading base model and tokenizer...")
    bnb_cfg = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_cfg,
        dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )

    model.gradient_checkpointing_enable()
    print("✅ Qwen2.5-3B loaded in 4-bit mode")
    return model, tokenizer

# ================== LORA SETUP ==================
def apply_lora(model):
    lora_cfg = LoraConfig(
        r=32,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.1,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()
    return model

# ================== DATA ==================
def load_and_tokenize_data(tokenizer):
    print(f"📂 Loading dataset from: {DATA_PATH}")
    data = load_dataset("json", data_files=DATA_PATH)["train"]

    def tok_fn(batch):
        texts = []
        for msgs in batch["messages"]:
            try:
                formatted = tokenizer.apply_chat_template(
                    msgs,
                    tokenize=False,
                    add_generation_prompt=False,
                )
                texts.append(formatted)
            except Exception:
                system = msgs[0].get("content", "")
                user = msgs[1].get("content", "")
                assistant = msgs[-1].get("content", "")
                text = (
                    f"<|im_start|>system\n{system}<|im_end|>\n"
                    f"<|im_start|>user\n{user}<|im_end|>\n"
                    f"<|im_start|>assistant\n{assistant}<|im_end|>"
                )
                texts.append(text)
        return tokenizer(
            texts,
            truncation=True,
            max_length=1024,
            padding="max_length",
        )

    print("🧪 Tokenizing data...")
    tok_data = data.map(tok_fn, batched=True, remove_columns=data.column_names).shuffle(seed=42)
    print(f"✅ Tokenization complete: {tok_data.num_rows} examples")

    split = tok_data.train_test_split(test_size=0.05, seed=42)
    train_data = split["train"]
    eval_data = split["test"]
    print(f"📊 Train: {train_data.num_rows} | Eval: {eval_data.num_rows}")
    return train_data, eval_data

# ================== COLLATOR ==================
@dataclass
class CausalDataCollator:
    tokenizer: object
    padding: bool = True
    max_length: int = 1024

    def __call__(self, features: List[Dict[str, List[int]]]) -> Dict[str, torch.Tensor]:
        batch = self.tokenizer.pad(
            features,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        input_ids = batch["input_ids"]
        attention_mask = batch["attention_mask"]
        labels = input_ids.clone()
        labels[attention_mask == 0] = -100
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }

# ================== MAIN TRAINING ==================
def main():
    start_time = time.time()

    model, tokenizer = load_model_and_tokenizer()
    model = apply_lora(model)
    train_data, eval_data = load_and_tokenize_data(tokenizer)

    data_collator = CausalDataCollator(tokenizer, max_length=1024)

    train_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,
        num_train_epochs=NUM_EPOCHS,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        logging_steps=50,
        eval_strategy="steps",
        eval_steps=250,
        save_strategy="steps",
        save_steps=500,
        save_total_limit=2,
        load_best_model_at_end=False,
        fp16=True,
        optim="adamw_8bit",
        weight_decay=0.01,
        report_to="none",
        save_safetensors=True,
        dataloader_num_workers=2,
        remove_unused_columns=True,
    )

    trainer = Trainer(
        model=model,
        args=train_args,
        train_dataset=train_data,
        eval_dataset=eval_data,
        data_collator=data_collator,
        processing_class=tokenizer,
    )

    print(f"🚀 Starting training: Single GPU, {NUM_EPOCHS} epochs, 15k examples...")
    trainer.train()

    # ================== SAVE PROPERLY ==================
    print("\n💾 Saving final model...")
    final_path = os.path.join(OUTPUT_DIR, "final")
    os.makedirs(final_path, exist_ok=True)

    # Save LoRA adapters
    model.save_pretrained(final_path)
    tokenizer.save_pretrained(final_path)

    # Merge and save full model
    print("🔀 Merging LoRA into base model...")
    merged_model = model.merge_and_unload()
    merged_path = final_path + "_merged"
    os.makedirs(merged_path, exist_ok=True)
    merged_model.save_pretrained(merged_path, safe_serialization=True)
    tokenizer.save_pretrained(merged_path)

    elapsed = (time.time() - start_time) / 60
    print("✅ Training complete!")
    print(f"   LoRA adapters: {final_path}")
    print(f"   Merged model:  {merged_path}")
    print(f"⏱️ Total time: {elapsed:.1f} minutes")

if __name__ == "__main__":
    main()
