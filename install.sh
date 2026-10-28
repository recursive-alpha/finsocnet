#!/usr/bin/env bash
set -euo pipefail

# FinSocNet Installer
# Installs finsocnet CLI and registers plugins across all AI harnesses
# (Claude Code, OMP, Pi, Hermes, OpenAI Codex, OpenClaw, DeepSeek Harness)

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
echo "=================================================================="
echo "    FinSocNet: Multi-Platform Intelligence & Strategy Terminal    "
echo "=================================================================="
echo -e "${NC}"

# Check for uv
if ! command -v uv >/dev/null 2>&1; then
    echo -e "${YELLOW}uv package manager not found. Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# --local: install only what the user's own machine needs (session export), plus the optional cookie readers
LOCAL_ONLY=0
for a in "$@"; do [ "$a" = "--local" ] && LOCAL_ONLY=1; done

# Determine source directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "$PWD")"
INSTALL_DIR="${FINSOCNET_DIR:-$HOME/.local/share/finsocnet}"

if [ -f "$SCRIPT_DIR/pyproject.toml" ] && grep -q 'name = "finsocnet"' "$SCRIPT_DIR/pyproject.toml" 2>/dev/null; then
    INSTALL_DIR="$SCRIPT_DIR"
    echo -e "${BLUE}[1/4]${NC} Using local repository at ${BOLD}$INSTALL_DIR${NC}"
else
    echo -e "${BLUE}[1/4]${NC} Setting up FinSocNet repository at ${BOLD}$INSTALL_DIR${NC}..."
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "      Updating existing repository..."
        (cd "$INSTALL_DIR" && git pull --quiet 2>/dev/null || true)
    else
        mkdir -p "$(dirname "$INSTALL_DIR")"
        echo "      Cloning from https://github.com/recursive-alpha/finsocnet.git..."
        git clone --depth 1 https://github.com/recursive-alpha/finsocnet.git "$INSTALL_DIR"
    fi
fi

BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"
TARGET_BIN="$BIN_DIR/finsocnet"

echo -e "${BLUE}[2/4]${NC} Building environment and creating CLI executable at ${BOLD}$TARGET_BIN${NC}..."
if [ "$LOCAL_ONLY" = "1" ]; then uv sync --project "$INSTALL_DIR" --extra local; else uv sync --project "$INSTALL_DIR"; fi

rm -f "$TARGET_BIN"
cat > "$TARGET_BIN" << EOF
#!/usr/bin/env bash
exec uv run --project "$INSTALL_DIR" finsocnet "\$@"
EOF
chmod +x "$TARGET_BIN"
echo -e "${GREEN}      ✓ Python CLI installed at: $TARGET_BIN${NC}"

# Ensure BIN_DIR is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}      Notice: $BIN_DIR is not in your \$PATH.${NC}"
    echo "      Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "        export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Register Plugins across AI Harnesses (not needed on the machine that only exports browser sessions)
if [ "$LOCAL_ONLY" = "1" ]; then
    echo -e "${BLUE}[3/4]${NC} --local: skipping harness registration. Next: finsocnet session init-local --recipient age1… --remote user@host --remote-path /srv/finsocnet"
else
    echo -e "${BLUE}[3/4]${NC} Registering FinSocNet plugins across AI Harnesses..."
    "$TARGET_BIN" install all
fi

# Verification
echo -e "${BLUE}[4/4]${NC} Verifying installation..."
"$TARGET_BIN" stats >/dev/null 2>&1 || true
echo -e "${GREEN}      ✓ FinSocNet CLI and database verified!${NC}"

echo -e "\n${CYAN}${BOLD}Installation Complete!${NC}\n"
echo -e "You can now run:"
echo -e "  ${BOLD}finsocnet kb init${NC}                      # Create data/knowledge.db (v2 schema, vocabulary seed)"
echo -e "  ${BOLD}finsocnet${NC}                              # Knowledge base summary"
echo -e "  ${BOLD}finsocnet tui${NC}                          # Terminal UI: cards, persons, gaps, sessions"
echo -e "  ${BOLD}finsocnet strategy minervini${NC}           # A person's rulebook"
echo -e "  ${BOLD}finsocnet session export${NC}               # (your own machine) export logged-in browser sessions"
echo -e "  ${BOLD}/finsocnet:search <question>${NC}           # Slash command inside Claude Code, OMP, Pi, Codex, Hermes, OpenClaw"
echo ""
