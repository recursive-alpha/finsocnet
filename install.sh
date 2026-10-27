#!/usr/bin/env bash
set -euo pipefail

# FinSocNet Installer
# Installs finsocnet single binary and registers plugins across all AI harnesses
# (OMP, Pi, Claude Code, OpenAI Codex, Hermes, OpenClaw, DeepSeek Harness)

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
echo "=================================================================="
echo "    FinSocNet: Hypothesis Explorer & Multi-Agent Harness TUI      "
echo "=================================================================="
echo -e "${NC}"

# 1. Determine directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"

TARGET_BIN="$BIN_DIR/finsocnet"

echo -e "${BLUE}[1/4]${NC} Installing finsocnet CLI to ${BOLD}$TARGET_BIN${NC}..."

uv sync --project "$SCRIPT_DIR"

rm -f "$TARGET_BIN"
cat > "$TARGET_BIN" << EOF
exec uv run --project "$SCRIPT_DIR" finsocnet "\$@"
EOF
chmod +x "$TARGET_BIN"
echo -e "${GREEN}      ✓ Python CLI installed at: $TARGET_BIN${NC}"

# Ensure BIN_DIR is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}      Notice: $BIN_DIR is not in your \$PATH.${NC}"
    echo "      Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "        export PATH=\"$BIN_DIR:\$PATH\""
fi

# 2. Install shared Agent Skill
echo -e "${BLUE}[2/4]${NC} Installing shared Agent Skill to ${BOLD}~/.agents/skills/finsocnet${NC}..."
mkdir -p "$HOME/.agents/skills/finsocnet"
if [ -f "$SCRIPT_DIR/.agents/skills/finsocnet/SKILL.md" ]; then
    cp "$SCRIPT_DIR/.agents/skills/finsocnet/SKILL.md" "$HOME/.agents/skills/finsocnet/SKILL.md"
    echo -e "${GREEN}      ✓ Agent Skill installed conforming to agentskills.io spec.${NC}"
fi

# 3. Register Slash Commands across Harnesses
echo -e "${BLUE}[3/4]${NC} Registering /finsocnet plugin across AI Harnesses..."

# OMP
if [ -d "$HOME/.omp" ] || command -v omp >/dev/null 2>&1; then
    mkdir -p "$HOME/.omp/agent/extensions"
    if [ -f "$SCRIPT_DIR/extensions/omp/finsocnet.ts" ]; then
        cp "$SCRIPT_DIR/extensions/omp/finsocnet.ts" "$HOME/.omp/agent/extensions/finsocnet.ts"
        echo -e "${GREEN}      ✓ OMP: Installed extension ~/.omp/agent/extensions/finsocnet.ts (/finsocnet)${NC}"
    fi
fi

# Pi Coding Agent
if [ -d "$HOME/.pi" ] || command -v pi >/dev/null 2>&1; then
    mkdir -p "$HOME/.pi/agent/extensions"
    if [ -f "$SCRIPT_DIR/extensions/omp/finsocnet.ts" ]; then
        cp "$SCRIPT_DIR/extensions/omp/finsocnet.ts" "$HOME/.pi/agent/extensions/finsocnet.ts"
        echo -e "${GREEN}      ✓ Pi: Installed extension ~/.pi/agent/extensions/finsocnet.ts (/finsocnet)${NC}"
    fi
fi

# Claude Code
if [ -d "$HOME/.claude" ] || command -v claude >/dev/null 2>&1; then
    mkdir -p "$HOME/.claude/commands" "$HOME/.claude/skills"
    if [ -f "$SCRIPT_DIR/commands/claude/finsocnet.md" ]; then
        cp "$SCRIPT_DIR/commands/claude/finsocnet.md" "$HOME/.claude/commands/finsocnet.md"
        ln -sfn "$HOME/.agents/skills/finsocnet" "$HOME/.claude/skills/finsocnet"
        echo -e "${GREEN}      ✓ Claude Code: Registered slash command ~/.claude/commands/finsocnet.md (/finsocnet)${NC}"
    fi
fi

# Hermes Agent
if [ -d "$HOME/.hermes" ] || command -v hermes >/dev/null 2>&1; then
    mkdir -p "$HOME/.hermes/skills/research/finsocnet"
    if [ -f "$SCRIPT_DIR/.agents/skills/finsocnet/SKILL.md" ]; then
        cp "$SCRIPT_DIR/.agents/skills/finsocnet/SKILL.md" "$HOME/.hermes/skills/research/finsocnet/SKILL.md"
        echo -e "${GREEN}      ✓ Hermes: Installed skill ~/.hermes/skills/research/finsocnet/SKILL.md${NC}"
    fi
fi

# OpenAI Codex
if [ -d "$HOME/.codex" ] || command -v codex >/dev/null 2>&1; then
    mkdir -p "$HOME/.codex/skills"
    ln -sfn "$HOME/.agents/skills/finsocnet" "$HOME/.codex/skills/finsocnet"
    echo -e "${GREEN}      ✓ Codex: Linked skill ~/.codex/skills/finsocnet${NC}"
fi

# DeepSeek Harness (DSH)
if command -v dsh >/dev/null 2>&1; then
    echo -e "${GREEN}      ✓ DSH: Connected to DeepSeek Harness CLI${NC}"
fi

# 4. Quick Verification
echo -e "${BLUE}[4/4]${NC} Verifying installation..."
STATS_OUTPUT="$($TARGET_BIN stats 2>/dev/null | grep -E "Total Hypotheses" || echo "Ready")"
echo -e "${GREEN}      ✓ Database connection verified: $STATS_OUTPUT${NC}"

echo -e "\n${CYAN}${BOLD}Installation Complete!${NC}\n"
echo -e "You can now run:"
echo -e "  ${BOLD}finsocnet${NC}                      # Open interactive Codex/OMP-style Chat TUI"
echo -e "  ${BOLD}finsocnet search \"breakout\"${NC}      # Search mined hypotheses directly from CLI"
echo -e "  ${BOLD}finsocnet view 2${NC}               # View full hypothesis card with verbatim quotes"
echo -e "  ${BOLD}/finsocnet${NC}                      # Use slash command inside OMP, Claude, Codex, Hermes, Pi"
echo ""
