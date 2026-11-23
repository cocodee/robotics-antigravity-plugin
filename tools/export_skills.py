#!/usr/bin/env python3
"""Export a flat, agent-neutral skill bundle with local rule references."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins" / "robotics"


def export(destination: Path) -> int:
    destination = destination.expanduser().resolve()
    # Never overwrite an installation or export into source directories.
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination}; choose a new directory")
    if destination == REPO or destination in REPO.parents or PLUGIN in destination.parents:
        raise ValueError("Destination must not overlap plugin sources or repository ancestors")
    skills = sorted((PLUGIN / "skills").iterdir())
    destination.mkdir(parents=True)
    for source in skills:
        if not (source / "SKILL.md").is_file():
            continue
        target = destination / source.name
        shutil.copytree(source, target, ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".venv", ".pytest_cache", "*.egg-info"))
        # Each exported skill carries its referenced rules. Sibling skills are
        # still required by composed workflows, so export the complete set.
        rules = target / "references" / "shared-rules"
        shutil.copytree(PLUGIN / "rules", rules)
        for doc in target.rglob("*.md"):
            content = doc.read_text()
            if rules in doc.parents:
                content = content.replace("../skills/", "../../../")
            else:
                content = content.replace("../../rules/", "references/shared-rules/")
            doc.write_text(content)
    shutil.copy2(REPO / "LICENSE", destination / "LICENSE")
    return sum((p / "SKILL.md").is_file() for p in destination.iterdir() if p.is_dir())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="New directory containing the exported skill folders")
    args = parser.parse_args()
    try:
        count = export(args.output)
    except ValueError as error:
        parser.error(str(error))
    print(f"Exported {count} skills to {args.output.expanduser().resolve()}")


if __name__ == "__main__":
    main()
