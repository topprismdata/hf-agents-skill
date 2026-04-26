# hf-agents-skill

A [Claude Code](https://claude.com/claude-code) skill that bridges natural language to HuggingFace's local AI ecosystem — making it trivial to set up, configure, and run local coding agents powered by open-source LLMs.

**Languages**: English / 中文

## What It Does

Turns natural language requests into complete local AI workflows:

| You Say | What Happens |
|---------|-------------|
| "帮我装一下本地AI编程助手" | Installs all dependencies (hf CLI, llama.cpp, jq, fzf, Node.js) |
| "我的电脑能跑什么模型" | Detects your hardware and recommends models that fit |
| "帮我启动一个本地编程助手" | Downloads model, starts llama-server, launches coding agent |
| "用Qwen模型写个排序算法" | Starts Qwen model with a specific coding task |
| "本地AI还在跑吗" | Checks llama-server and Pi agent status |
| "关掉本地AI" | Gracefully stops all services |
| "为什么本地AI启动失败" | Runs 10-category diagnostics with auto-fix |

## Architecture

```
User (natural language)
    ↓
Claude Code (this skill)
    ↓
scripts/ ← smart wrappers around hf-agents ecosystem
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

## Quick Start

### As a Claude Code Skill

1. Install the skill:
   ```bash
   # Option 1: Pull from GitHub
   python ~/.claude/skills/pull_BRAINSkill/scripts/pull_skills.py \
     https://github.com/topprismdata/hf-agents-skill/archive/refs/heads/main.zip --overwrite

   # Option 2: Clone manually
   git clone https://github.com/topprismdata/hf-agents-skill.git \
     ~/.claude/skills/hf-agents-skill
   ```

2. In Claude Code, just say what you want:
   - "帮我安装本地AI编程助手"
   - "我的电脑能跑什么模型"
   - "启动一个Qwen编程助手"

### As a Standalone CLI

The `hfa` wrapper works without Claude Code:

```bash
# Symlink for convenience (optional)
ln -sf ~/.claude/skills/hf-agents-skill/scripts/hfa ~/.local/bin/hfa

# Use it
hfa setup                  # Install everything
hfa recommend              # Hardware + model recommendations
hfa run --model qwen       # Start Qwen coding agent
hfa run --model 1          # Use recommendation #1
hfa run --model qwen --task "write a quicksort"  # With a task
hfa status                 # Check services
hfa stop                   # Stop everything
hfa doctor                 # Diagnose issues
hfa doctor --fix           # Diagnose + auto-fix
```

### Individual Scripts

Each script also works independently:

```bash
# Setup — one-click dependency installer
bash scripts/setup.sh

# Hardware detection + model recommendation
python3 scripts/hardware.py                  # Full report
python3 scripts/hardware.py --json           # JSON output
python3 scripts/hardware.py --top 5          # Top 5 recommendations
python3 scripts/hardware.py --recommend-only # Skip hardware report

# Start a local coding agent
python3 scripts/run.py --model qwen          # Use model shortcut
python3 scripts/run.py --model 1             # Use recommendation #1
python3 scripts/run.py --model Qwen/Qwen2.5-Coder-7B-Instruct-GGUF  # Direct HF ID
python3 scripts/run.py --port 8081           # Custom port
python3 scripts/run.py --task "fix the bug"  # Non-interactive mode

# Check status
python3 scripts/status.py                    # Human-readable
python3 scripts/status.py --json             # JSON output

# Stop services
bash scripts/stop.sh                         # Graceful stop
bash scripts/stop.sh --force                 # Force kill

# Diagnose issues
python3 scripts/diagnose.py                  # Check only
python3 scripts/diagnose.py --fix            # Auto-fix
```

## Supported Models

| Shortcut | Model | Size (Q4_K_M) | Min RAM |
|----------|-------|---------------|---------|
| `qwen` | Qwen2.5-Coder-7B-Instruct | ~5 GB | 8 GB |
| `phi` | Phi-4-mini-instruct | ~3 GB | 8 GB |
| `deepseek` | DeepSeek-Coder-6.7B | ~4 GB | 8 GB |
| `gemma` | Gemma-3-4B-IT | ~3 GB | 8 GB |
| `llama` | Llama-3.1-8B-Instruct | ~6 GB | 16 GB |

You can also pass any HuggingFace GGUF model ID directly.

## Requirements

- **macOS** (Apple Silicon or Intel) or **Linux**
- **Homebrew** (macOS) or **apt/yum** (Linux) for system packages
- **Python 3.10+**
- **Internet connection** (for model downloads)

The `setup.sh` script installs everything else: hf CLI, llama.cpp, jq, fzf, Node.js, and the hf-agents extension.

## Supported Hardware

| Platform | GPU Backend | Auto-detected |
|----------|------------|---------------|
| Apple Silicon (M1/M2/M3/M4) | Metal | Yes |
| NVIDIA GPU (Linux) | CUDA | Yes |
| CPU only | CPU fallback | Yes |

## HuggingFace Mirror (China users)

If downloads are slow, set the HuggingFace mirror before running:

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## File Structure

```
hf-agents-skill/
├── SKILL.md                  # Claude Code skill definition
├── README.md                 # This file
├── scripts/
│   ├── setup.sh              # One-click dependency installer
│   ├── hardware.py           # Hardware detection + model recommendations
│   ├── run.py                # Start local agent (model → server → Pi)
│   ├── status.py             # Check running services
│   ├── stop.sh               # Stop services gracefully
│   ├── diagnose.py           # 10-category diagnostics + auto-fix
│   └── hfa                   # Standalone CLI wrapper
└── references/
    └── architecture.md       # Technical architecture reference
```

## Evaluation

Scored by [skill-tester](https://github.com/topprismdata/skill-tester) (4D rubric):

| Dimension | Score |
|-----------|-------|
| Documentation | 9.0/10 |
| Code/Scripts | 8.5/10 |
| Completeness | 9.0/10 |
| Usability | 9.0/10 |
| **Total** | **8.9/10 (POWERFUL)** |

## Limitations

- **macOS and Linux only** — Windows is not supported
- **hf-agents extension** may not be publicly available yet — the skill degrades gracefully to direct llama-server mode
- **GGUF models only** — this skill uses llama.cpp, not vLLM or TGI
- **Pi agent** requires Node.js — falls back to raw API mode if unavailable

## License

MIT
