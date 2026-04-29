# Bailian Model State Management

## Overview

The Bailian provider now includes persistent model state management. This system automatically tracks which models have failed (403 errors) and which model is currently working, persisting this information across service restarts.

## How It Works

1. **Automatic Tracking**: When a model returns a 403 error, it's automatically marked as failed
2. **Persistent Storage**: Failed models are saved to `bailian_model_state.json`
3. **Smart Filtering**: On service restart, failed models are automatically excluded from the available pool
4. **Working Model**: The system remembers which model last worked successfully

## State File

The state is stored in `bailian_model_state.json` in the project root directory:

```json
{
  "failed_models": ["qwen-max", "qwen-plus"],
  "current_working_model": "qwen-turbo",
  "available_models": ["qwen-turbo", "qwen-long"],
  "last_updated": "2026-04-28T10:30:00+00:00"
}
```

This file is automatically created when the first model failure occurs.

## Viewing State

### Method 1: Command Line Tool

```bash
# View current state
uv run python -m providers.bailian

# Or with explicit state file path
uv run python -m providers.bailian --state-file bailian_model_state.json
```

Example output:
```
============================================================
Bailian Model State
============================================================

State File: bailian_model_state.json
Last Updated: 2026-04-28 10:30:00 UTC

Current Working Model:
  ✓ qwen-turbo

Available Models (2):
    1. qwen-turbo
    2. qwen-long

Failed Models (2):
  ✗ 1. qwen-max
  ✗ 2. qwen-plus

============================================================
```

### Method 2: Direct JSON Inspection

```bash
cat bailian_model_state.json | python -m json.tool
```

### Method 3: Server Logs

Check `server.log` for these log messages:
- `BAILIAN_INIT:` - Shows initial state on startup
- `BAILIAN_MODEL_SWITCH:` - Shows when switching to next model
- `BAILIAN_STREAM: Error detected on model` - Shows which model failed
- `BAILIAN_MODEL_SUCCESS:` - Shows successful model and available list
- `BAILIAN_STATE:` - Shows state manager operations

## Managing State

### Reset Failed Models

If you want to retry previously failed models (e.g., after quota refresh):

```bash
uv run python -m providers.bailian --reset
```

This clears all failed models but keeps the current working model.

### Clear All State

To completely reset the state:

```bash
uv run python -m providers.bailian --clear
```

This removes the state file entirely. On next service start, all configured models will be tried again.

### Manual Edit

You can also manually edit `bailian_model_state.json`:

```json
{
  "failed_models": [],
  "current_working_model": null,
  "available_models": [],
  "last_updated": null
}
```

Then restart the service.

## Workflow Example

### Initial Configuration

```env
BAILIAN_MODELS="qwen-max,qwen-plus,qwen-turbo,qwen-long"
MODEL="bailian/qwen-max"
```

### First Request (qwen-max fails)

```
BAILIAN_STREAM: Error detected on model qwen-max, will retry with next model (attempt 2/5)
BAILIAN_STATE: Marked model 'qwen-max' as failed (total failed: 1)
```

### Second Request (qwen-plus fails)

```
BAILIAN_STREAM: Error detected on model qwen-plus, will retry with next model (attempt 3/5)
BAILIAN_STATE: Marked model 'qwen-plus' as failed (total failed: 2)
```

### Third Request (qwen-turbo succeeds!)

```
BAILIAN_MODEL_SUCCESS: Using working model qwen-turbo (available: ['qwen-turbo', 'qwen-long'])
BAILIAN_STATE: Working model changed from 'none' to 'qwen-turbo'
```

### Service Restart - Auto-Sync to .env

On next startup, the system automatically syncs state back to `.env`:

```
BAILIAN_INIT: Configured 4 models, 2 available after filtering failed ones
BAILIAN_STATE_SYNC: Updated MODEL to 'bailian/qwen-turbo'
BAILIAN_STATE_SYNC: Updated BAILIAN_MODELS to 2 models
BAILIAN_STATE_SYNC: Successfully synced state to .env - working=bailian/qwen-turbo, available=2
```

The `.env` file is now updated:
```env
MODEL="bailian/qwen-turbo"
BAILIAN_MODELS="bailian/qwen-turbo,bailian/qwen-long"
```

Now only `qwen-turbo` and `qwen-long` will be tried, skipping the known-failed models.

## Benefits

1. **Efficiency**: No wasted API calls to known-failed models
2. **Persistence**: State survives service restarts
3. **Transparency**: Easy to see which models are working/failed
4. **Flexibility**: Can reset state when quotas refresh
5. **Debugging**: Clear logs show exactly what's happening
6. **Auto-Sync**: On service startup, automatically updates `.env` file with current working model and available models

## Troubleshooting

### State file not created

The state file is only created when the first model failure occurs. If all models work, no file is created.

### Want to retry failed models

Use the `--reset` command or manually edit the state file to clear `failed_models`.

### State seems stale

Check the `last_updated` timestamp. If it's old, you might want to reset the state and let the system re-evaluate model availability.

### Multiple service instances

If running multiple instances, they will each maintain their own state file. Consider using a shared state file path if needed:

```python
from providers.bailian import BailianModelState

# Use shared location
state_manager = BailianModelState(state_file="/shared/bailian_state.json")
```

## API Usage

For programmatic access:

```python
from providers.bailian import BailianModelState

# Load state
state = BailianModelState()

# Get information
print(state.get_working_model())        # Current working model
print(state.get_failed_models())        # List of failed models
print(state.get_available_models())     # List of available models
print(state.get_status_summary())       # Complete status dict

# Modify state
state.mark_model_failed("qwen-max")     # Mark a model as failed
state.set_working_model("qwen-turbo")   # Set working model
state.reset_failed_models()             # Reset all failures
state.clear_state()                     # Clear everything
```
