# AXON — VS Code / Cursor Extension (MVP)

Send the current editor selection to the [AXON](https://runaxon.xyz) CLI as a headless prompt (`axon -p`). Responses appear in the **AXON** output channel.

> Phase G MVP — unpacked install only. Not published to the marketplace.

## Prerequisites

- [AXON CLI](https://github.com/core/axon) installed and on your `PATH` (`axon doctor` should pass)
- VS Code **1.85+** or Cursor

## Install (unpacked)

1. Clone or copy this repo so `vscode-extension/` exists locally.
2. Open **Extensions** (`Ctrl+Shift+X` / `Cmd+Shift+X`).
3. Click the `···` menu → **Install from VSIX…** is *not* used here — choose **Install from Location…** / **Load Extension**:
   - **VS Code:** Command Palette → `Developer: Install Extension from Location…` → pick `vscode-extension/`
   - **Cursor:** Command Palette → `Extensions: Install from Location…` → pick `vscode-extension/`
4. Reload the window when prompted.

Alternative (development):

```bash
code --extensionDevelopmentPath="C:\path\to\CLI\vscode-extension"
# or
cursor --extensionDevelopmentPath="C:\path\to\CLI\vscode-extension"
```

## Usage

1. Select text in an editor.
2. Run **AXON: Send Selection to Prompt** from the Command Palette, editor context menu, or `Ctrl+Shift+A` (`Cmd+Shift+A` on macOS).
3. Open the **AXON** output channel to read the CLI response.

The extension runs:

```bash
axon -p "<your selection>" --cwd <workspace-root>
```

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `axon.executable` | `axon` | CLI binary name or absolute path |
| `axon.headlessArgs` | `[]` | Extra flags, e.g. `["--yes"]` or `["--json"]` |

## Optional: `tasks.json` snippet

Add to `.vscode/tasks.json` in your project for a task-based workflow (no extension required):

```jsonc
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "AXON: Send selection to prompt",
      "type": "shell",
      "command": "axon -p \"${selectedText}\" --cwd ${workspaceFolder}",
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "dedicated",
        "clear": true
      }
    }
  ]
}
```

Bind via `keybindings.json` if desired:

```json
{
  "key": "ctrl+shift+a",
  "command": "workbench.action.tasks.runTask",
  "args": "AXON: Send selection to prompt",
  "when": "editorHasSelection"
}
```

> `${selectedText}` is resolved when the task runs from the active editor with a selection.

## Branding

Matches AXON Zenith: black `#000`, white `#fafafa`, monospace output channel logging.

## Out of scope (MVP)

- Marketplace publish
- Inline diff / LSP
- Auth / Zenith webview panel
