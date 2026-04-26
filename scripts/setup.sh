#!/usr/bin/env bash
# setup.sh — One-click installer for hf-agents and all dependencies
# Usage: bash setup.sh [--skip-hf-login]
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SKIP_LOGIN=false
DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --skip-hf-login) SKIP_LOGIN=true ;;
        --dry-run) DRY_RUN=true ;;
    esac
done

# In dry-run mode, wrap install commands with a no-op
maybe_do() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} Would run: $*"
        return 0
    fi
    "$@"
}

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; }

OS="$(uname -s)"
ARCH="$(uname -m)"
errors=0

check_cmd() {
    command -v "$1" &>/dev/null
}

# ── 1. OS detection ──────────────────────────────────────────────
info "Detected: $OS ($ARCH)"

if [[ "$OS" != "Darwin" && "$OS" != "Linux" ]]; then
    fail "Unsupported OS: $OS (only macOS and Linux are supported)"
    exit 1
fi

# ── 2. Install system dependencies ───────────────────────────────
install_if_missing() {
    local cmd="$1"; shift
    if check_cmd "$cmd"; then
        ok "$cmd is already installed"
        return 0
    fi

    info "Installing $cmd..."
    if [[ "$OS" == "Darwin" ]]; then
        if ! check_cmd brew; then
            fail "Homebrew not found. Install it from https://brew.sh"
            errors=$((errors + 1))
            return 1
        fi
        maybe_do brew install "$@"
    else
        # Try apt first, then yum
        if check_cmd apt-get; then
            maybe_do sudo apt-get update -qq && maybe_do sudo apt-get install -y -qq "$@"
        elif check_cmd yum; then
            maybe_do sudo yum install -y "$@"
        else
            fail "No supported package manager found (tried apt, yum)"
            errors=$((errors + 1))
            return 1
        fi
    fi

    if check_cmd "$cmd"; then
        ok "$cmd installed successfully"
    else
        fail "Failed to install $cmd"
        errors=$((errors + 1))
    fi
}

# jq
install_if_missing jq jq

# fzf
install_if_missing fzf fzf

# ── 3. Install Node.js (needed for Pi) ──────────────────────────
if check_cmd node; then
    NODE_VERSION=$(node --version 2>/dev/null || echo "unknown")
    ok "Node.js $NODE_VERSION is installed"
else
    info "Installing Node.js..."
    if [[ "$OS" == "Darwin" ]]; then
        brew install node
    else
        # Use NodeSource
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - 2>/dev/null || true
        sudo apt-get install -y nodejs 2>/dev/null || sudo yum install -y nodejs 2>/dev/null || true
    fi
    if check_cmd node; then
        ok "Node.js installed: $(node --version)"
    else
        warn "Node.js installation may have failed. Pi (coding agent) requires Node.js."
        errors=$((errors + 1))
    fi
fi

# ── 4. Install llama.cpp ────────────────────────────────────────
if check_cmd llama-server; then
    ok "llama-server is already installed: $(llama-server --version 2>&1 | head -1 || echo 'version unknown')"
else
    info "Installing llama.cpp (provides llama-server)..."
    if [[ "$OS" == "Darwin" ]]; then
        brew install llama.cpp
    else
        # Build from source on Linux
        if ! check_cmd cmake; then
            install_if_missing cmake cmake
        fi
        if ! check_cmd g++; then
            install_if_missing g++ g++ build-essential 2>/dev/null || true
        fi
        LLAMA_DIR="${HOME}/.local/share/llama.cpp"
        info "Building llama.cpp from source into $LLAMA_DIR..."
        mkdir -p "$LLAMA_DIR"
        git clone https://github.com/ggml-org/llama.cpp.git "$LLAMA_DIR/src" 2>/dev/null || \
            (cd "$LLAMA_DIR/src" && git pull)
        cd "$LLAMA_DIR/src"
        cmake -B build -DCMAKE_INSTALL_PREFIX="$LLAMA_DIR" 2>&1 | tail -5
        cmake --build build --config Release -j"$(nproc 2>/dev/null || echo 4)" 2>&1 | tail -5
        # Add to PATH
        mkdir -p "${HOME}/.local/bin"
        cp build/bin/llama-server "${HOME}/.local/bin/" 2>/dev/null || \
            cp build/llama-server "${HOME}/.local/bin/" 2>/dev/null || true
        export PATH="${HOME}/.local/bin:$PATH"
        cd - > /dev/null
    fi
    if check_cmd llama-server; then
        ok "llama-server installed"
    else
        fail "llama-server installation failed. Try: brew install llama.cpp (macOS) or build from https://github.com/ggml-org/llama.cpp"
        errors=$((errors + 1))
    fi
fi

# ── 5. Install / update huggingface_hub CLI ─────────────────────
if check_cmd hf; then
    HF_VERSION=$(hf --version 2>/dev/null || echo "unknown")
    ok "hf CLI installed: $HF_VERSION"
else
    info "Installing huggingface-cli..."
    pip install -U huggingface_hub 2>&1 | tail -3
fi

if ! check_cmd hf; then
    # Try via python module
    if python3 -m huggingface_hub version &>/dev/null; then
        warn "hf CLI not in PATH, but huggingface_hub is installed. Adding to PATH..."
        PIP_BIN="$(python3 -m pip show huggingface_hub 2>/dev/null | grep Location | sed 's/Location: //' | sed 's/site-packages.*/scripts/')"
        export PATH="$PIP_BIN:$PATH"
    else
        fail "hf CLI not available. Install with: pip install -U huggingface_hub"
        errors=$((errors + 1))
    fi
fi

# ── 6. Install hf-agents extension ──────────────────────────────
if hf extensions list 2>&1 | grep -q "agents"; then
    ok "hf-agents extension is installed"
else
    info "Installing hf-agents extension..."
    if hf extensions install hf-agents 2>&1; then
        ok "hf-agents extension installed"
    else
        warn "hf-agents extension install via 'hf extensions install hf-agents' failed."
        warn "The extension may not yet be publicly available. Check https://huggingface.co/docs for updates."
        warn "The other scripts in this skill can still use llama.cpp + OpenAI-compatible API directly."
    fi
fi

# ── 7. HuggingFace login ────────────────────────────────────────
if [[ "$SKIP_LOGIN" == "true" ]]; then
    info "Skipping HuggingFace login (--skip-hf-login)"
else
    HF_TOKEN="${HF_TOKEN:-}"
    if [[ -n "$HF_TOKEN" ]]; then
        info "Using HF_TOKEN from environment"
    elif [[ -f "${HOME}/.cache/huggingface/token" ]]; then
        ok "HuggingFace token found in cache"
    else
        warn "No HuggingFace token found."
        echo "  To download gated models, you may need to log in:"
        echo "    hf login"
        echo "  Or set HF_TOKEN environment variable"
    fi
fi

# ── 8. Summary ──────────────────────────────────────────────────
echo ""
echo "=========================================="
echo "  hf-agents Setup Summary"
echo "=========================================="

check_dep() {
    if check_cmd "$1"; then
        echo -e "  ${GREEN}✓${NC} $1 — $(command -v "$1")"
    else
        echo -e "  ${RED}✗${NC} $1 — NOT FOUND"
        errors=$((errors + 1))
    fi
}

check_dep hf
check_dep llama-server
check_dep jq
check_dep fzf
check_dep node
check_dep python3

echo ""
if [[ $errors -eq 0 ]]; then
    ok "All dependencies installed! Ready to use hf-agents."
    echo ""
    echo "Quick start:"
    echo "  python3 $(dirname "$0")/hardware.py    # Check hardware & recommend models"
    echo "  python3 $(dirname "$0")/run.py          # Start a local coding agent"
    echo "  python3 $(dirname "$0")/status.py       # Check running services"
else
    warn "$errors issue(s) found. Some features may not work."
    echo "  Run 'python3 $(dirname "$0")/diagnose.py' for troubleshooting."
fi

exit $errors
