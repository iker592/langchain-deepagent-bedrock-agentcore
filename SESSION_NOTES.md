# Session Notes - Dec 29, 2025

## Changes Made

1. **Local SDK** - `pyproject.toml` now uses local `agent-sdk/` instead of remote Yahoo PyPI
2. **Package structure** - Moved files to `agent-sdk/src/yahoo_dsp_agent_sdk/`
3. **`make chat` fix** - Added `__main__` block, fixed port to 8080, set `chmod +x` on script
4. **AWS config** - Removed bootstrap qualifier and cross-account role

## Deployment

- **Account**: `239388734812`
- **Runtime ID**: `deep_agent-6o4qqZBwpx`
- **Memory ID**: `memory-lIAIK14xDn`
- **Region**: `us-east-1`

## Commands

```bash
# Local
make local          # Start server on :8080
make chat           # Interactive chat

# Deployed
make invoke ENDPOINT=dev INPUT="..."
make invoke-stream ENDPOINT=dev INPUT="..."
```

