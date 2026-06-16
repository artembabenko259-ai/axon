"use strict";

const { spawn } = require("child_process");
const vscode = require("vscode");

/** @type {vscode.OutputChannel | undefined} */
let outputChannel;

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  outputChannel = vscode.window.createOutputChannel("AXON", { log: true });
  outputChannel.appendLine("AXON extension ready — select text and run “AXON: Send Selection to Prompt”.");

  context.subscriptions.push(
    outputChannel,
    vscode.commands.registerCommand("axon.sendSelection", sendSelection)
  );
}

function deactivate() {
  outputChannel = undefined;
}

async function sendSelection() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("AXON: open an editor with a text selection first.");
    return;
  }

  const selection = editor.selection;
  const prompt = editor.document.getText(selection).trim();
  if (!prompt) {
    vscode.window.showWarningMessage("AXON: select some text to send as a prompt.");
    return;
  }

  const workspaceFolder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
  const cwd = workspaceFolder?.uri.fsPath ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

  if (!cwd) {
    vscode.window.showWarningMessage("AXON: open a workspace folder so --cwd can be set for axon -p.");
    return;
  }

  const config = vscode.workspace.getConfiguration("axon");
  const executable = config.get("executable", "axon");
  const extraArgs = config.get("headlessArgs", []);

  const args = ["-p", prompt, "--cwd", cwd, ...extraArgs];

  outputChannel?.show(true);
  outputChannel?.appendLine("");
  outputChannel?.appendLine(`✦ AXON  ${new Date().toLocaleTimeString()}`);
  outputChannel?.appendLine(`$ ${executable} -p "<selection>" --cwd ${cwd}${extraArgs.length ? " " + extraArgs.join(" ") : ""}`);
  outputChannel?.appendLine("—".repeat(48));
  outputChannel?.appendLine(prompt);
  outputChannel?.appendLine("—".repeat(48));

  await new Promise((resolve) => {
    const child = spawn(executable, args, {
      cwd,
      shell: process.platform === "win32",
      env: process.env,
    });

    child.stdout?.on("data", (chunk) => {
      outputChannel?.append(chunk.toString());
    });

    child.stderr?.on("data", (chunk) => {
      outputChannel?.append(chunk.toString());
    });

    child.on("error", (err) => {
      outputChannel?.appendLine("");
      outputChannel?.appendLine(`[error] ${err.message}`);
      vscode.window.showErrorMessage(
        `AXON: failed to run "${executable}". Install AXON CLI and ensure it is on PATH, or set axon.executable.`
      );
      resolve();
    });

    child.on("close", (code) => {
      outputChannel?.appendLine("");
      outputChannel?.appendLine(`[exit ${code ?? "?"}]`);
      if (code !== 0) {
        vscode.window.showWarningMessage(`AXON finished with exit code ${code}. See AXON output channel.`);
      }
      resolve();
    });
  });
}

module.exports = { activate, deactivate };
