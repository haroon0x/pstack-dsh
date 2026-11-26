#!/usr/bin/env python3
"""Install pstack (github.com/cursor/plugins/tree/main/pstack) into DeepSeek Harness.

pstack is a Cursor plugin. DSH has no plugin format that ships SKILL.md bundles,
so this installer copies pstack's skills into the DSH user skill root
($DSH_HOME/skills, normally ~/.dsh/skills), where dsh-skill-filesystem discovers
them live: one directory per skill, root/<name>/SKILL.md.

Run this file from a checkout of https://github.com/haroon0x/pstack-dsh at any
path. It writes only under $DSH_HOME and next to this file.

Usage:
  install.py install [--no-update]   install or update (default command)
  install.py check                   verify the installed set and DSH patches
  install.py uninstall               remove only the skills this port installed

The upstream checkout lives at $DSH_HOME/vendor/cursor-plugins (sparse: pstack/
only). Re-running install refreshes it with git fetch.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_URL = "https://github.com/cursor/plugins"
MARKER = "<!-- dsh-pstack-port -->"
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

HOME = Path.home()
DSH_HOME = Path(os.environ.get("DSH_HOME", HOME / ".dsh"))
VENDOR = DSH_HOME / "vendor" / "cursor-plugins"
SRC = VENDOR / "pstack"
DST = DSH_HOME / "skills"
PORT_DIR = Path(__file__).resolve().parent
ADAPTER_TMPL = PORT_DIR / "adapter" / "SKILL.md"
MANIFEST = PORT_DIR / "manifest.json"

# Cursor-specific vocabulary that makes a skill body need the adapter pointer.
COUPLING_RE = re.compile(
    r"~/.cursor|\.cursor/|cursor\.sh|Bugbot|Cursor [Aa]utomation|"
    r"\bTask (tool|subagent|spawn)|subagent_type|generalPurpose|"
    r"/deslop|control-ui|control-cli|cursor-team-kit|agent-transcripts|"
    r"pstack-models|AskQuestion|run_in_background|readonly:|"
    r'environment: "cloud"|`/loop`|/autopilot'
)

SKILL_FOOTER = """
{MARKER}
## DSH note

This skill runs in DeepSeek Harness, not Cursor. Before any step that mentions a
Cursor tool, `Task`/`subagent_type`, a model slug, `~/.cursor/...`,
`cursor-team-kit`, Bugbot, or Automations, read the `pstack` skill at
`{dsh}/skills/pstack/SKILL.md` for the Cursor-to-DSH mapping. Load sibling pstack
skills by reading `{dsh}/skills/<name>/SKILL.md`; the `skill` tool refuses
user-only skills.
"""

POTETO_MODE_SECTION = """
{MARKER}
## DSH harness

This copy runs in DeepSeek Harness. Read `{dsh}/skills/pstack/SKILL.md` (the
`pstack` adapter) before executing steps, and map Cursor names as follows:

- The Cursor-specific steps below are superseded by this section.
- `Task` / `subagent_type` -> the `subagent` tool. A `poteto-agent` delegate's
  brief starts with `Read {dsh}/skills/poteto-mode/worker.md before anything
  else.`, then `Then read {dsh}/skills/poteto-agent/SKILL.md and
  {dsh}/skills/poteto-mode/SKILL.md in full.`, then the goal and the task.
- `AskQuestion` -> `ask_user_question`; todolist -> `todo_write`; `/loop` ->
  `schedule_create`.
- Model slugs (`claude-*`, `gemini-*`, `auto`, `inherit-parent`) do not exist.
  Omit `provider`/`model` on `subagent` calls and roles inherit the session
  model. Skip `/setup-pstack` model detection; see `~/.dsh/AGENTS.md` for an
  optional `# pstack models` block.
- `~/.cursor/...` paths do not exist. pstack lives at `{dsh}/skills/`; its docs
  and guide live at `{vendor}/pstack/`. Transcript-mining steps are skipped.
- `cursor-team-kit` skills (`/deslop`, `control-ui`, `control-cli`) are not
  installed: skip with `Skipped in DSH: no cursor-team-kit.` and continue.
  Cursor-only Automations, Bugbot, cloud agents, and projects/workers are
  skipped the same way; use `gh` for PR work.
- To run another pstack skill, read `{dsh}/skills/<name>/SKILL.md` (the `skill`
  tool refuses user-only skills); the user can also type `/name` in a new
  message.
"""

SETUP_PSTACK_SECTION = """
{MARKER}
## DSH harness

This copy runs in DeepSeek Harness, which has no `~/.cursor/rules/` and no
Cursor model slugs. Do not detect or write Cursor models.

1. Read `{dsh}/AGENTS.md` (if present) for a `# pstack models` block; those role
   lines override anything below.
2. Offer the user the DSH route ids available in this session (inspect with
   `list_subagent_models`), or `inherit` for every role.
3. If they choose non-inherit values, write a `# pstack models` block to
   `{dsh}/AGENTS.md` with one line per role, using the exact role labels
   `poteto-mode` defines: `feature, refactoring`, `bug-fix`, `perf-issue`,
   `hillclimb`, `judgment and prose`, `swarm workers`, `arena runners`,
   `interrogate reviewers`, `arena cross-judge pool`. Never write under
   `~/.cursor/`.
4. With no changes, stop after reporting that every role inherits the session
   model; `inherit` is the DSH default and needs no file.
"""

POTETO_AGENT_DSH_NOTE = """
> **DSH note:** this file is a subagent prompt, not an agent-registry entry.
> The parent reads this file (the `skill` tool refuses it), then passes this body
> as the prompt of the `subagent` tool, prefixed with the first line
> `Read {dsh}/skills/poteto-mode/worker.md before anything else.` and then
> `Then read {dsh}/skills/poteto-agent/SKILL.md and
> {dsh}/skills/poteto-mode/SKILL.md in full.`
"""

COMMENT_SICKO_DSH_NOTE = """
> **DSH note:** this file is a subagent prompt, not an agent-registry entry.
> The parent spawns the `subagent` tool with `Read
> {dsh}/skills/comment-sicko/SKILL.md before anything else.` plus the diff or
> scoped files as the prompt.
"""


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(f"$ {' '.join(cmd)}\n{result.stderr}")
        raise SystemExit(result.returncode)
    return result.stdout.strip()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def ensure_vendor(update: bool) -> None:
    if not (VENDOR / ".git").is_dir():
        VENDOR.parent.mkdir(parents=True, exist_ok=True)
        print(f"cloning {REPO_URL} -> {VENDOR} (sparse: pstack/)")
        run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", REPO_URL, str(VENDOR)])
        run(["git", "sparse-checkout", "set", "pstack"], cwd=VENDOR)
        return
    if not update:
        return
    print("refreshing vendored checkout")
    run(["git", "fetch", "--depth", "1", "origin", "main"], cwd=VENDOR)
    run(["git", "reset", "--hard", "FETCH_HEAD"], cwd=VENDOR)
    run(["git", "sparse-checkout", "set", "pstack"], cwd=VENDOR)


def load_manifest() -> dict:
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_version() -> str:
    return json.loads((SRC / "plugin.json").read_text(encoding="utf-8")).get("version", "unknown")


def skill_dirs() -> list[Path]:
    return sorted(
        (d for d in (SRC / "skills").iterdir() if d.is_dir() and (d / "SKILL.md").is_file()),
        key=lambda d: d.name,
    )


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---", 4)
    if end < 0:
        return "", text
    body_start = text.find("\n", end + 1)
    return text[: body_start + 1], text[body_start + 1 :]


def drop_frontmatter_keys(frontmatter: str, keys: set[str]) -> str:
    out = []
    for line in frontmatter.splitlines():
        if any(line.startswith(f"{key}:") for key in keys):
            continue
        out.append(line)
    return "\n".join(out) + "\n"


def rewrite_description(frontmatter: str, suffix: str) -> str:
    match = re.search(r"^description: (.*)$", frontmatter, re.M)
    if match is None:
        return frontmatter
    return frontmatter[: match.start(1)] + match.group(1) + " " + suffix + frontmatter[match.end(1) :]


def patch_markdown_files(skill_dir: Path) -> int:
    patched = 0
    files = [skill_dir / "SKILL.md"]
    playbooks = skill_dir / "playbooks"
    if playbooks.is_dir():
        files.extend(sorted(playbooks.glob("*.md")))
    worker = skill_dir / "worker.md"
    if worker.is_file():
        files.append(worker)
    for path in files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if MARKER in text:
            continue
        footer = "\n" + SKILL_FOOTER.format(MARKER=MARKER, dsh=DSH_HOME)
        path.write_text(text.rstrip() + "\n" + footer, encoding="utf-8")
        patched += 1
    return patched


def insert_dsh_section(path: Path, section: str) -> bool:
    """Insert the DSH section directly after the document H1, if present."""
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    lines = text.splitlines()
    index = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if index is None:
        return False
    lines[index + 1 : index + 1] = ["", section.strip("\n"), ""]
    atomic_write(path, "\n".join(lines) + "\n")
    return True


def install_skill_bundle(version: str, vendor_commit: str) -> None:
    if not ADAPTER_TMPL.is_file():
        raise SystemExit(f"adapter template missing: {ADAPTER_TMPL}")

    DST.mkdir(parents=True, exist_ok=True)
    previous = load_manifest()
    for name in previous.get("skills", []):
        cleanup_skill(name)

    installed: list[str] = []
    patched_skills: list[str] = []
    for src_dir in skill_dirs():
        name = src_dir.name
        if not SKILL_NAME_RE.match(name):
            print(f"skip {name}: invalid DSH skill name")
            continue
        target = DST / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src_dir, target, symlinks=True)
        installed.append(name)
        coupled = any(
            COUPLING_RE.search(p.read_text(encoding="utf-8", errors="replace"))
            for p in src_dir.rglob("*.md")
            if "scripts" not in p.parts
        )
        if coupled and name not in {"poteto-mode", "setup-pstack"}:
            patch_markdown_files(target)
            patched_skills.append(name)

    # poteto-mode entry point: insert the DSH section right after the title so a
    # top-down executor meets the override before the Cursor-only steps.
    poteto = DST / "poteto-mode"
    if poteto.is_dir():
        poteto_skill = poteto / "SKILL.md"
        section = POTETO_MODE_SECTION.format(MARKER=MARKER, dsh=DSH_HOME, vendor=VENDOR)
        if insert_dsh_section(poteto_skill, section):
            patched_skills.append("poteto-mode")
        for playbook in sorted((poteto / "playbooks").glob("*.md")):
            body = playbook.read_text(encoding="utf-8").rstrip()
            if MARKER not in body:
                atomic_write(playbook, body + "\n\n" + SKILL_FOOTER.format(MARKER=MARKER, dsh=DSH_HOME))

    setup = DST / "setup-pstack"
    if setup.is_dir():
        setup_skill = setup / "SKILL.md"
        section = SETUP_PSTACK_SECTION.format(MARKER=MARKER, dsh=DSH_HOME)
        if insert_dsh_section(setup_skill, section):
            patched_skills.append("setup-pstack")

    # agents/*.md are not a DSH concept: install each as a prompt-carrying skill.
    for agent_name, note, drop in (
        ("poteto-agent", POTETO_AGENT_DSH_NOTE, {"model", "is_background"}),
        ("comment-sicko", COMMENT_SICKO_DSH_NOTE, set()),
    ):
        source = SRC / "agents" / f"{agent_name}.md"
        if not source.is_file():
            print(f"warn: missing agent definition {source}")
            continue
        frontmatter, body = split_frontmatter(source.read_text(encoding="utf-8"))
        frontmatter = drop_frontmatter_keys(frontmatter, drop)
        frontmatter = rewrite_description(
            frontmatter, "(DSH prompt file - read it and pass its body to the `subagent` tool.)"
        )
        # Hidden from both catalogues like the rest of pstack; the adapter
        # tells the model to read the file when it spawns a delegate.
        frontmatter = frontmatter.replace(
            "---\n", "---\ndisable-model-invocation: true\nuser-invocable: false\n", 1
        )
        target = DST / agent_name
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        body = body.replace(
            "search `~/.cursor/plugins/` for a file whose path ends in "
            "`skills/poteto-mode/SKILL.md`. If more than one file matches, use the copy whose "
            "`.cursor-plugin/plugin.json` has the highest `version`.",
            f"read `{DSH_HOME}/skills/poteto-mode/SKILL.md`.",
        )
        body = body.replace(
            "Your skill catalog hides this skill, so a missing catalog entry does not mean pstack is absent.",
            "That file exists on this machine; a missing catalog entry does not mean pstack is absent.",
        )
        body = body.replace("every Task spawn", "every subagent spawn")
        note_text = note.format(dsh=DSH_HOME)
        atomic_write(target / "SKILL.md", frontmatter.rstrip() + "\n\n" + note_text.strip() + "\n\n" + body.strip() + "\n")
        installed.append(agent_name)

    # Adapter skill: Cursor->DSH mapping, model-invocable so the model can pull it.
    adapter_text = ADAPTER_TMPL.read_text(encoding="utf-8")
    adapter_text = (
        adapter_text.replace("{{DSH_HOME}}", str(DSH_HOME))
        .replace("{{VENDOR}}", str(VENDOR))
        .replace("{{VERSION}}", version)
    )
    adapter_dir = DST / "pstack"
    if adapter_dir.exists():
        shutil.rmtree(adapter_dir)
    atomic_write(adapter_dir / "SKILL.md", adapter_text)
    # MIT requires the upstream copyright and permission notice to travel with
    # copies of the skills, so keep the upstream LICENSE inside the adapter dir.
    upstream_license = SRC / "LICENSE"
    if upstream_license.is_file():
        shutil.copy2(upstream_license, adapter_dir / "LICENSE")
    installed.append("pstack")

    # README.md and docs/ live one level above the skills root upstream, and
    # some skill bodies link to them as ../../README.md / ../../docs/.... Copy
    # them into the DSH home so those relative links resolve.
    root_assets = install_root_assets(previous)

    manifest = {
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "pstack_version": version,
        "source_url": REPO_URL,
        "source_commit": vendor_commit,
        "vendored_at": str(VENDOR),
        "skills_dir": str(DST),
        "adapter_skill": "pstack",
        "root_assets": root_assets,
        "patched": sorted(patched_skills),
        "skills": installed,
        "skill_count": len(installed),
    }
    atomic_write(MANIFEST, json.dumps(manifest, indent=2) + "\n")
    print(f"installed {len(installed)} skills into {DST} (pstack {version}, commit {vendor_commit[:9]})")
    print(f"adapter skill: {adapter_dir / 'SKILL.md'}")
    print(f"manifest: {MANIFEST}")


ROOT_ASSETS = ("README.md", "docs")


def install_root_assets(previous: dict) -> list[str]:
    previously_managed = set(previous.get("root_assets", []))
    installed: list[str] = []
    for name in ROOT_ASSETS:
        source = SRC / name
        target = DSH_HOME / name
        if not source.exists():
            print(f"warn: upstream asset missing: {source}")
            continue
        if target.exists() and name not in previously_managed:
            backup = target.with_name(target.name + ".before-pstack")
            if backup.exists():
                shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
            target.rename(backup)
            print(f"backed up existing {target} -> {backup}")
        if target.exists():
            shutil.rmtree(target) if target.is_dir() else target.unlink()
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        installed.append(name)
    return installed


def cleanup_skill(name: str) -> None:
    if not SKILL_NAME_RE.match(name):
        print(f"refuse to remove suspicious name: {name!r}")
        return
    target = (DST / name).resolve()
    try:
        target.relative_to(DST.resolve())
    except ValueError:
        print(f"refuse to remove outside {DST}: {target}")
        return
    if target.name != name:
        print(f"refuse to remove unexpected path: {target}")
        return
    if target.is_dir():
        shutil.rmtree(target)


def uninstall() -> None:
    manifest = load_manifest()
    if not manifest:
        print(f"no manifest at {MANIFEST}; nothing to uninstall")
        return
    for name in manifest.get("skills", []):
        cleanup_skill(name)
    for name in manifest.get("root_assets", []):
        if name not in ROOT_ASSETS:
            print(f"refuse to remove unexpected root asset: {name!r}")
            continue
        target = DSH_HOME / name
        backup = target.with_name(target.name + ".before-pstack")
        if target.exists():
            shutil.rmtree(target) if target.is_dir() else target.unlink()
        if backup.exists():
            backup.rename(target)
            print(f"restored {target}")
    MANIFEST.unlink(missing_ok=True)
    print(f"removed {len(manifest.get('skills', []))} installed pstack skills from {DST}")
    print(f"left in place: {VENDOR} (upstream checkout), {PORT_DIR} (this port)")


def check() -> int:
    manifest = load_manifest()
    if not manifest:
        print("FAIL: no manifest; run install")
        return 1
    missing, bad_name, unpatched = [], [], []
    for name in manifest.get("skills", []):
        skill = DST / name / "SKILL.md"
        if not skill.is_file():
            missing.append(name)
            continue
        text = skill.read_text(encoding="utf-8", errors="replace")
        header = split_frontmatter(text)[0]
        if f"name: {name}" not in header and f"name: \"{name}\"" not in header:
            bad_name.append(name)
    for name in manifest.get("root_assets", []):
        if name not in ROOT_ASSETS or not (DSH_HOME / name).exists():
            missing.append(f"root-asset:{name}")
    # Upstream restructures its entry points from time to time. A missing DSH
    # section means the patch anchors no longer match, so fail loudly here
    # instead of leaving a silently Cursor-only install. CI runs this weekly.
    for name in ("poteto-mode", "setup-pstack"):
        skill = DST / name / "SKILL.md"
        if skill.is_file() and MARKER not in skill.read_text(encoding="utf-8", errors="replace"):
            unpatched.append(name)
    problems = [p for p in (missing, bad_name, unpatched) if p]
    print(f"installed: {len(manifest.get('skills', []))} skills, pstack {manifest.get('pstack_version')}")
    print(f"location: {DST}")
    print(f"root assets: {', '.join(manifest.get('root_assets', [])) or 'none'}")
    if missing:
        print(f"MISSING ({len(missing)}): {missing}")
    if bad_name:
        print(f"NAME MISMATCH: {bad_name}")
    if unpatched:
        print(f"DSH SECTION MISSING: {unpatched}")
    if problems:
        print("FAIL")
        return 1
    print("OK: skills, root assets, and DSH sections are in place")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Install pstack skills into DeepSeek Harness")
    parser.add_argument("command", nargs="?", default="install", choices=["install", "check", "uninstall"])
    parser.add_argument("--no-update", action="store_true", help="use the existing vendored checkout as-is")
    args = parser.parse_args(argv)

    if args.command == "uninstall":
        uninstall()
        return 0
    if args.command == "check":
        return check()

    ensure_vendor(update=not args.no_update)
    if not (SRC / "plugin.json").is_file():
        print(f"error: {SRC} does not look like a pstack checkout", file=sys.stderr)
        return 1
    version = load_version()
    commit = run(["git", "rev-parse", "HEAD"], cwd=VENDOR)
    install_skill_bundle(version, commit)
    return check()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
