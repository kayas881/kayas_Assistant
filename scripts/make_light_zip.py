from __future__ import annotations

import argparse
import os
from pathlib import Path
import time
import zipfile
from typing import Iterable, Set, Tuple, Dict

# Default exclude directories and file patterns suitable for AI-friendly sharing
DEFAULT_EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "ENV", "env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".playwright",
    "dist", "build", "site", "docs/_build", "doc", "docs_output",
    "artifacts", ".agent", "playwright-report", "test-results", "screenshots", "recordings",
    # ML/data/model caches
    ".cache", "cache", "hf_cache", "huggingface", ".huggingface", "datasets", "data",
    "wandb", "lightning_logs", "runs", "checkpoints", "outputs", "models", "saved_models", "adapters",
    # Common non-Python
    "node_modules",
}

DEFAULT_EXCLUDE_GLOBS = {
    # Large/binary artifacts
    "*.zip", "*.tar", "*.tar.gz", "*.tgz", "*.gz", "*.7z", "*.rar",
    "*.safetensors", "*.bin", "*.pt", "*.onnx",
    # Non-essential docs/assets (AI doesn't need to render these)
    "*.pdf", "*.docx", "*.pptx", "*.xlsx", "*.xls", "*.html", "*.epub", "*.chm",
    # OS / editor
    "*.log", "*.bak", "*.old", "*.orig",
}

# Always include some critical top-level files even if in excluded locations
ALWAYS_INCLUDE = {
    "README.md", "requirements.txt", "pyproject.toml", "setup.cfg", "setup.py", "kayas.py",
}

# Markdown inclusion policy: Include only top-level READMEs and key subdirectory READMEs.
# These are essential for AI assistants to understand the project structure and purpose.
# Top-level README.md explains the entire project, brain_training/README.md explains the training pipeline.
DEFAULT_ALLOWED_MD = {"README.md"}  # Matches any README.md anywhere in the tree

TEXT_EXT_WHITELIST = {
    ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".ini", ".cfg", ".toml", ".csv",
}


def should_exclude_path(root: Path, path: Path, exclude_dirs: Set[str], exclude_globs: Set[str]) -> Tuple[bool, str]:
    # Exclude if any parent directory matches excluded set
    for part in path.relative_to(root).parts[:-1]:
        if part in exclude_dirs:
            return True, f"dir:{part}"
    # Exclude by glob
    from fnmatch import fnmatch
    name = path.name
    for pat in exclude_globs:
        if fnmatch(name, pat):
            return True, f"glob:{pat}"
    return False, ""


def collect_files(root: Path, max_bytes: int, exclude_dirs: Set[str], exclude_globs: Set[str], allowed_md: Set[str]) -> Tuple[Iterable[Path], Dict[str, int]]:
    included = []
    stats = {"included": 0, "excluded": 0, "too_big": 0, "md_excluded": 0, "md_included": 0}

    for p in root.rglob("*"):
        if p.is_dir():
            # Skip excluded directories quickly
            parts = p.relative_to(root).parts
            if any(part in exclude_dirs for part in parts):
                continue
            else:
                continue  # directories are not added; files handled below
        # Prefer including source and config files
        rel = p.relative_to(root)
        if rel.parts and rel.parts[0] in exclude_dirs:
            stats["excluded"] += 1
            continue
        # Always include specific top-level files
        if rel.name in ALWAYS_INCLUDE and len(rel.parts) == 1:
            if p.stat().st_size <= max_bytes:
                included.append(p)
                stats["included"] += 1
            else:
                stats["too_big"] += 1
            continue
        # Markdown filtering: include only whitelisted .md files by name
        if p.suffix.lower() == ".md":
            if rel.name in allowed_md:
                included.append(p)
                stats["included"] += 1
                stats["md_included"] += 1
            else:
                stats["md_excluded"] += 1
            continue
        # Exclude by pattern
        excluded, reason = should_exclude_path(root, p, exclude_dirs, exclude_globs)
        if excluded:
            stats["excluded"] += 1
            continue
        # Enforce size threshold except for small text/code files which are usually small anyway
        size = p.stat().st_size
        if size > max_bytes:
            # allow slightly larger if it's a whitelisted text/code file up to 2x max
            if p.suffix.lower() in TEXT_EXT_WHITELIST and size <= max_bytes * 2:
                included.append(p)
                stats["included"] += 1
            else:
                stats["too_big"] += 1
            continue
        included.append(p)
        stats["included"] += 1
    return included, stats


def make_zip(output: Path, files: Iterable[Path], root: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            arcname = str(p.relative_to(root))
            zf.write(p, arcname)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a light ZIP of the project, excluding big or irrelevant files for AI analysis.")
    parser.add_argument("--max-mb", type=float, default=2.0, help="Max file size (in MB) to include; text code files may be allowed up to 2x.")
    parser.add_argument("--root", type=str, default=str(Path(__file__).resolve().parents[1]), help="Project root directory.")
    parser.add_argument("--out", type=str, default="", help="Output zip path. Default: artifacts/<name>-light-YYYYmmdd-HHMM.zip")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be included.")
    parser.add_argument("--include-md", type=str, default="", help="Comma-separated list of additional Markdown file names to include (by name, anywhere). Example: ARCHITECTURE.md,ROADMAP.md")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root does not exist: {root}")
        return 2

    project_name = root.name
    ts = time.strftime("%Y%m%d-%H%M")
    out = Path(args.out) if args.out else (root / "artifacts" / f"{project_name}-light-{ts}.zip")

    max_bytes = int(args.max_mb * 1024 * 1024)

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    exclude_globs = set(DEFAULT_EXCLUDE_GLOBS)

    allowed_md = set(DEFAULT_ALLOWED_MD)
    if args.include_md:
        extra = [s.strip() for s in args.include_md.split(",") if s.strip()]
        allowed_md.update(extra)

    # Collect files
    files, stats = collect_files(root, max_bytes, exclude_dirs, exclude_globs, allowed_md)

    total_size = sum(p.stat().st_size for p in files)
    print(f"Including {len(files)} files (~{total_size/1024:.1f} KB). Excluded: {stats['excluded']}, too big: {stats['too_big']}. MD included: {stats['md_included']}, MD excluded: {stats['md_excluded']}.")

    # Show a quick preview of top-level included groups
    preview = [str(p.relative_to(root)) for p in files if p.suffix.lower() in TEXT_EXT_WHITELIST][:20]
    if preview:
        print("Sample included files:")
        for s in preview:
            print(" -", s)

    if args.dry_run:
        print("Dry-run: no archive created.")
        return 0

    make_zip(out, files, root)
    print(f"Wrote: {out}")

    # Also write a small pack report
    try:
        report_path = root / "artifacts" / "pack_report.txt"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as f:
            f.write(f"Output: {out}\n")
            f.write(f"Included files: {len(files)}\n")
            f.write(f"Approx size: {total_size} bytes\n")
            f.write("\nFirst 50 files:\n")
            for p in [str(p.relative_to(root)) for p in files][:50]:
                f.write(p + "\n")
        print(f"Report: {report_path}")
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
