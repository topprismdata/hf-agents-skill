# hf-agents Architecture Reference

## Overview

hf-agents is a HuggingFace CLI extension that enables local AI coding assistants.
It connects three components:

1. **hf CLI + hf-agents extension** — Model discovery, download, hardware fitting
2. **llama.cpp (llama-server)** — Local LLM inference server (OpenAI-compatible API)
3. **Pi agent** — Coding agent that uses the LLM to complete tasks

## Component Details

### 1. HuggingFace CLI (`hf`)

Installed via `pip install huggingface_hub`. Provides:
- `hf download <model>` — Download model files from HuggingFace Hub
- `hf extensions install hf-agents` — Install the agents extension
- `hf extensions exec agents fit system` — Detect hardware capabilities
- `hf extensions exec agents fit recommend` — Recommend models for hardware

### 2. llama-server (from llama.cpp)

A lightweight HTTP server that runs GGUF models locally:
- OpenAI-compatible `/v1/chat/completions` endpoint
- `/health` endpoint for health checks
- `/props` endpoint for server properties
- Supports Metal (Apple Silicon), CUDA (NVIDIA), CPU backends
- Key flags: `-m` (model), `--port`, `-ngl` (GPU layers), `-c` (context size)

Install: `brew install llama.cpp` (macOS) or build from source (Linux)

### 3. Pi Agent

A coding agent that connects to llama-server:
- Reads config from `~/.config/pi/config.json`
- Uses OpenAI-compatible API to communicate with llama-server
- Can run in interactive or non-interactive (`--task`) mode

## Data Flow

```
┌─────────────────────────────────────────────┐
│  User Request (natural language to Claude)   │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  Skill Scripts                               │
│  ├── hardware.py → "what models fit?"        │
│  ├── run.py      → "start model X"           │
│  └── status.py   → "is it running?"          │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  hf CLI                                      │
│  ├── hf download <model> (get GGUF files)    │
│  └── hf agents fit (hardware detection)      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  llama-server                                │
│  ├── Loads GGUF model into memory            │
│  ├── Serves OpenAI-compatible API            │
│  └── Uses Metal/CUDA/CPU for inference       │
│  Default: http://localhost:8080               │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  Pi Agent (optional)                         │
│  ├── Connects to llama-server API            │
│  ├── Accepts coding tasks                    │
│  └── Reads/writes files, runs commands       │
└─────────────────────────────────────────────┘
```

## Key Paths

| Path | Purpose |
|------|---------|
| `~/.cache/huggingface/hub/` | Downloaded model files (GGUF) |
| `~/.cache/hf-agents/llama-server.log` | llama-server log output |
| `~/.config/pi/config.json` | Pi agent configuration |
| `~/.config/pi/config.json.bak` | Pi config backup (created by scripts) |

## Model Selection Guide

### Quantization Levels

| Level | Size vs Original | Quality Loss | Use Case |
|-------|-----------------|-------------|----------|
| Q4_K_M | ~30-40% | Moderate | Best balance for limited RAM |
| Q5_K_M | ~40-50% | Minimal | Good quality, needs more RAM |
| Q8_0 | ~70-80% | Negligible | Near-original quality |

### Memory Estimates (Q4_K_M)

| Model | Parameters | Memory Needed | Min System RAM |
|-------|-----------|---------------|---------------|
| Phi-4-mini | 3.8B | ~3 GB | 8 GB |
| Qwen2.5-Coder-7B | 7B | ~5 GB | 8 GB |
| DeepSeek-Coder-6.7B | 6.7B | ~4 GB | 8 GB |
| Gemma-3-4B | 4B | ~3 GB | 8 GB |
| Qwen2.5-Coder-14B | 14B | ~10 GB | 16 GB |
| Llama-3.1-8B | 8B | ~6 GB | 16 GB |
| Qwen2.5-Coder-32B | 32B | ~20 GB | 32 GB |

### Performance Estimates (Apple M3 Pro)

| Model | Approx tok/s (Q4_K_M) |
|-------|----------------------|
| Phi-4-mini (3.8B) | ~30-40 |
| Qwen2.5-Coder-7B | ~15-25 |
| Qwen2.5-Coder-14B | ~8-12 |
| Qwen2.5-Coder-32B | ~3-5 |

## Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `llama-server: command not found` | llama.cpp not installed | `brew install llama.cpp` |
| `Address already in use` | Port occupied | `stop.sh` or `--port 8081` |
| `model not found` | GGUF file not downloaded | Check `~/.cache/huggingface/hub/` |
| `OOM/cannot allocate memory` | Model too large for RAM | Use smaller model or quantization |
| `CUDA error` | NVIDIA driver issue | Update drivers, or use CPU mode |
| `Metal: no suitable device` | Non-Apple Silicon | Remove `-ngl` flag, use CPU |
| `download stalled` | Network issues | Use HF mirror: `export HF_ENDPOINT=https://hf-mirror.com` |
