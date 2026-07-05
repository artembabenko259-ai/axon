#!/usr/bin/env bash
# ============================================================================
#  AXON Linux One-Click Builder (Arch / General Linux)
#  Creates a standalone compiled ELF binary with bundled Next.js Zenith UI
# ============================================================================

set -euo pipefail

# Project root
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

VERSION="1.0.1"
RELEASE_DIR="$ROOT/release"
VENV_PY="$ROOT/.venv-build/bin/python"

echo -e "\033[1;36m========================================================================\033[0m"
echo -e "\033[1;36m  AXON Linux Builder v${VERSION} (Arch / General Linux)\033[0m"
echo -e "\033[1;36m========================================================================\033[0m"
echo

# --- Step 1: Check System Requirements ---------------------------------------
echo -e "\033[1;34m[1/6] Checking system tools...\033[0m"
for cmd in python3 node npm; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "\033[1;31m[ERROR] Required tool '$cmd' not found in PATH.\033[0m"
        if [ "$cmd" = "python3" ]; then
            echo "Install via: sudo pacman -S python"
        elif [ "$cmd" = "node" ] || [ "$cmd" = "npm" ]; then
            echo "Install via: sudo pacman -S nodejs npm"
        fi
        exit 1
    fi
done
echo "      Python, Node, npm found."

# --- Step 2: Set up Virtual Environment --------------------------------------
if [ ! -f "$VENV_PY" ]; then
    echo -e "\033[1;34m[2/6] Creating build virtualenv .venv-build...\033[0m"
    python3 -m venv "$ROOT/.venv-build"
    "$VENV_PY" -m pip install --upgrade pip -q
    "$VENV_PY" -m pip install -r "$ROOT/requirements.txt" -q
    "$VENV_PY" -m pip install -r "$ROOT/requirements-build.txt" -q
else
    echo -e "\033[1;34m[2/6] Reusing existing virtualenv .venv-build\033[0m"
fi

# --- Step 3: Build Zenith Web Panel (Next.js standalone) ---------------------
echo -e "\033[1;34m[3/6] Compiling Next.js Zenith control panel...\033[0m"
"$VENV_PY" "$ROOT/scripts/build_zenith.py"
if [ ! -f "$ROOT/build/bundle-staging/zenith-web/server.js" ]; then
    echo -e "\033[1;31m[ERROR] Standalone server.js not found in Zenith staging.\033[0m"
    exit 1
fi

# --- Step 4: Compile Go Shard Client (Optional) ------------------------------
if command -v go &>/dev/null; then
    echo -e "\033[1;34m[4/6] Compiling Go-based Shard client...\033[0m"
    (
        cd "$ROOT/shard"
        go build -o "$ROOT/axon-shard"
    )
else
    echo -e "\033[1;33m[4/6] Go compiler not found, skipping Go TUI client build.\033[0m"
fi

# --- Step 5: Build AXON Standalone Executable (PyInstaller) ------------------
echo -e "\033[1;34m[5/6] Packaging AXON executable with PyInstaller...\033[0m"
"$VENV_PY" "$ROOT/scripts/build_exe.py" --clean
if [ ! -f "$ROOT/dist/exe/axon/axon" ]; then
    echo -e "\033[1;31m[ERROR] Standalone ELF binary not created at dist/exe/axon/axon.\033[0m"
    exit 1
fi
if [ ! -f "$ROOT/dist/exe/axon/uar" ]; then
    echo -e "\033[1;31m[ERROR] Standalone ELF binary not created at dist/exe/axon/uar.\033[0m"
    exit 1
fi

# Copy Go client if compiled
if [ -f "$ROOT/axon-shard" ]; then
    copy_dest="$ROOT/dist/exe/axon/axon-shard"
    cp "$ROOT/axon-shard" "$copy_dest"
    chmod +x "$copy_dest"
fi

# Copy staged Zenith web panel and .axon assets into the build directory
echo "Syncing staged assets to bundle..."
cp -r "$ROOT/build/bundle-staging/zenith-web" "$ROOT/dist/exe/axon/zenith-web"
cp -r "$ROOT/build/bundle-staging/.axon" "$ROOT/dist/exe/axon/.axon"

# --- Step 6: Create Portable Linux Release Package ---------------------------
echo -e "\033[1;34m[6/6] Packaging final release...\033[0m"
mkdir -p "$RELEASE_DIR"
rm -rf "$RELEASE_DIR/axon-linux"
cp -r "$ROOT/dist/exe/axon" "$RELEASE_DIR/axon-linux"

# Write installation helper script
cat << 'EOF' > "$RELEASE_DIR/axon-linux/install.sh"
#!/usr/bin/env bash
set -e
INSTALL_DIR="$HOME/.local/share/axon"
BIN_DIR="$HOME/.local/bin"

echo "Installing AXON to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -r "$(dirname "${BASH_SOURCE[0]}")"/* "$INSTALL_DIR/"

echo "Creating binary symlinks in $BIN_DIR/axon and $BIN_DIR/uar..."
mkdir -p "$BIN_DIR"
ln -sf "$INSTALL_DIR/axon" "$BIN_DIR/axon"
ln -sf "$INSTALL_DIR/uar" "$BIN_DIR/uar"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "\n\033[1;33m[NOTE] $BIN_DIR is not in your PATH. Please add it to your ~/.bashrc or ~/.zshrc:\033[0m"
    echo 'export PATH="$HOME/.local/bin:$PATH"'
fi
echo -e "\033[1;32m[SUCCESS] AXON and UAR successfully installed! Type 'axon' or 'uar' to start.\033[0m"
EOF
chmod +x "$RELEASE_DIR/axon-linux/install.sh"

echo
echo -e "\033[1;32m========================================================================\033[0m"
echo -e "\033[1;32m  BUILD COMPLETE!\033[0m"
echo -e "\033[1;32m========================================================================\033[0m"
echo "  Staged output:  $RELEASE_DIR/axon-linux/"
echo "  Run executable: $RELEASE_DIR/axon-linux/axon"
echo
echo "  To install AXON locally on your notebook:"
echo "    cd $RELEASE_DIR/axon-linux"
echo "    ./install.sh"
echo -e "\033[1;32m========================================================================\033[0m"
echo
