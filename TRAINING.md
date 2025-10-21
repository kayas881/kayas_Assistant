# Preference Model Training Workflow

The preference model learns what makes a "good" vs "bad" plan based on your feedback. Here's how to train and use it:

## How Training Works

1. **Data Collection**: Every time you run the agent, it logs the plan prompt and output to SQLite
2. **Feedback**: You provide feedback via `/feedback` API or CLI scripts  
3. **Training**: The model learns from feedback tags/keywords:
   - Positive: `pos`, `good`, `great`, `+1`, `accept`, `helpful`, `correct`
   - Negative: `neg`, `bad`, `wrong`, `worse`, `-1`, `reject`, `not good`
4. **Usage**: Trained model scores new plans and helps pick better actions

## Training Commands

### Option 1: CLI Script (Recommended)
```powershell
# Basic training with default settings
C:/Users/KAYAS/Desktop/kayasWorkPlace/kayas/.venv/Scripts/python.exe scripts/train_preference.py

# Custom training parameters
C:/Users/KAYAS/Desktop/kayasWorkPlace/kayas/.venv/Scripts/python.exe scripts/train_preference.py --epochs 5 --vocab-size 4000 --lr 0.05
```

### Option 2: API (if server is running)
```powershell
# Start API server
C:/Users/KAYAS/Desktop/kayasWorkPlace/kayas/.venv/Scripts/python.exe -m uvicorn src.server.api:app --reload --port 8000

# Train via API
curl -X POST http://localhost:8000/training/preference/train -H "Content-Type: application/json" -d "{\"epochs\": 5, \"max_vocab\": 4000, \"lr\": 0.05}"
```

## Providing Feedback

### Method 1: CLI Script
```powershell
# Submit positive feedback
C:/Users/KAYAS/Desktop/kayasWorkPlace/kayas/.venv/Scripts/python.exe scripts/submit_feedback.py "run-id-here" "Great plan, worked perfectly" --tags "pos"

# Submit negative feedback  
C:/Users/KAYAS/Desktop/kayasWorkPlace/kayas/.venv/Scripts/python.exe scripts/submit_feedback.py "run-id-here" "Too many steps, should be simpler" --tags "neg"
```

### Method 2: API
```powershell
curl -X POST http://localhost:8000/feedback -H "Content-Type: application/json" -d "{\"run_id\": \"your-run-id\", \"feedback\": \"Good plan\", \"tags\": \"pos\"}"
```

## How the Model is Used

1. **In ReAct Mode**: Scores candidate actions per step and picks the best ones (beam search)
2. **In Structured Mode**: Scores the initial plan; if low score and strong model available, tries alternative and picks better one
3. **Export Training Data**: Generate JSONL datasets for fine-tuning larger models

## Files Created

- `.agent/preference_model.json` - Trained model weights and vocabulary
- `.agent/agent.db` - SQLite database with plans and feedback
- `.agent/datasets/` - Exported training datasets (JSONL format)

## Example Workflow

1. Run some agent tasks:
```powershell
C:/Users/KAYAS/Desktop/kayasWorkPlace/kayas/.venv/Scripts/python.exe -m src.agent.main "Summarize https://example.com"
```

2. Note the run ID from output, provide feedback:
```powershell
C:/Users/KAYAS/Desktop/kayasWorkPlace/kayas/.venv/Scripts/python.exe scripts/submit_feedback.py "abc-123-def" "Perfect summary, great job" --tags "pos"
```

3. Train the model:
```powershell
C:/Users/KAYAS/Desktop/kayasWorkPlace/kayas/.venv/Scripts/python.exe scripts/train_preference.py
```

4. Future runs will use the trained model to make better decisions automatically.

## Advanced: Auto-Training

The system can auto-train periodically when enough new feedback accumulates. This is not implemented yet but would trigger training every N feedback items.