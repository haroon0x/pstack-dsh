---
name: pstack
description: Use when any pstack skill is active in DeepSeek Harness (poteto-mode, its playbooks, principles, architect, arena, swarm, interrogate, recall, teach, verification skills) or when a pstack step mentions Task/subagent_type/model slugs/~/.cursor paths/cursor-team-kit/Bugbot/Automations. Maps pstack's Cursor conventions to DSH tools, paths, and subagents, and names what to skip.
---

# pstack in DeepSeek Harness (DSH adapter)

pstack (Lauren Tan's "poteto" workflow, MIT) is installed for DSH at `{{DSH_HOME}}/skills/` from `cursor/plugins` pstack `{{VERSION}}` (vendored at `{{VENDOR}}`). Its skills were written for Cursor. Read this adapter before following any pstack step that mentions a Cursor tool, subagent, model, rule file, or `.cursor/` path. If a Cursor field has no row here, drop it and say so.

The port that produced this install lives at https://github.com/haroon0x/pstack-dsh. Reinstall or update with `python3 install.py install` from that checkout. The upstream pstack skills themselves come from `https://github.com/cursor/plugins/tree/main/pstack`.

## Loading pstack skills

- Most pstack skills are user-invocation-only (`disable-model-invocation: true`). The `skill` tool answers `skill "<name>" is not available for model invocation`. To run one, read `{{DSH_HOME}}/skills/<name>/SKILL.md` and follow it. Sibling references such as `../<name>/SKILL.md` resolve against `{{DSH_HOME}}/skills/`.
- The user invokes them from the composer by typing `/name`, e.g. `/poteto-mode <task>`, `/how ...`, `/architect ...`. A `/name` token naming a user-invocable skill is injected into that step.
- Only `setup-pstack` and `pstack` (this adapter) are in your skill catalogue. Every other pstack skill, plus the `poteto-agent` and `comment-sicko` prompt files, loads by `read`.

## Tools

| Cursor | DSH |
|---|---|
| `Task` / Task tool / Task subagent | `subagent` (fresh context) or `subagent_fork` (inherits this conversation) |
| `run_in_background: true` | no such flag: `subagent` returns an id immediately and reports when finished; fan out by emitting several `subagent` calls in one block. For large independent fan-out use the `workflow` tool. |
| `readonly: true` | spawn `subagent` and say "read-only: do not edit files in this task"; there is no readonly tool mode |
| agent mode / MCP access | subagents inherit the toolset; there is no mode to select |
| `AskQuestion` | `ask_user_question` |
| open/copy a todolist | `todo_write` |
| `Grep`, `Glob` | `grep`, `glob` |
| `/loop` | `schedule_create` (recurring) or one long `subagent` run |
| Cursor Automations, Bugbot, cloud agents, projects/workers, built-in PR tool, `SendToUser` | Cursor-only: skip with one line `Skipped in DSH: <step>. Cursor-only.` then continue. Use `gh` for PR work. |
| `/deslop`, `control-ui`, `control-cli` (`cursor-team-kit`) | not installed: write `Skipped in DSH: no cursor-team-kit.` and continue; `unslop`, `technical-writing`, `make-bot-ui` are installed |
| Cursor built-ins `create-skill`, `/autopilot`, plan mode | not installed: substitute `reflect`/`teaching`-style authoring plus `todo_write`, or say so |

## Subagents

- `subagent_type: "poteto-agent"` -> `subagent` with a self-contained prompt whose first line is the one `poteto-mode` already requires, `Read {{DSH_HOME}}/skills/poteto-mode/worker.md before anything else.`, followed by `Then read {{DSH_HOME}}/skills/poteto-agent/SKILL.md and {{DSH_HOME}}/skills/poteto-mode/SKILL.md in full.`, then the goal and the task. Read the `poteto-agent` file yourself to copy its body; the `skill` tool refuses it. Do not use the parent to do the delegate's work.
- `subagent_type: "generalPurpose"` -> `subagent` with the same prompt minus the poteto-agent read.
- `subagent_type: "comment-sicko"` -> `subagent` with `Read {{DSH_HOME}}/skills/comment-sicko/SKILL.md before anything else.` plus the diff or scoped files.
- `environment: "cloud"` -> no cloud workers; run locally, or isolate with `bash` and `git worktree add`.
- `resume` -> `subagent_fork`, or a new `subagent` with the earlier result pasted into the brief.
- `file_attachments` -> list absolute paths in the prompt.
- Fan out by emitting several `subagent` calls in one block; results arrive as they finish.

## Models

- Cursor slugs (`claude-opus-5-5-xhigh-fast`, `gemini-4-carbon-high`, `auto`, `inherit-parent`) do not exist here. DSH subagent calls take `provider` + `model` (inspect with `list_subagent_models`); omit both to inherit this session's model, which is the default and the right choice for most pstack roles.
- The pstack model rule does not live at `~/.cursor/rules/pstack-models.mdc`. Check `{{DSH_HOME}}/AGENTS.md` for an optional `pstack models` block; absent that, every role inherits the session model. Cursor role slugs in the skill bodies are dead text: never pass `claude-*`/`gemini-*`/`auto`/`inherit-parent` to `subagent`. If the user runs `/setup-pstack`, follow its DSH section (offer DSH route ids or `inherit`) instead of its Cursor steps. Run an arena/interrogate panel on the session model unless the user has other providers configured, and then say that the vendor check did not run.
- If a step says a model slug was rejected, run that role on the session model and note it.

## Paths

| Cursor | DSH |
|---|---|
| `.cursor/skills/` (project) | `.dsh/skills/` at the project root (or `<project>/.agents/skills/`) |
| `~/.cursor/skills/` | `{{DSH_HOME}}/skills/` |
| `~/.cursor/plugins/` | `{{VENDOR}}/` |
| `.cursor/rules/pstack-models.mdc` | `{{DSH_HOME}}/AGENTS.md` (optional `pstack models` block) |
| `~/.cursor/projects/<slug>/agent-transcripts/*.jsonl` | no Cursor transcripts. DSH session logs live under `{{DSH_HOME}}/sessions/` and are not exposed to agents: write `Skipped in DSH: transcripts are not exposed to agents.` and work from the conversation plus `git log` instead |
| any write under `~/.cursor/` | never; use `{{DSH_HOME}}/` or the project's `AGENTS.md`/`.dsh/` |
| pstack GitHub URL | read the local vendored copy under `{{VENDOR}}/pstack/` (README and `docs/guide/` included) |

## Not installed

- `pstack/automations/benny` (Cursor Automations pack, Slack triage + repro): excluded, Cursor-only.
- `cursor-team-kit` skills (`deslop`, `control-ui`, `control-cli`), Cursor built-ins (`create-skill`, `/autopilot`, plan mode), Cursor Automations, Bugbot, cloud agents, projects/workers, agent transcripts.

## Guardrails

- Verify with real commands through `bash`, never self-report. `prove-it-works` and DSH's own `verification-before-completion` / `systematic-debugging` skills complement pstack.
- Do not write under `{{VENDOR}}` or `~/.cursor/`. Installed pstack files are managed by `{{VENDOR}}/../pstack-dsh/install.py` (`install`, `check`, `uninstall` subcommands).
- Skill folders ship helper scripts (`scripts/`, e.g. bun/gh/playwright-based). Check the runtime exists before relying on a script; if it is missing, do the step by hand or skip it with a line.
