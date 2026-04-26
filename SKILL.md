---
name: hf-agents-skill
description: |
  Use HuggingFace's hf-agents to run local AI coding assistants.
  Translates natural language requests into setup, model selection, launch,
  monitoring, and troubleshooting actions for local LLM-based coding agents.
  Covers hardware detection, model recommendation, llama-server management,
  and Pi coding agent integration.
---

# hf-agents Skill — Local AI Coding Assistant

This skill bridges user natural language to the hf-agents ecosystem, making it
easy to set up, configure, and run local coding agents powered by open-source
LLMs (Qwen, Phi, DeepSeek, etc.) via llama.cpp.

## When to Use This Skill

**Trigger phrases** (user says something like):

| User Intent | Trigger Phrases |
|-------------|-----------------|
| **Install/setup** | "帮我装一下本地AI编程助手", "setup local AI", "install hf-agents", "本地AI安装" |
| **Hardware check** | "我的电脑能跑什么模型", "what models can I run", "硬件检测", "check my GPU" |
| **Start agent** | "帮我启动一个本地编程助手", "start local AI", "启动本地AI", "run a local model" |
| **Specific model** | "用Qwen模型写个排序算法", "用deepseek帮我写代码", "run qwen model" |
| **Check status** | "本地AI助手还在跑吗", "is the local AI running", "check llama server" |
| **Stop services** | "关掉本地AI", "stop local model", "stop llama server" |
| **Diagnose issues** | "为什么本地AI启动失败", "local AI not working", "llama server error", "模型下载失败" |

## Architecture

```
User (natural language)
    ↓
Claude Code (this skill)
    ↓
scripts/  ←── smart wrappers around hf-agents ecosystem
    ├── setup.sh      → install all deps
    ├── hardware.py   → detect hardware + recommend models
    ├── run.py        → download model → start llama-server → start Pi agent
    ├── status.py     → check running services
    ├── stop.sh       → stop services gracefully
    ├── diagnose.py   → find and fix issues
    └── hfa           → standalone CLI entry point
    ↓
hf-agents / llama.cpp / Pi agent
```

## Workflow

### 1. First-time Setup

When the user wants to set up local AI for the first time:

```bash
# Run the setup script
bash ~/.claude/skills/hf-agents-skill/scripts/setup.sh
```

This installs: hf CLI, hf-agents extension, llama.cpp, jq, fzf, Node.js.

**What to tell the user:**
- What's being installed and why
- Whether installation succeeded
- If HuggingFace login is needed for gated models

### 2. Hardware Check & Model Recommendation

When the user asks what models they can run:

```bash
python3 ~/.claude/skills/hf-agents-skill/scripts/hardware.py
```

**What to tell the user:**
- Their hardware summary (chip, memory, GPU)
- Recommended models in a friendly format
- Estimated memory usage and speed for each model

For JSON output (programmatic use):
```bash
python3 ~/.claude/skills/hf-agents-skill/scripts/hardware.py --json
```

### 3. Start a Local Coding Agent

When the user wants to start coding with a local model:

```bash
# With a model shortcut
python3 ~/.claude/skills/hf-agents-skill/scripts/run.py --model qwen

# With a specific task
python3 ~/.claude/skills/hf-agents-skill/scripts/run.py --model qwen --task "write a quicksort in Python"

# With a recommendation number from hardware.py
python3 ~/.claude/skills/hf-agents-skill/scripts/run.py --model 1

# If server is already running
python3 ~/.claude/skills/hf-agents-skill/scripts/run.py --skip-server --task "fix the bug"
```

**Model shortcuts available:**
- `qwen` → Qwen2.5-Coder-7B-Instruct (default, recommended)
- `phi` → Phi-4-mini-instruct
- `deepseek` → DeepSeek-Coder-6.7B
- `gemma` → Gemma-3-4B-IT
- `llama` → Llama-3.1-8B-Instruct
- Any HuggingFace model ID (e.g., `Qwen/Qwen2.5-Coder-14B-Instruct-GGUF`)

**What to tell the user:**
- Which model was selected
- Download progress (if not cached)
- When the server is ready
- How to connect (URL or Pi agent)

### 4. Check Status

```bash
python3 ~/.claude/skills/hf-agents-skill/scripts/status.py
```

Shows: running processes, ports, memory usage, current model, recent log lines.

### 5. Stop Services

```bash
bash ~/.claude/skills/hf-agents-skill/scripts/stop.sh
# Force kill if graceful stop fails
bash ~/.claude/skills/hf-agents-skill/scripts/stop.sh --force
```

### 6. Diagnose Issues

```bash
# Check only
python3 ~/.claude/skills/hf-agents-skill/scripts/diagnose.py

# Auto-fix
python3 ~/.claude/skills/hf-agents-skill/scripts/diagnose.py --fix
```

Checks: llama-server binary, hf CLI, hf-agents extension, port availability,
HuggingFace auth, system memory, GPU support, error logs, dependency tools.

## Standalone CLI

All functionality is also available via the `hfa` wrapper script:

```bash
# Symlink for convenience (optional)
ln -sf ~/.claude/skills/hf-agents-skill/scripts/hfa ~/.local/bin/hfa

# Then use:
hfa setup                  # Install everything
hfa recommend              # Hardware + model recommendations
hfa run --model qwen       # Start Qwen coding agent
hfa run --model 1          # Use recommendation #1
hfa status                 # Check services
hfa stop                   # Stop everything
hfa doctor                 # Diagnose issues
hfa doctor --fix           # Diagnose + auto-fix
```

## Common Scenarios

### "I want to use local AI but don't know where to start"

1. Run `setup.sh` to install dependencies
2. Run `hardware.py` to see what models fit their hardware
3. Guide them to pick a model and run `run.py --model <choice>`

### "Download is too slow"

Set HuggingFace mirror before downloading:
```bash
export HF_ENDPOINT=https://hf-mirror.com
```
Then retry. See also: `huggingface-mirror-acceleration` skill.

### "Out of memory error"

- Switch to a smaller model (7B → 3B)
- Use a more aggressive quantization (Q5 → Q4)
- Close other applications
- The `hardware.py` script estimates memory requirements

### "Port already in use"

- Stop existing server: `bash stop.sh`
- Or use a different port: `run.py --port 8081`

## Notes

- llama-server runs in the background and persists after the skill exits
- Model files are cached in `~/.cache/huggingface/hub/`
- Server logs go to `~/.cache/hf-agents/llama-server.log`
- Pi config is at `~/.config/pi/config.json` (backed up before modification)
- Apple Silicon automatically uses Metal GPU acceleration
- NVIDIA GPUs automatically use CUDA via `-ngl 99`

## Limitations

- **macOS and Linux only** — Windows is not supported (llama.cpp builds differ, no PowerShell wrappers)
- **hf-agents extension** may not be publicly available yet — the skill degrades gracefully, falling back to direct llama-server + OpenAI-compatible API mode
- **Pi agent** requires Node.js and the `hf agents run pi` subcommand — if unavailable, the skill falls back to raw llama-server with curl instructions
- **GGUF models only** — this skill uses llama.cpp, not vLLM or TGI; models must be in GGUF format
- **Hardware recommendations** require the `hf agents fit recommend` command — without it, the skill provides hardcoded popular model suggestions
- **Memory estimates** are approximate — actual usage depends on context length, batch size, and quantization

## Version

- v1.1.0 — 2026-04-26
- Scripts: setup.sh, hardware.py, run.py, status.py, stop.sh, diagnose.py, hfa

## See Also

- `huggingface-mirror-acceleration` — Faster model downloads
- `qwen-model-compatibility-guide` — Qwen model version compatibility
- `gemma4-on-device-deployment` — Gemma 4 on Apple Silicon
- `references/architecture.md` — Technical architecture details
