# Agent Model Configuration

This file defines which AI models are used for each agent to ensure deterministic, reproducible results.

## Model Assignments

### Agent 1: Implementation Agent
- **Model**: `claude-sonnet-4.5`
- **Rationale**: Strong at code generation, modern Python features, type hints
- **Temperature**: Default (controlled by system)

### Agent 2: Primary Critique Agent (Claude)
- **Model**: `claude-sonnet-4.5`
- **Rationale**: Excellent at finding logical errors, enforcing conventions
- **Temperature**: Default (controlled by system)

### Agent 2b: Secondary Critique Agent (GPT-5)
- **Model**: `gpt-5.1-codex-max`
- **Rationale**: Alternative perspective, strong at practical engineering concerns
- **Temperature**: Default (controlled by system)

### Agent 3: Testing Agent
- **Model**: `claude-sonnet-4.5`
- **Rationale**: Thorough test coverage, good at edge case discovery, strong at property-based testing patterns
- **Temperature**: Default (controlled by system)
- **Key Requirement**: MUST implement randomized testing for every implementation

## Model Specifications

### claude-sonnet-4.5
- **Type**: Claude Sonnet 4.5
- **Provider**: Anthropic
- **Tier**: Standard
- **Best For**: Code generation, analysis, refactoring
- **Context Window**: Large
- **Speed**: Fast

### gpt-5.1-codex-max
- **Type**: GPT-5.1-Codex-Max
- **Provider**: OpenAI
- **Tier**: Standard
- **Best For**: Code review, practical engineering
- **Context Window**: Large
- **Speed**: Fast

## Usage in Code

When invoking agents programmatically:

```python
# Implementation Agent
task(
    agent_type="general-purpose",
    model="claude-sonnet-4.5",
    description="Implement feature",
    prompt="..."
)

# Primary Critic (Claude)
task(
    agent_type="general-purpose",
    model="claude-sonnet-4.5",
    description="Review implementation",
    prompt="..."
)

# Secondary Critic (GPT-5)
task(
    agent_type="general-purpose",
    model="gpt-5.1-codex-max",
    description="Secondary review",
    prompt="..."
)

# Testing Agent
task(
    agent_type="general-purpose",
    model="claude-sonnet-4.5",
    description="Write tests",
    prompt="..."
)
```

## Changing Models

To change a model assignment:
1. Update this file with the new model
2. Document the reason for the change
3. Update the agent definition in AGENTS.md
4. Test that the new model produces acceptable results

## Version History

| Date       | Change                                    | Reason                           |
|------------|-------------------------------------------|----------------------------------|
| 2026-01-29 | Initial configuration                     | Establish deterministic baseline |
| 2026-01-29 | Added GPT-5 secondary critic             | Provide alternative perspective  |

## Available Models

For reference, here are the available models in Copilot CLI:

### Standard Tier
- `claude-sonnet-4.5` - Claude Sonnet 4.5 (current default)
- `claude-sonnet-4` - Claude Sonnet 4
- `gpt-5.1-codex-max` - GPT-5.1-Codex-Max
- `gpt-5.1-codex` - GPT-5.1-Codex
- `gpt-5.1` - GPT-5.1
- `gpt-5` - GPT-5

### Fast/Cheap Tier
- `claude-haiku-4.5` - Claude Haiku 4.5
- `gpt-5.1-codex-mini` - GPT-5.1-Codex-Mini
- `gpt-5-mini` - GPT-5 mini
- `gpt-4.1` - GPT-4.1

### Premium Tier
- `claude-opus-4.5` - Claude Opus 4.5

### Preview/Experimental
- `gemini-3-pro-preview` - Gemini 3 Pro (Preview)
