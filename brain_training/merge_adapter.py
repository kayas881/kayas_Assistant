"""
Merge LoRA adapter with base model for faster inference.
This creates a single merged model that doesn't need adapter loading.
"""
import argparse
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


def merge_adapter(
    base_model_name: str,
    adapter_path: str,
    output_path: str,
    push_to_hub: bool = False,
    hub_model_id: str = None,
):
    """
    Merge LoRA adapter with base model and save.
    
    Args:
        base_model_name: HF model name (e.g., "Qwen/Qwen2.5-3B-Instruct")
        adapter_path: Path to LoRA adapter folder
        output_path: Where to save merged model
        push_to_hub: Whether to push to HuggingFace Hub
        hub_model_id: HF Hub model ID if pushing
    """
    print(f"Loading base model: {base_model_name}")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float16,
        device_map="cpu",  # Load on CPU to avoid memory issues
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    
    print(f"Loading LoRA adapter from: {adapter_path}")
    model = PeftModel.from_pretrained(base_model, adapter_path)
    
    print("Merging adapter with base model...")
    merged_model = model.merge_and_unload()
    
    print(f"Saving merged model to: {output_path}")
    Path(output_path).mkdir(parents=True, exist_ok=True)
    merged_model.save_pretrained(output_path)
    
    print("Saving tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    tokenizer.save_pretrained(output_path)
    
    print("✅ Merge complete!")
    
    if push_to_hub:
        if not hub_model_id:
            raise ValueError("hub_model_id required when push_to_hub=True")
        
        print(f"Pushing to HuggingFace Hub: {hub_model_id}")
        merged_model.push_to_hub(hub_model_id)
        tokenizer.push_to_hub(hub_model_id)
        print("✅ Pushed to Hub!")
    
    return merged_model


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Merge LoRA adapter with base model")
    parser.add_argument(
        '--base-model',
        type=str,
        default='Qwen/Qwen2.5-3B-Instruct',
        help='Base model name from HuggingFace'
    )
    parser.add_argument(
        '--adapter-path',
        type=str,
        required=True,
        help='Path to LoRA adapter folder'
    )
    parser.add_argument(
        '--output-path',
        type=str,
        required=True,
        help='Where to save merged model'
    )
    parser.add_argument(
        '--push-to-hub',
        action='store_true',
        help='Push merged model to HuggingFace Hub'
    )
    parser.add_argument(
        '--hub-model-id',
        type=str,
        help='HuggingFace Hub model ID (required if --push-to-hub)'
    )
    
    args = parser.parse_args()
    
    merge_adapter(
        base_model_name=args.base_model,
        adapter_path=args.adapter_path,
        output_path=args.output_path,
        push_to_hub=args.push_to_hub,
        hub_model_id=args.hub_model_id,
    )
