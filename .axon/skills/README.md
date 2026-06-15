# AXON Skills

Skills are markdown-driven instruction sets (inspired by Claude Code's `SKILL.md`).

## Layout

```
.axon/skills/
  my-skill/
    SKILL.md
```

Each skill lives in its own subdirectory with a `SKILL.md` file.

## SKILL.md format

```markdown
---
name: my-skill
description: Short description shown to the LLM as a tool
disable-model-invocation: false
allowed-tools: read_file, execute_shell
---

# Instructions

Your skill body here. Use inline shell to inject live context:

Current directory:
!`pwd`

When this skill is invoked, follow the instructions above.
```

## Frontmatter fields

| Field | Description |
|-------|-------------|
| `name` | Tool name (defaults to folder name) |
| `description` | Tool description for the LLM |
| `disable-model-invocation` | If `true`, hidden from LLM tools (manual only) |
| `allowed-tools` | Comma-separated built-in tools the skill may use |

## Inline shell (`!`command``)

Before the skill body is sent to the LLM, AXON executes `!`command`` placeholders
locally and replaces them with stdout/stderr output.
