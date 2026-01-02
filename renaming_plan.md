# Rename DeepAgent to DSPAgent

## Summary of Changes

| Pattern | Current | New |
|---------|---------|-----|
| Stack class | `ServerlessDeepAgentStack` | `DSPAgentStack` |
| Stack ID | `"ServerlessDeepAgentStack"` | `"DSPAgentStack"` |
| Runtime name | `deep_agent` | `dsp_agent` |
| Construct ID | `DeepAgent` | `DSPAgent` |
| Variable | `deepagent_runtime_artifact` | `dspagent_runtime_artifact` |
| Package name | `serverless-deep-agent` | `dsp-agent` |
| Docker image | `deepagent` | `dspagent` |

---

## Files to Modify

### 1. Infrastructure Code

**[iac/stack.py](iac/stack.py)**:

- `ServerlessDeepAgentStack` → `DSPAgentStack`
- `deepagent_runtime_artifact` → `dspagent_runtime_artifact`
- `"DeepAgent"` → `"DSPAgent"`
- `"deep_agent"` → `"dsp_agent"`

**[iac/app.py](iac/app.py)**:

- Import and instantiate `DSPAgentStack`

### 2. Build Configuration

**[pyproject.toml](pyproject.toml)**: `name = "dsp-agent"`

**[docker-compose.yml](docker-compose.yml)**: `image: dspagent`

### 3. Makefile

**[Makefile](Makefile)**: Replace all 10 occurrences of `ServerlessDeepAgentStack` → `DSPAgentStack`

### 4. Scripts

**[scripts/on_merge.sh](scripts/on_merge.sh)**: `ServerlessDeepAgentStack` → `DSPAgentStack`

### 5. Documentation

**[README.md](README.md)**: Update `deep_agent` examples to `dsp_agent`

### 6. Directory

**agents/deep/** → **agents/dsp/**

---

## Verification Steps

1. **Lint and format**: `make fix`
2. **Unit tests**: `make test-unit`
3. **Open PR** for deployment verification on another machine