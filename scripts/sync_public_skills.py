#!/usr/bin/env python3
"""Build, validate, apply, and optionally publish privacy-safe public Skill copies."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "sync-manifest.json"
TEXT_SUFFIXES = {".md", ".py", ".ps1", ".json", ".yaml", ".yml", ".svg", ".txt"}
CACHE_SUFFIXES = {".pyc", ".pyo"}


class SyncError(RuntimeError):
    """A safety or validation failure that must stop synchronization."""


def load_manifest() -> dict:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("skills"), dict):
        raise SyncError("sync-manifest.json has an unsupported schema")
    return payload


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hash(root: Path) -> tuple[int, str]:
    files = sorted((path for path in root.rglob("*") if path.is_file()), key=lambda path: path.relative_to(root).as_posix())
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return len(files), digest.hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SyncError(f"{label}: expected one exact match, found {count}")
    return text.replace(old, new, 1)


def replace_regex_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    rendered, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SyncError(f"{label}: expected one pattern match, found {count}")
    return rendered


def transform_building_skill(rel: str, text: str) -> str:
    if rel == "SKILL.md":
        text = replace_regex_once(
            text,
            r"then copy only the final DOCX to `<项目>\\04_审图成果`\.",
            "then copy only the final DOCX to the user-selected deliverables directory.",
            rel,
        )
        text = replace_once(
            text,
            "## Phase References\n\n",
            "## Phase References\n\n- Runtime dependencies and public configuration: `references/runtime-requirements.md`\n",
            rel,
        )
        text = replace_regex_once(
            text,
            r"- Business workspace: `[^`\n]+`\n- Local knowledge base: `[^`\n]+`\n- Project root: `[^`\n]+`",
            "- Set `BUILDING_REVIEW_KNOWLEDGE_BASE` or pass `--knowledge-base <path>` when building a private local index. This public package does not include standards, policies, cases, or project files.\n"
            "- Set `BUILDING_REVIEW_INDEX_DIR` when building the index and `BUILDING_REVIEW_INDEX` when searching or snapshotting it; otherwise the scripts use `./building-review-index` under the current working directory.\n"
            "- Set `BUILDING_REVIEW_PROJECT_ROOT` or pass `--root <path>` for workspace creation; otherwise the script uses `./building-review-projects` under the current working directory.",
            rel,
        )
        return text

    if rel == "references/knowledge-map.md":
        return replace_regex_once(
            text,
            r"Raw knowledge base:\n\n`[A-Za-z]:\\[^`]+`",
            "Raw knowledge base:\n\n`BUILDING_REVIEW_KNOWLEDGE_BASE` or an explicit `--knowledge-base <path>`.\n\n"
            "The public Skill contains indexing and search code only. Users must supply lawfully obtained local standards, policies, review guides, and project-specific materials; none are bundled in this repository.",
            rel,
        )

    if rel == "references/single-building-retrospective.md":
        return text

    if rel == "scripts/build_knowledge_index.py":
        text = replace_once(text, "import logging\nimport re", "import logging\nimport os\nimport re", rel)
        text = replace_regex_once(
            text,
            r'DEFAULT_KNOWLEDGE_BASE = Path\(r"[A-Za-z]:\\[^"\n]+"\)\nDEFAULT_OUTPUT_DIR = SKILL_DIR / "generated"',
            "DEFAULT_KNOWLEDGE_BASE = (\n"
            "    Path(os.environ[\"BUILDING_REVIEW_KNOWLEDGE_BASE\"]).expanduser()\n"
            "    if os.environ.get(\"BUILDING_REVIEW_KNOWLEDGE_BASE\")\n"
            "    else None\n"
            ")\n"
            "DEFAULT_OUTPUT_DIR = Path(\n"
            "    os.environ.get(\"BUILDING_REVIEW_INDEX_DIR\", str(Path.cwd() / \"building-review-index\"))\n"
            ").expanduser()",
            rel,
        )
        return replace_once(
            text,
            "    args = parser.parse_args()\n    if not args.knowledge_base.exists():",
            "    args = parser.parse_args()\n"
            "    if args.knowledge_base is None:\n"
            "        parser.error(\n"
            "            \"pass --knowledge-base or set BUILDING_REVIEW_KNOWLEDGE_BASE; \"\n"
            "            \"this public package does not include standards or project knowledge files\"\n"
            "        )\n"
            "    if not args.knowledge_base.exists():",
            rel,
        )

    if rel == "scripts/create_review_workspace.py":
        text = replace_once(text, "import json\nimport re", "import json\nimport os\nimport re", rel)
        text = replace_regex_once(
            text,
            r'DEFAULT_PROJECT_ROOT = Path\(r"[A-Za-z]:\\[^"\n]+"\)',
            "DEFAULT_PROJECT_ROOT = Path(\n"
            "    os.environ.get(\"BUILDING_REVIEW_PROJECT_ROOT\", str(Path.cwd() / \"building-review-projects\"))\n"
            ").expanduser()",
            rel,
        )
        return replace_once(text, "WARN: using the global project root.", "WARN: using the default project root.", rel)

    if rel == "scripts/search_knowledge.py":
        text = replace_once(text, "import json\nimport sys", "import json\nimport os\nimport sys", rel)
        return replace_once(
            text,
            'DEFAULT_INDEX = SKILL_DIR / "generated" / "knowledge-index.json"',
            "DEFAULT_INDEX = Path(\n"
            "    os.environ.get(\n"
            "        \"BUILDING_REVIEW_INDEX\",\n"
            "        str(Path.cwd() / \"building-review-index\" / \"knowledge-index.json\"),\n"
            "    )\n"
            ").expanduser()",
            rel,
        )

    if rel == "scripts/snapshot_review_integrity.py":
        text = replace_once(text, "import json\nimport sys", "import json\nimport os\nimport sys", rel)
        return replace_once(
            text,
            'DEFAULT_INDEX = SKILL_DIR / "generated" / "knowledge-index.json"',
            "DEFAULT_INDEX = Path(\n"
            "    os.environ.get(\n"
            "        \"BUILDING_REVIEW_INDEX\",\n"
            "        str(Path.cwd() / \"building-review-index\" / \"knowledge-index.json\"),\n"
            "    )\n"
            ").expanduser()",
            rel,
        )

    if rel == "evals/test_v14_workflow.py":
        text = replace_regex_once(
            text,
            r'        oil_workspace = Path\(\n            r"[A-Za-z]:\\[^"\n]+"\n        \)',
            '        oil_workspace = temp / "legacy-v13-workspace"',
            rel,
        )
        return replace_once(
            text,
            '        snapshot = [python, str(SCRIPTS / "snapshot_review_integrity.py"), str(workspace)]',
            "        anonymous_standards = temp / \"anonymous-standards\"\n"
            "        anonymous_standards.mkdir()\n"
            "        index_files = []\n"
            "        for index, standard_source in enumerate(\n"
            "            sorted({check[\"standard_source\"] for check in checks if check.get(\"standard_source\")}), start=1\n"
            "        ):\n"
            "            standard_path = anonymous_standards / f\"standard-{index:03d}.txt\"\n"
            "            standard_path.write_text(\n"
            "                f\"Anonymous regression source for {standard_source}\\n\", encoding=\"utf-8\"\n"
            "            )\n"
            "            index_files.append(\n"
            "                {\n"
            "                    \"name\": Path(standard_source).name,\n"
            "                    \"relative_path\": standard_source,\n"
            "                    \"absolute_path\": str(standard_path.resolve()),\n"
            "                    \"size_bytes\": standard_path.stat().st_size,\n"
            "                    \"sha256\": sha256(standard_path),\n"
            "                }\n"
            "            )\n"
            "        anonymous_index = temp / \"knowledge-index.json\"\n"
            "        anonymous_index.write_text(\n"
            "            json.dumps(\n"
            "                {\n"
            "                    \"schema_version\": \"1.1\",\n"
            "                    \"generated_at\": \"2026-08-12T00:00:00Z\",\n"
            "                    \"corpus_sha256\": hashlib.sha256(\n"
            "                        b\"anonymous-regression-corpus\"\n"
            "                    ).hexdigest(),\n"
            "                    \"total_files\": len(index_files),\n"
            "                    \"specialty_count\": 0,\n"
            "                    \"files\": index_files,\n"
            "                },\n"
            "                ensure_ascii=False,\n"
            "                indent=2,\n"
            "            )\n"
            "            + \"\\n\",\n"
            "            encoding=\"utf-8\",\n"
            "        )\n"
            "        snapshot = [\n"
            "            python,\n"
            "            str(SCRIPTS / \"snapshot_review_integrity.py\"),\n"
            "            str(workspace),\n"
            "            \"--index\",\n"
            "            str(anonymous_index),\n"
            "        ]",
            rel,
        )

    return text


def transform_delivery_skill(rel: str, text: str) -> str:
    if rel == "SKILL.md":
        text = replace_once(
            text,
            "## Progressive Reference Routing\n\n",
            "## Progressive Reference Routing\n\n- Runtime dependencies and public configuration: `references/runtime-requirements.md`\n",
            rel,
        )
        return replace_regex_once(
            text,
            r"- Standalone workspace root: `[^`\n]+`",
            "- Set `REVIEW_OPINION_PROJECT_ROOT` or pass `--root <path>` for workspace creation; otherwise the script uses `./review-opinion-projects` under the current working directory.",
            rel,
        )

    if rel == "references/delivery-style.md":
        return replace_regex_once(
            text,
            r"\A# Word 交付样式\n.*?\n## Page System",
            "# Word 交付样式\n\n"
            "This style contract is distilled from reviewer-approved, anonymized Word references. The public package intentionally omits project paths, source hashes, client names, and identifying document metadata.\n\n"
            "The verified reference set uses a single-section internal-review layout with centered page numbers and evidence images placed next to their approved opinions.\n\n"
            "## Page System",
            rel,
            flags=re.DOTALL,
        )

    if rel == "scripts/create_delivery_workspace.py":
        text = replace_once(text, "import json\nimport re", "import json\nimport os\nimport re", rel)
        return replace_regex_once(
            text,
            r'DEFAULT_ROOT = Path\(r"[A-Za-z]:\\[^"\n]+"\)',
            "DEFAULT_ROOT = Path(\n"
            "    os.environ.get(\"REVIEW_OPINION_PROJECT_ROOT\", str(Path.cwd() / \"review-opinion-projects\"))\n"
            ").expanduser()",
            rel,
        )

    return text


def anonymize_gold_cases(data: bytes) -> bytes:
    payload = json.loads(data.decode("utf-8"))
    anonymous_cases = []
    for index, case in enumerate(payload.get("cases", []), start=1):
        anonymous_cases.append(
            {
                "id": f"GOLD-CANDIDATE-{index:03d}",
                "status": "pending_reviewer_confirmation",
                "report_type": case.get("report_type", "single"),
                "source_paths": [],
                "gold_opinion_candidates": [],
                "approved_gold_path": "",
                "approved_gold_sha256": "",
                "expected_issues": [],
            }
        )
    payload["cases"] = anonymous_cases
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def scrub_xml(name: str, data: bytes) -> bytes:
    if name == "docProps/core.xml":
        for tag in (b"creator", b"lastModifiedBy"):
            pattern = rb"(<(?:[A-Za-z_][\w.-]*:)?" + tag + rb"\b[^>]*>).*?(</(?:[A-Za-z_][\w.-]*:)?" + tag + rb">)"
            data = re.sub(pattern, rb"\1\2", data, flags=re.DOTALL)
    if name == "_rels/.rels":
        data = re.sub(
            rb"<(?:[A-Za-z_][\w.-]*:)?Relationship\b(?=[^>]*(?:custom-properties|docProps/custom\.xml))[^>]*/>",
            b"",
            data,
        )
    if name == "[Content_Types].xml":
        data = re.sub(
            rb"<(?:[A-Za-z_][\w.-]*:)?Override\b(?=[^>]*PartName=(?:\x22|\x27)/docProps/custom\.xml(?:\x22|\x27))[^>]*/>",
            b"",
            data,
        )
    if name.startswith("word/") and name.endswith(".xml"):
        data = data.replace("永州零陵".encode("utf-8"), "某".encode("utf-8"))
        data = re.sub(
            rb"\s+(?:[A-Za-z_][\w.-]*:)?rsid[\w.-]*=(?:\x22[^\x22]*\x22|\x27[^\x27]*\x27)",
            b"",
            data,
        )
    return data


def scrub_docx(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as incoming, zipfile.ZipFile(destination, "w") as outgoing:
        for info in incoming.infolist():
            if info.filename == "docProps/custom.xml":
                continue
            data = incoming.read(info.filename)
            if info.filename.endswith(".xml") or info.filename.endswith(".rels"):
                data = scrub_xml(info.filename, data)
            cloned = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            cloned.compress_type = info.compress_type
            cloned.comment = info.comment
            cloned.extra = info.extra
            cloned.create_system = info.create_system
            cloned.external_attr = info.external_attr
            cloned.internal_attr = info.internal_attr
            outgoing.writestr(cloned, data)


def transform_file(skill: str, rel: str, source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".docx":
        scrub_docx(source, destination)
        return
    data = source.read_bytes()
    if skill == "building-review" and rel == "evals/gold-cases.json":
        destination.write_bytes(anonymize_gold_cases(data))
        return
    if source.suffix.lower() not in TEXT_SUFFIXES:
        destination.write_bytes(data)
        return
    text = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    text = transform_building_skill(rel, text) if skill == "building-review" else transform_delivery_skill(rel, text)
    destination.write_text(text, encoding="utf-8", newline="\n")


def source_files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def validate_source_boundary(source_root: Path, manifest: dict) -> None:
    media_by_skill: dict[str, set[str]] = {}
    for item in manifest.get("media", []):
        media_by_skill.setdefault(item["source_skill"], set()).add(item["source"])
    for skill, config in manifest["skills"].items():
        root = source_root / skill
        if not root.is_dir():
            raise SyncError(f"missing development source: {root}")
        actual = source_files(root)
        approved = set(config["files"]) | set(config.get("ignored_files", [])) | media_by_skill.get(skill, set())
        unknown = sorted(
            rel
            for rel in actual - approved
            if "__pycache__" not in Path(rel).parts and Path(rel).suffix.lower() not in CACHE_SUFFIXES
        )
        if unknown:
            raise SyncError(f"{skill}: new source files require explicit classification:\n- " + "\n- ".join(unknown))
        missing = sorted(rel for rel in config["files"] if rel not in actual)
        if missing:
            raise SyncError(f"{skill}: approved source files are missing:\n- " + "\n- ".join(missing))


def copy_repo_shell(destination: Path) -> None:
    def ignored(_root: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {".git", "__pycache__"} or name.endswith((".pyc", ".pyo"))}

    shutil.copytree(REPO_ROOT, destination, ignore=ignored)


def build_snapshot(source_root: Path, manifest: dict, snapshot: Path) -> None:
    copy_repo_shell(snapshot)
    for skill, config in manifest["skills"].items():
        destination_root = snapshot / skill
        if destination_root.exists():
            shutil.rmtree(destination_root)
        destination_root.mkdir(parents=True)
        for rel in config["files"]:
            transform_file(skill, rel, source_root / skill / Path(rel), destination_root / Path(rel))
        for rel in config.get("public_only", []):
            source = REPO_ROOT / skill / Path(rel)
            if not source.is_file():
                raise SyncError(f"missing public-only file: {source.relative_to(REPO_ROOT)}")
            destination = destination_root / Path(rel)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    for item in manifest.get("media", []):
        source = source_root / item["source_skill"] / Path(item["source"])
        if not source.is_file():
            raise SyncError(f"missing media source: {source}")
        destination = snapshot / Path(item["destination"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def check_python_syntax(root: Path) -> None:
    files = list(root.rglob("*.py"))
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    print(f"PASS: parsed {len(files)} Python files")


def run_checked(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace", capture_output=True)
    output = (result.stdout + result.stderr).strip()
    if output:
        print(output)
    if result.returncode:
        raise SyncError(f"command failed ({result.returncode}): {' '.join(command)}")
    return result


def run_gates(root: Path, manifest: dict) -> None:
    check_python_syntax(root)
    env = dict(os.environ)
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    for arguments in manifest.get("validation_commands", []):
        script = root / Path(arguments[0])
        command = [sys.executable, "-B", str(script), *arguments[1:]]
        run_checked(command, root, env)


def managed_paths(manifest: dict) -> list[Path]:
    paths: list[Path] = []
    for skill, config in manifest["skills"].items():
        paths.extend(Path(skill) / Path(rel) for rel in config["files"] + config.get("public_only", []))
    paths.extend(Path(item["destination"]) for item in manifest.get("media", []))
    return sorted(set(paths), key=lambda path: path.as_posix())


def validate_public_tree(manifest: dict) -> None:
    for skill, config in manifest["skills"].items():
        root = REPO_ROOT / skill
        expected = set(config["files"]) | set(config.get("public_only", []))
        actual = source_files(root)
        unexpected = sorted(actual - expected)
        if unexpected:
            raise SyncError(f"{skill}: public files are outside the managed manifest:\n- " + "\n- ".join(unexpected))
    expected_media = {item["destination"] for item in manifest.get("media", [])}
    actual_media = {path.relative_to(REPO_ROOT).as_posix() for path in (REPO_ROOT / "media").rglob("*") if path.is_file()}
    unexpected_media = sorted(actual_media - expected_media)
    if unexpected_media:
        raise SyncError("media: public files are outside the managed manifest:\n- " + "\n- ".join(unexpected_media))


def changes(snapshot: Path, manifest: dict) -> list[tuple[str, Path]]:
    result: list[tuple[str, Path]] = []
    for rel in managed_paths(manifest):
        current = REPO_ROOT / rel
        proposed = snapshot / rel
        if not current.exists():
            result.append(("ADD", rel))
        elif sha256(current) != sha256(proposed):
            result.append(("UPDATE", rel))
    return result


def apply_snapshot(snapshot: Path, changed: list[tuple[str, Path]]) -> None:
    for _action, rel in changed:
        source = snapshot / rel
        destination = REPO_ROOT / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def executable(value: str | None, fallback: str) -> str:
    candidate = value or shutil.which(fallback)
    if not candidate:
        raise SyncError(f"required executable not found: {fallback}")
    return str(candidate)


def git_output(git: str, *arguments: str) -> str:
    result = run_checked([git, "-C", str(REPO_ROOT), *arguments], REPO_ROOT)
    return result.stdout.strip()


def publish(git_value: str | None, gh_value: str | None, message: str, actions_timeout: int) -> None:
    git = executable(git_value, "git")
    gh = executable(gh_value, "gh")
    branch = git_output(git, "branch", "--show-current")
    if branch != "main":
        raise SyncError(f"automatic public synchronization requires main, found {branch}")
    changed_lines = git_output(git, "status", "--porcelain").splitlines()
    allowed_prefixes = ("building-review/", "review-opinion-delivery/", "media/")
    unrelated = [line for line in changed_lines if line[3:].replace("\\", "/").strip('"') and not line[3:].replace("\\", "/").strip('"').startswith(allowed_prefixes)]
    if unrelated:
        raise SyncError("refusing to publish unrelated working-tree changes:\n" + "\n".join(unrelated))
    if not changed_lines:
        print("PASS: public repository already matches the approved development sources")
        return
    run_checked([git, "-C", str(REPO_ROOT), "add", "--", *allowed_prefixes], REPO_ROOT)
    run_checked([git, "-C", str(REPO_ROOT), "commit", "-m", message], REPO_ROOT)
    run_checked([git, "-C", str(REPO_ROOT), "push", "origin", "main"], REPO_ROOT)
    head = git_output(git, "rev-parse", "HEAD")
    repo = run_checked([gh, "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], REPO_ROOT).stdout.strip()
    deadline = time.monotonic() + actions_timeout
    while time.monotonic() < deadline:
        raw = run_checked(
            [gh, "run", "list", "--repo", repo, "--commit", head, "--limit", "10", "--json", "status,conclusion,url,workflowName"],
            REPO_ROOT,
        ).stdout
        runs = [item for item in json.loads(raw or "[]") if item.get("workflowName") == "Validate Skills"]
        if runs:
            run = runs[0]
            if run.get("status") == "completed":
                if run.get("conclusion") != "success":
                    raise SyncError(f"GitHub Actions failed: {run.get('url', '')}")
                print(f"PASS: GitHub Actions succeeded: {run.get('url', '')}")
                return
        time.sleep(5)
    raise SyncError("timed out waiting for Validate Skills GitHub Actions")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=os.environ.get("KANGMAOJIAN_SKILLS_SOURCE_ROOT"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate and report changes without writing")
    mode.add_argument("--apply", action="store_true", help="apply the validated public snapshot")
    parser.add_argument("--publish", action="store_true", help="commit, push main, and wait for GitHub Actions")
    parser.add_argument("--message", default="Sync public architectural review skills")
    parser.add_argument("--git-executable")
    parser.add_argument("--gh-executable")
    parser.add_argument("--actions-timeout", type=int, default=600)
    args = parser.parse_args()
    if args.source_root is None:
        parser.error("pass --source-root or set KANGMAOJIAN_SKILLS_SOURCE_ROOT")
    if args.publish and not args.apply:
        parser.error("--publish requires --apply")

    source_root = args.source_root.expanduser().resolve()
    manifest = load_manifest()
    before = {skill: tree_hash(source_root / skill) for skill in manifest["skills"]}
    try:
        validate_source_boundary(source_root, manifest)
        validate_public_tree(manifest)
        with tempfile.TemporaryDirectory(prefix="kangmaojian-public-sync-") as temp_value:
            snapshot = Path(temp_value) / "repo"
            build_snapshot(source_root, manifest, snapshot)
            run_gates(snapshot, manifest)
            changed = changes(snapshot, manifest)
            if changed:
                for action, rel in changed:
                    print(f"{action}: {rel.as_posix()}")
            else:
                print("NO CHANGES")
            if args.apply:
                apply_snapshot(snapshot, changed)
                run_gates(REPO_ROOT, manifest)
        after = {skill: tree_hash(source_root / skill) for skill in manifest["skills"]}
        if before != after:
            raise SyncError("development source content changed during synchronization")
        for skill, (count, digest) in after.items():
            print(f"SOURCE UNCHANGED: {skill} files={count} sha256={digest.upper()}")
        if args.publish:
            publish(args.git_executable, args.gh_executable, args.message, args.actions_timeout)
        print("PASS: safe public Skill synchronization completed")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, SyncError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
