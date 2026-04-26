#!/usr/bin/env bash
# stop.sh — Gracefully stop llama-server and Pi agent
# Usage: bash stop.sh [--force]
set -euo pipefail

FORCE=false
[[ "${1:-}" == "--force" ]] && FORCE=true

log()  { echo "[hfa] $*"; }

# ── Stop Pi agent ────────────────────────────────────────────────
PI_PIDS=$(pgrep -f "pi" 2>/dev/null || true)
if [[ -n "$PI_PIDS" ]]; then
    log "Stopping Pi agent..."
    echo "$PI_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    # Check if still running
    PI_PIDS=$(pgrep -f "pi" 2>/dev/null || true)
    if [[ -n "$PI_PIDS" ]]; then
        if [[ "$FORCE" == "true" ]]; then
            log "Force killing Pi..."
            echo "$PI_PIDS" | xargs kill -KILL 2>/dev/null || true
        else
            log "Pi is still running. Use --force to kill."
        fi
    else
        log "Pi stopped."
    fi
else
    log "Pi agent is not running."
fi

# ── Stop llama-server ───────────────────────────────────────────
LS_PIDS=$(pgrep -f "llama-server" 2>/dev/null || true)
if [[ -n "$LS_PIDS" ]]; then
    log "Stopping llama-server..."
    echo "$LS_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    LS_PIDS=$(pgrep -f "llama-server" 2>/dev/null || true)
    if [[ -n "$LS_PIDS" ]]; then
        if [[ "$FORCE" == "true" ]]; then
            log "Force killing llama-server..."
            echo "$LS_PIDS" | xargs kill -KILL 2>/dev/null || true
        else
            log "llama-server is still running. Use --force to kill."
        fi
    else
        log "llama-server stopped."
    fi
else
    log "llama-server is not running."
fi

# ── Restore Pi config backup ────────────────────────────────────
PI_CONFIG="${HOME}/.config/pi/config.json"
PI_BACKUP="${HOME}/.config/pi/config.json.bak"
if [[ -f "$PI_BACKUP" ]]; then
    log "Restoring Pi config from backup..."
    mv "$PI_BACKUP" "$PI_CONFIG" 2>/dev/null || true
fi

log "All services stopped."
