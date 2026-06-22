from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "docs" / "cases"


def slugify(title: str) -> str:
    allowed = []
    for char in title.lower().strip():
        if char.isalnum():
            allowed.append(char)
        elif char in {" ", "-", "_", "：", ":"}:
            allowed.append("-")
    slug = "".join(allowed).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "confirmed-standby-case"


def first_heading_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# 案例："):
            return line.replace("# 案例：", "", 1).strip()
        if line.startswith("# "):
            return line.replace("# ", "", 1).strip()
    return "confirmed-standby-case"


def first_summary(conclusion: str) -> str:
    lines = conclusion.splitlines()
    in_summary = False
    for line in lines:
        if line.strip() == "## 结论摘要":
            in_summary = True
            continue
        if in_summary and line.startswith("## "):
            break
        if in_summary and line.strip():
            return line.strip()
    return "人工确认的待机功耗分析结论。"


def extract_table_section(markdown: str, heading: str) -> str:
    pattern = re.compile(rf"## {re.escape(heading)}\n\n(?P<body>.*?)(?=\n## |\Z)", re.DOTALL)
    match = pattern.search(markdown)
    return match.group("body").strip() if match else "待补充。"


def strip_frontmatter(markdown: str) -> str:
    if markdown.startswith("---\n"):
        end = markdown.find("\n---", 4)
        if end != -1:
            return markdown[end + len("\n---") :].lstrip()
    return markdown


def mark_confirmed(markdown: str, reviewer: str) -> str:
    body = strip_frontmatter(markdown)
    today = date.today().isoformat()
    frontmatter = f"""---
status: confirmed
confirmed_at: {today}
reviewer: {reviewer or '待补充'}
---"""
    body = body.replace("- 状态：draft", "- 状态：confirmed")
    body = body.replace("status: draft", "status: confirmed")
    if "## 人工复核记录" not in body and "## 人工复核清单" in body:
        body = body.replace("## 人工复核清单", "## 人工复核记录")
    return f"{frontmatter}\n\n{body.rstrip()}\n"


def build_case(title: str, conclusion: str, issue: str, source_log: str, reviewer: str) -> str:
    today = date.today().isoformat()
    summary = first_summary(conclusion)
    causes = extract_table_section(conclusion, "可能原因排序")
    review_checklist = extract_table_section(conclusion, "人工复核清单")
    validation = extract_table_section(conclusion, "建议验证实验")
    rag_sources = extract_table_section(conclusion, "RAG 参考知识")

    return f"""---
status: confirmed
confirmed_at: {today}
reviewer: {reviewer or '待补充'}
---

# 案例：{title}

## 基本信息

- 平台：待补充
- 软件版本：待补充
- 硬件版本：待补充
- 测试场景：待补充
- 期望电流：待补充
- 实测电流：待补充
- 确认日期：{today}
- 复核人：{reviewer or '待补充'}

## 问题现象

{issue}

## 输入材料

- 日志：{source_log or '待补充'}
- 结构化分析结论：人工确认后入库

## 分析过程

{summary}

## 可能原因排序

{causes}

## 根因

待人工补充最终根因。如果已确认，可将 P1 结论整理为根因。

## 优化方案

待人工补充实际修改、配置调整或规避方案。

## 验证结果

{validation}

## 人工复核记录

{review_checklist}

## 关联知识

{rag_sources}
"""


def resolve_output(output: Path | None, title: str) -> Path:
    return (output or CASES_DIR / f"{date.today().strftime('%Y%m%d')}-{slugify(title)}.md").resolve()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Store a human-confirmed case in the knowledge base.")
    parser.add_argument("--confirmed", action="store_true", help="Required. Indicates human review confirmed the conclusion or draft.")
    parser.add_argument("--from-draft", type=Path, help="Confirmed case draft Markdown file.")
    parser.add_argument("--title", help="Case title.")
    parser.add_argument("--issue", help="Original issue description.")
    parser.add_argument("--conclusion", type=Path, help="Structured conclusion Markdown file.")
    parser.add_argument("--source-log", default="", help="Source log file path or description.")
    parser.add_argument("--reviewer", default="", help="Human reviewer name.")
    parser.add_argument("--output", type=Path, help="Optional output case path. Defaults to docs/cases/<date>-<slug>.md.")
    args = parser.parse_args()

    if not args.confirmed:
        raise SystemExit("Refusing to store unconfirmed analysis. Re-run with --confirmed after human review.")

    if args.from_draft:
        if not args.from_draft.exists():
            raise SystemExit(f"Draft file not found: {args.from_draft}")
        draft = args.from_draft.read_text(encoding="utf-8")
        title = args.title or first_heading_title(draft)
        output = resolve_output(args.output, title)
        if output.exists():
            raise SystemExit(f"Case already exists: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(mark_confirmed(draft, args.reviewer), encoding="utf-8")
        print(f"Stored confirmed draft case at {output.relative_to(ROOT)}")
        print("Next step: run `python rag/ingest.py` to update the local vector store.")
        return

    if not args.title or not args.issue or not args.conclusion:
        raise SystemExit("--title, --issue, and --conclusion are required unless --from-draft is used.")
    if not args.conclusion.exists():
        raise SystemExit(f"Conclusion file not found: {args.conclusion}")

    conclusion = args.conclusion.read_text(encoding="utf-8")
    output = resolve_output(args.output, args.title)
    if output.exists():
        raise SystemExit(f"Case already exists: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_case(args.title, conclusion, args.issue, args.source_log, args.reviewer), encoding="utf-8")
    print(f"Stored confirmed case at {output.relative_to(ROOT)}")
    print("Next step: run `python rag/ingest.py` to update the local vector store.")


if __name__ == "__main__":
    main()
