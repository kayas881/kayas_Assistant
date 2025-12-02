# Phase 1: Robust Planner + Verifier

Multi-candidate planning with verification and automatic fallback for more reliable agent execution.

## Overview

The agent now generates **multiple candidate plans** for each goal, ranks them by confidence/risk, and executes them with **verification at each step**. If a plan fails, it automatically falls back to the next candidate.

## Key Features

### 1. Multi-Candidate Planning (`plan_candidates`)
- Generates k=3 candidate strategies:
  1. **Heuristic/Primary**: Fast, rule-based or LLM-generated primary plan
  2. **Alternative**: Creative approach with higher temperature (different tools/methods)
  3. **Conservative Fallback**: Safe filesystem-based plan (web fetch + file write)
- Each candidate includes:
  - `risk_score`: 0.0 (safe) to 1.0 (risky manual actions, CAPTCHA, etc.)
  - `step_count`: Number of actions
  - `estimated_time_sec`: Rough execution time estimate
  - `confidence`: Preference model score or heuristic confidence
  - `overall_score()`: Combined ranking metric (higher = better)

### 2. Execution Manager with Verification
- **Action Verification**: After each action, verifies the result:
  - Filesystem: File exists after creation
  - Web fetch: Content length > 10 chars, no 404
  - Browser: No failed steps
  - UI automation: Window/text found successfully
  - Process: Exit code == 0
- **Retry Logic**: Failed actions retry up to 2 times with exponential backoff (1s, 2s)
- **Plan Fallback**: If a plan fails, automatically tries the next candidate

### 3. Risk Assessment
Risk scores computed from tool usage:
- `browser.run_steps`: 0.3 (CAPTCHA risk)
- `process.kill_process`: 0.4 (dangerous)
- `filesystem.delete_file`: 0.3 (data loss risk)
- `desktop.run_steps`: 0.2 (manual UI fragility)
- Default: 0.05 per action

## Configuration

Enable in `.agent/profile.yaml`:
```yaml
planning:
  use_multi_candidate: true
  num_candidates: 3
  max_retries: 2
```

Or via environment variables:
```powershell
$env:USE_MULTI_CANDIDATE_PLANNING="1"
$env:NUM_PLAN_CANDIDATES="3"
$env:MAX_ACTION_RETRIES="2"
```

## Example Output

```
[Agent] Using multi-candidate planning (k=3)
[Planner] Generated 3 candidate plans:
  1. conservative_fallback: 2 steps, risk=0.10, conf=0.70, score=1.15
  2. llm_primary: 1 steps, risk=0.05, conf=0.00, score=-0.12
  3. llm_alternative: 2 steps, risk=0.10, conf=0.00, score=-0.25
[ExecutionManager] Executing 3 candidate plans with fallback
[ExecutionManager] Attempting plan 1/3: conservative_fallback
[ExecutionManager] Executing plan: conservative_fallback (2 steps)
[ExecutionManager] Step 1/2: web.fetch
[ExecutionManager] Step 2/2: filesystem.create_file
[ExecutionManager] Plan completed successfully: conservative_fallback
```

## Architecture

### New Files
- `src/agent/plan_candidate.py`: PlanCandidate dataclass + risk/time estimation
- `src/agent/execution_manager.py`: ExecutionManager with verification & retry
- Updated `src/agent/planner.py`: Added `plan_candidates()` function
- Updated `src/agent/config.py`: New config options
- Updated `src/agent/main.py`: Integrated multi-candidate flow

### Data Flow
```
Goal → plan_candidates(k=3)
  ↓
[Candidate 1, Candidate 2, Candidate 3] (sorted by overall_score)
  ↓
ExecutionManager.execute_with_fallback()
  ↓
For each candidate:
  ↓
  For each action:
    ↓
    execute_action_with_retry() (max 2 retries)
    ↓
    verify_action_result()
    ↓
    If verified: continue
    If failed after retries: fail plan → try next candidate
  ↓
First successful plan wins
```

## Benefits

1. **Reliability**: Automatic fallback if primary plan fails
2. **Verification**: Catches silent failures (missing files, empty web content)
3. **Retry Logic**: Handles transient errors (network timeouts, race conditions)
4. **Risk Awareness**: Ranks safer plans higher
5. **Preference Learning**: Uses trained model to score plans

## Testing

```powershell
# Enable multi-candidate planning
$env:USE_MULTI_CANDIDATE_PLANNING="1"

# Test with a web fetch goal
python -m src.agent.main "fetch python.org and create a 3-point summary"

# Test with a file operation goal
python -m src.agent.main "search for AI trends and save to trends_summary.txt"
```

## Future Enhancements

- [ ] Per-executor verification hooks (executor-specific checks)
- [ ] Plan replay/debugging (save failed plans for analysis)
- [ ] Dynamic k adjustment (start with k=1, increase on failure)
- [ ] Parallel candidate execution (race multiple plans)
- [ ] User feedback integration (upvote/downvote plans)
