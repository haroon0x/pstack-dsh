# pstack for DeepSeek Harness

pstack is Lauren Tan's engineering workflow for coding agents. This repo installs it into DeepSeek Harness (DSH) and adds one adapter that translates pstack's Cursor tools, paths, and subagents into DSH terms.

The installer fetches pstack from [cursor/plugins](https://github.com/cursor/plugins/tree/main/pstack) at install time and patches it under your DSH home. This repo ships no pstack skills, so you get the upstream skills on the upstream MIT license.

## Requirements

- Python 3.9 or later.
- Git.
- DSH 0.2.2-rc.1 or later. Tested on 0.2.2-rc.1.
- A writable DSH home. The default is `~/.dsh`; set `DSH_HOME` to use another path.

## Install

One command:

```bash
curl -fsSL https://raw.githubusercontent.com/haroon0x/pstack-dsh/main/bootstrap.sh | bash
```

The script clones this repo into `$DSH_HOME/vendor/pstack-dsh` and runs the installer. It pulls the latest port first if that clone already exists.

To read the code before you run it:

```bash
mkdir -p "$HOME/.dsh/vendor"
git clone https://github.com/haroon0x/pstack-dsh.git "$HOME/.dsh/vendor/pstack-dsh"
python3 "$HOME/.dsh/vendor/pstack-dsh/install.py" install
```

The installer also runs from any clone path. It writes only under `DSH_HOME` and inside its own checkout:

```bash
git clone https://github.com/haroon0x/pstack-dsh.git ~/src/pstack-dsh
python3 ~/src/pstack-dsh/install.py install
```

Start a new DSH chat, or reload the GUI page, then type `/poteto-mode <task>`.

## Use

- `/poteto-mode` picks a playbook and drives it. `/poteto-help` lists the other skills.
- `/setup-pstack` records optional model roles in `$DSH_HOME/AGENTS.md`. With no file, every subagent role inherits the session model, which is the DSH default.
- The remaining pstack skills are user-invoked with `/name`. The model reads them from disk when a playbook asks for one.

## Update

```bash
git -C "$HOME/.dsh/vendor/pstack-dsh" pull --ff-only
python3 "$HOME/.dsh/vendor/pstack-dsh/install.py" install
```

`install` refreshes the upstream checkout to pstack main, copies the skills again, and reapplies the DSH patches. It records the pstack version and source commit in `manifest.json`.

To reinstall from the existing upstream checkout without a network fetch:

```bash
python3 "$HOME/.dsh/vendor/pstack-dsh/install.py" install --no-update
```

## Check

```bash
python3 "$HOME/.dsh/vendor/pstack-dsh/install.py" check
```

The command exits 0 when every skill and the DSH sections exist. CI runs it against upstream main in a scratch `DSH_HOME` on every push and every week.

## Uninstall

```bash
python3 "$HOME/.dsh/vendor/pstack-dsh/install.py" uninstall
```

Uninstall removes only the files listed in `manifest.json`. It restores any `$DSH_HOME/README.md` and `$DSH_HOME/docs` that the installer moved aside, and leaves the upstream checkout and this port in place.

## Troubleshooting

- `bootstrap.sh` stops because the target path exists and is not a git checkout. Move the old copy aside and run the command again. Earlier local ports used the same path.
- `check` prints `DSH SECTION MISSING`. Upstream changed a file that the patch anchors on. The weekly CI run reports the same failure. Open an issue with the pstack version that `check` prints.
- The `skill` tool refuses a pstack skill. That is expected. The skills are user-invocable on purpose. Type `/name` instead.

## What the install writes

| Path | Contents |
|---|---|
| `$DSH_HOME/skills/<name>/` | pstack skills, the `pstack` adapter, and the two agent prompt files |
| `$DSH_HOME/README.md`, `$DSH_HOME/docs/` | upstream README and guide, copied so links like `../../docs/guide/README.md` resolve |
| `$DSH_HOME/vendor/cursor-plugins/` | sparse checkout of cursor/plugins, the update source |
| `manifest.json` in this checkout | local record of installed skills, patched skills, pstack version, source commit |

At pstack 0.15.48 the installer writes 62 skill folders: 59 upstream skills, the adapter, and the two agent prompt files. `check` prints the count for the version you installed.

The installer patches DSH sections into `poteto-mode` and `setup-pstack`, adds a short adapter footer to skills and playbooks that mention Cursor tools, and installs the agent definitions as hidden prompt files. The rest of the upstream skills are copied unmodified. Upstream's MIT LICENSE is copied into the adapter directory.

## Cursor-only features

pstack was written for Cursor, so some steps have no DSH equivalent. The adapter tells the model to skip them with one line and continue.

- Cursor Automations and the benny pack are not installed.
- Bugbot, cloud agents, projects and workers, and the Cursor PR tool are not available. Use `gh` for PR work.
- `cursor-team-kit` skills (`/deslop`, `control-ui`, `control-cli`) are not installed.
- Cursor transcripts are not exposed, so transcript-mining steps report a skip.
- Cursor model slugs do not exist. Subagent roles inherit the session model unless you configure other providers.

See [docs/port-notes.md](docs/port-notes.md) for the decisions behind the port.

## Limitations

- Multi-vendor panels in `arena` and `interrogate` degrade to one model unless DSH has more than one provider route configured.
- Tested on Linux with Python 3.12. macOS should work because the scripts use portable tools. Windows is untested.
- This project is not affiliated with Cursor or Lauren Tan.

## Staying current

Upstream pstack changes often. The `.github/workflows/verify.yml` job installs the latest upstream into a scratch DSH home and runs `check`. A failing weekly run means an upstream change broke a patch anchor. Fix `install.py`, run `scripts/verify-install.sh`, and push.

## License

The port is MIT licensed. See [LICENSE](LICENSE). pstack itself is Copyright (c) 2026 Lauren Tan, MIT. See [NOTICE](NOTICE). This repo does not vendor upstream skills.
