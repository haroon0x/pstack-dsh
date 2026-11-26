# DSH install mechanics

This note records how DSH discovers and reloads skills, and why the port installs into the user skill root instead of a plugin. It was verified on DSH 0.2.2-rc.1. Source line numbers refer to that release and can move.

## Roots and ranks

`@deepseek-ai/dsh-skill-filesystem` scans each root for direct children only, `<root>/<name>/SKILL.md` or `<root>/<name>.md`. It does not discover nested `**/SKILL.md` files.

| Root | Rank |
|---|---|
| project `.dsh/skills` | 100 |
| project `.agents/skills` | 200 |
| `customSkillDirs` | 300 |
| `~/.dsh/skills` | 400 |
| `~/.agents/skills` | 500 |
| bundled skills | 600 |

The default roots come from `includeDefaultRoots: true`, with `dshHome = $DSH_HOME || ~/.dsh`. Rank resolves same-name duplicates within one layer. The registry merges layers, and the nearest layer wins.

Install into `~/.dsh/skills`, not `~/.agents/skills`, because the latter is shared with other harnesses.

## Frontmatter contract

- Required fields are `name` and `description`. `name` must match `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
- DSH honours `whenToUse`, `metadata`, `disable-model-invocation`, and `user-invocable`.
- Legacy aliases (`disableModelInvocation`, `modelInvocable`, `userInvocable`) are rejected with a warning and the skill is skipped.
- Unknown fields are ignored, so Cursor extras are harmless.
- The directory name does not have to match the frontmatter name.

## Hot reload

An installed skill becomes visible without restarting `dsh web`.

1. The filesystem provider watches each root at depth 1 and watches missing roots through an ancestor poll.
2. A relevant event invalidates the provider and bumps the registry revision.
3. `dsh-tool-skill` recomputes the model-visible catalogue on each step and injects a replacement catalogue message when the digest changes.
4. New sessions and subagents see the new catalogue on their first step.

The browser `/` menu caches its list per session. Reload the page to see a new skill in the menu. Typing `/name` works without a reload.

## Symlinks

Symlinked skill directories, flat files, and roots are followed. The installer copies real directories anyway, so the installed tree does not depend on the checkout path.

## Slash invocation

The composer inserts the literal text `/<name> `. On send, the pre-step hook matches `/name` in user messages and injects the full skill body for user-invocable skills. The `skill` tool refuses skills that are not model-invocable.

That is why most pstack skills stay user-invoked, and why the adapter tells the model to load siblings by reading `SKILL.md`.

## Why not a plugin bundle

A bundle would need a package with a bundle patch row, a profile link, pnpm install and build approval, and a restart or relink to replace it. The user skill root needs none of that and has the same catalogue cost. The trade-off is no version pinning in the DSH plugin manager, which the installer covers with its own manifest.

## Limits

- Hot reload was verified at the provider level and by reading the DSH source, not by driving the live GUI in every profile.
- Presets that mount their own skill filesystem use the same default roots, so the install applies there too.
