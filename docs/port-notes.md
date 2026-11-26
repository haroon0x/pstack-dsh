# Port notes

This is the decision record for installing pstack into DeepSeek Harness (DSH). It covers what DSH supports natively, what the installer patches, and what the port leaves out. The installer is the source of truth.

## Verdict

pstack is portable in shape and Cursor-specific in wording. Its skill format matches DSH: a directory per skill with `SKILL.md`, YAML frontmatter, and `disable-model-invocation`. DSH reads the same keys. The skill bodies name Cursor tools (`Task`, `AskQuestion`, `create-skill`), Cursor paths (`~/.cursor/...`), Cursor model slugs, and Cursor-only products (Bugbot, Automations, cloud agents, projects, `cursor-team-kit`).

The port copies every upstream skill, adds one adapter skill, patches the two entry-point skills, and adds a footer to any skill or playbook that mentions a Cursor tool. It excludes the Cursor Automations pack.

## Install shape

DSH discovers skills from scanned roots and reads direct children only, `<root>/<name>/SKILL.md`. Root ranks are project `.dsh/skills` 100, project `.agents/skills` 200, `customSkillDirs` 300, `~/.dsh/skills` 400, `~/.agents/skills` 500, and bundled skills 600.

The port installs into `~/.dsh/skills`. Two alternatives were rejected.

- A custom skill root keeps the upstream tree byte-identical, but it needs a profile patch and that patch differs per DSH preset.
- A plugin bundle needs a package, a bundle patch row, pnpm, and a restart or relink cycle. It adds moving parts for the same catalogue.

The user skill root needs no configuration and reloads live. The installer flattens `pstack/skills/*` into `$DSH_HOME/skills/` and copies upstream `README.md` and `docs/` to `$DSH_HOME` so relative links inside skill bodies resolve.

## Frontmatter compatibility

- Both DSH and pstack require `name` in kebab case and `description`.
- DSH honours `disable-model-invocation` and `user-invocable` with the same meaning as Cursor.
- Cursor extras (`icon`, `color`, `paths`) are ignored by DSH.
- Every upstream skill except `setup-pstack` sets `disable-model-invocation: true`. That keeps the model catalogue near zero tokens. Flipping the policy would add roughly 3k tokens of descriptions to every request, so the port keeps it.

## Files the installer patches

- `poteto-mode/SKILL.md`: inserts a `## DSH harness` section after the title so a top-down executor meets the mapping first. All 22 playbooks also get the adapter footer.
- `setup-pstack/SKILL.md`: inserts a DSH section that collects model routes with `list_subagent_models` and writes an optional `# pstack models` block to `$DSH_HOME/AGENTS.md`.
- Skills whose bodies mention Cursor tools get a short footer with the adapter path and the note that sibling skills load by reading `SKILL.md`.
- `agents/poteto-agent.md` and `agents/comment-sicko.md`: become hidden skills (`disable-model-invocation: true`, `user-invocable: false`) whose bodies are prompts. Cursor-only fields are dropped, and the Cursor plugin path fallback is rewritten to the local skill path.

The manifest records the patched list.

## Cursor to DSH mapping

This table is abridged. The installed adapter has the full mapping.

| Cursor | DSH |
|---|---|
| Task tool, `subagent_type` | `subagent`, or `subagent_fork` for inherited context |
| `run_in_background` | not needed; subagents return an id immediately |
| `readonly: true` | no field; say "read-only" in the brief and check `git status` after |
| `AskQuestion` | `ask_user_question` |
| todolist | `todo_write` |
| `Grep`, `Glob`, `Read`, `Write`, `Edit`, `Bash` | `grep`, `glob`, `read`, `write`, `edit`, `bash` |
| `/loop` | `schedule_create` |
| Cursor model slugs | omit `provider` and `model` to inherit the session model |
| `.cursor/rules/pstack-models.mdc` | `$DSH_HOME/AGENTS.md` |
| `.cursor/skills/` | `.dsh/skills/` in a project, or `$DSH_HOME/skills/` |
| transcripts under `~/.cursor/projects/` | not exposed to agents; skip the step |
| Bugbot, Automations, cloud agents, `cursor-team-kit` | skip with one line and continue |

## Skipped content

- `automations/benny/`: Cursor Automations and Slack, no DSH equivalent.
- `.cursor-plugin/`, `plugin.json`, logo: Cursor packaging.
- `make-bot-ui` and `ketchup-video` are copied for parity but report a missing dependency.
- The statechart TLA+ test corpus is copied with the skill. It needs Java and TLA+ tools to run.

## Token cost

These estimates were measured on upstream 0.15.43.

| Quantity | Estimate |
|---|---|
| Model catalogue with only `setup-pstack` | about 72 tokens |
| Model catalogue if all skills were model-invocable | about 3,260 tokens |
| All skill bodies, loaded only on demand | about 39,400 tokens |
| One playbook | 210 to 1,700 tokens |

The catalogue cost stays near zero because skill bodies load only when a user or a playbook reads them. The upstream checkout is disk, not context.

## Upstream drift

The installer tracks pstack main. It rebuilds the install from the upstream tree on every run, so a new upstream skill appears without a port change. The fragile part is the patch anchors. If upstream renames or restructures `poteto-mode` or `setup-pstack`, the DSH section may not apply.

`install.py check` fails when a DSH section is missing, and CI runs that check weekly against upstream main. Fix the patch, then run `scripts/verify-install.sh` before pushing.

## Verification

`install.py check` verifies three things:

- Every manifest skill has a `SKILL.md` with a matching `name`.
- Upstream README and docs are present.
- Both patched entry points contain the DSH marker.

The check does not run the skills. A smoke test is to start a new DSH chat, run `/poteto-mode` on a small task, and confirm the model cites a principle and loads the skill file by path.
