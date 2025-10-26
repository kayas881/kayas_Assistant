import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel, AdamW, get_linear_schedule_with_warmup
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import numpy as np
import os
from datetime import datetime
import pickle

print("🚀 Starting Jarvis AI Training Pipeline...")
print(f"📅 Training started at: {datetime.now()}")
print(f"🔧 PyTorch version: {torch.__version__}")
print(f"🎮 CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"🎮 GPU device: {torch.cuda.get_device_name(0)}")
    print(f"🎮 GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# Load dataset
print("\n📊 Loading dataset...")
with open('~/mega_brain_dataset_8000.jsonl', 'r') as f:
    data = [json.loads(line) for line in f]

print(f"📊 Loaded {len(data)} training examples")

# Extract features
texts = []
intents = []
tools = []

for item in data:
    texts.append(item['text'])
    intents.append(item['intent'])
    tools.append(item['tool'])

print(f"📊 Unique intents: {len(set(intents))}")
print(f"📊 Unique tools: {len(set(tools))}")

# Encode labels
intent_encoder = LabelEncoder()
tool_encoder = LabelEncoder()

intent_labels = intent_encoder.fit_transform(intents)
tool_labels = tool_encoder.fit_transform(tools)

print(f"📊 Intent classes: {len(intent_encoder.classes_)}")
print(f"📊 Tool classes: {len(tool_encoder.classes_)}")

# Initialize tokenizer and model
print("\n🤖 Loading BERT model...")
model_name = "distilbert-base-uncased"  # Faster than full BERT
tokenizer = AutoTokenizer.from_pretrained(model_name)
bert_model = AutoModel.from_pretrained(model_name)

class JarvisDataset(Dataset):
    def __init__(self, texts, intent_labels, tool_labels, tokenizer, max_length=128):
        self.texts = texts
        self.intent_labels = intent_labels
        self.tool_labels = tool_labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'intent_label': torch.tensor(self.intent_labels[idx], dtype=torch.long),
            'tool_label': torch.tensor(self.tool_labels[idx], dtype=torch.long)
        }

class JarvisModel(nn.Module):
    def __init__(self, bert_model, num_intents, num_tools, dropout=0.3):
        super(JarvisModel, self).__init__()
        self.bert = bert_model
        self.dropout = nn.Dropout(dropout)
        
        # Intent classifier
        self.intent_classifier = nn.Linear(bert_model.config.hidden_size, num_intents)
        
        # Tool selector
        self.tool_classifier = nn.Linear(bert_model.config.hidden_size, num_tools)
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.pooler_output
        pooled_output = self.dropout(pooled_output)
        
        intent_logits = self.intent_classifier(pooled_output)
        tool_logits = self.tool_classifier(pooled_output)
        
        return intent_logits, tool_logits

# Split data
print("\n📊 Splitting dataset...")
X_train, X_val, y_intent_train, y_intent_val, y_tool_train, y_tool_val = train_test_split(
    texts, intent_labels, tool_labels, test_size=0.2, random_state=42, stratify=intent_labels
)

print(f"📊 Training samples: {len(X_train)}")
print(f"📊 Validation samples: {len(X_val)}")

# Create datasets
train_dataset = JarvisDataset(X_train, y_intent_train, y_tool_train, tokenizer)
val_dataset = JarvisDataset(X_val, y_intent_val, y_tool_val, tokenizer)

# Create data loaders
batch_size = 16  # Optimized for GPU memory
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=batch_size)

print(f"📊 Training batches: {len(train_loader)}")
print(f"📊 Validation batches: {len(val_loader)}")

# Initialize model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"\n🎮 Using device: {device}")

model = JarvisModel(
    bert_model=bert_model,
    num_intents=len(intent_encoder.classes_),
    num_tools=len(tool_encoder.classes_)
).to(device)

# Training parameters (optimized for 6-hour limit)
epochs = 3  # Reduced for time constraint
learning_rate = 2e-5
warmup_steps = 100

optimizer = AdamW(model.parameters(), lr=learning_rate)
total_steps = len(train_loader) * epochs
scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=warmup_steps,
    num_training_steps=total_steps
)

criterion = nn.CrossEntropyLoss()

print(f"\n🎯 Training Configuration:")
print(f"🎯 Epochs: {epochs}")
print(f"🎯 Batch size: {batch_size}")
print(f"🎯 Learning rate: {learning_rate}")
print(f"🎯 Total steps: {total_steps}")

# Training loop
print("\n🚀 Starting training...")
model.train()

for epoch in range(epochs):
    print(f"\n📈 Epoch {epoch + 1}/{epochs}")
    total_loss = 0
    correct_intents = 0
    correct_tools = 0
    total_samples = 0
    
    for batch_idx, batch in enumerate(train_loader):
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        intent_labels = batch['intent_label'].to(device)
        tool_labels = batch['tool_label'].to(device)
        
        optimizer.zero_grad()
        
        intent_logits, tool_logits = model(input_ids, attention_mask)
        
        intent_loss = criterion(intent_logits, intent_labels)
        tool_loss = criterion(tool_logits, tool_labels)
        total_loss_batch = intent_loss + tool_loss
        
        total_loss_batch.backward()
        optimizer.step()
        scheduler.step()
        
        total_loss += total_loss_batch.item()
        
        # Calculate accuracy
        intent_preds = torch.argmax(intent_logits, dim=1)
        tool_preds = torch.argmax(tool_logits, dim=1)
        
        correct_intents += (intent_preds == intent_labels).sum().item()
        correct_tools += (tool_preds == tool_labels).sum().item()
        total_samples += intent_labels.size(0)
        
        if batch_idx % 50 == 0:
            print(f"📊 Batch {batch_idx}/{len(train_loader)} - Loss: {total_loss_batch.item():.4f}")
    
    avg_loss = total_loss / len(train_loader)
    intent_acc = correct_intents / total_samples
    tool_acc = correct_tools / total_samples
    
    print(f"📈 Epoch {epoch + 1} Results:")
    print(f"📈 Average Loss: {avg_loss:.4f}")
    print(f"📈 Intent Accuracy: {intent_acc:.4f}")
    print(f"📈 Tool Accuracy: {tool_acc:.4f}")

# Validation
print("\n🔍 Running validation...")
model.eval()
val_loss = 0
val_correct_intents = 0
val_correct_tools = 0
val_total = 0

with torch.no_grad():
    for batch in val_loader:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        intent_labels = batch['intent_label'].to(device)
        tool_labels = batch['tool_label'].to(device)
        
        intent_logits, tool_logits = model(input_ids, attention_mask)
        
        intent_loss = criterion(intent_logits, intent_labels)
        tool_loss = criterion(tool_logits, tool_labels)
        val_loss += (intent_loss + tool_loss).item()
        
        intent_preds = torch.argmax(intent_logits, dim=1)
        tool_preds = torch.argmax(tool_logits, dim=1)
        
        val_correct_intents += (intent_preds == intent_labels).sum().item()
        val_correct_tools += (tool_preds == tool_labels).sum().item()
        val_total += intent_labels.size(0)

val_intent_acc = val_correct_intents / val_total
val_tool_acc = val_correct_tools / val_total

print(f"\n🎯 Validation Results:")
print(f"🎯 Intent Accuracy: {val_intent_acc:.4f}")
print(f"🎯 Tool Accuracy: {val_tool_acc:.4f}")

# Save models and encoders
print("\n💾 Saving trained models...")
os.makedirs('./outputs', exist_ok=True)

# Save model
torch.save(model.state_dict(), './outputs/jarvis_model.pth')

# Save tokenizer
tokenizer.save_pretrained('./outputs/jarvis_tokenizer')

# Save encoders
with open('./outputs/intent_encoder.pkl', 'wb') as f:
    pickle.dump(intent_encoder, f)

with open('./outputs/tool_encoder.pkl', 'wb') as f:
    pickle.dump(tool_encoder, f)

# Save model config
config = {
    'model_name': model_name,
    'num_intents': len(intent_encoder.classes_),
    'num_tools': len(tool_encoder.classes_),
    'intent_classes': intent_encoder.classes_.tolist(),
    'tool_classes': tool_encoder.classes_.tolist(),
    'max_length': 128,
    'final_intent_accuracy': val_intent_acc,
    'final_tool_accuracy': val_tool_acc
}

with open('./outputs/model_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print(f"\n✅ Training completed successfully!")
print(f"✅ Final Intent Accuracy: {val_intent_acc:.4f}")
print(f"✅ Final Tool Accuracy: {val_tool_acc:.4f}")
print(f"✅ Models saved to ./outputs/")
print(f"✅ Training finished at: {datetime.now()}")

# Test inference
print("\n🧪 Testing inference...")
test_texts = [
    "Send a message to John",
    "What's the weather like today?",
    "Play some music",
    "Set a reminder for 3 PM"
]

model.eval()
with torch.no_grad():
    for text in test_texts:
        encoding = tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=128,
            return_tensors='pt'
        ).to(device)
        
        intent_logits, tool_logits = model(
            encoding['input_ids'],
            encoding['attention_mask']
        )
        
        intent_pred = torch.argmax(intent_logits, dim=1).cpu().numpy()[0]
        tool_pred = torch.argmax(tool_logits, dim=1).cpu().numpy()[0]
        
        intent_name = intent_encoder.inverse_transform([intent_pred])[0]
        tool_name = tool_encoder.inverse_transform([tool_pred])[0]
        
        print(f"🧪 '{text}' -> Intent: {intent_name}, Tool: {tool_name}")

print("\n🎉 Jarvis AI training pipeline completed successfully!")