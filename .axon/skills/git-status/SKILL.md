---
name: git-status
description: Inspect git repository status and summarize recent activity for the user
disable-model-invocation: false
allowed-tools: execute_shell, read_file
---

# Git Status Skill

You are helping the user understand their git repository.

## Live context (auto-injected)

Branch:
!`git branch --show-current 2>nul || git branch --show-current`

Last 3 commits:
!`git log -3 --oneline 2>nul || git log -3 --oneline`

## Instructions

1. Run or reason about `git status` using `execute_shell` if needed.
2. Summarize staged, unstaged, and untracked changes clearly.
3. Mention the current branch and recent commits from the context above.
4. Keep the reply concise and actionable.
