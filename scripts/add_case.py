from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "cases" / "template.md"
CASES_DIR = ROOT / "docs" / "cases"


def slugify(title: str) -> str:
    allowed = []
    for char in title.lower().strip():
        if char.isalnum():
            allowed.append(char)
        elif char in {" ", "-", "_"}:
            allowed.append("-")
    slug = "".join(allowed).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "standby-case"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new standby power case from template.")
    parser.add_argument("title", help="Case title.")
    args = parser.parse_args()

    today = date.today().strftime("%Y%m%d")
    path = CASES_DIR / f"{today}-{slugify(args.title)}.md"
    if path.exists():
        raise SystemExit(f"Case already exists: {path}")

    content = TEMPLATE.read_text(encoding="utf-8").replace("<问题标题>", args.title)
    path.write_text(content, encoding="utf-8")
    print(f"Created {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
