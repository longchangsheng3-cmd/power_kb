from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    "基本信息",
    "问题现象",
    "输入材料",
    "关键证据",
    "分析过程",
    "可能原因排序",
    "根因候选",
    "优化方案候选",
    "验证建议",
    "人工复核清单",
    "关联知识",
]


def has_section(markdown: str, heading: str) -> bool:
    return re.search(rf"^## {re.escape(heading)}\s*$", markdown, re.MULTILINE) is not None


def has_p1(markdown: str) -> bool:
    return "| P1 |" in markdown


def count_pending(markdown: str) -> int:
    return markdown.count("待补充")


def has_frontmatter(markdown: str) -> bool:
    return markdown.startswith("---\n") and "\n---" in markdown[4:]


def build_review(markdown: str) -> tuple[int, list[str]]:
    score = 100
    findings: list[str] = []

    if not has_frontmatter(markdown):
        score -= 10
        findings.append("缺少 frontmatter 元数据。")

    for section in REQUIRED_SECTIONS:
        if not has_section(markdown, section):
            score -= 8
            findings.append(f"缺少章节：{section}")

    pending_count = count_pending(markdown)
    if pending_count:
        penalty = min(30, pending_count * 3)
        score -= penalty
        findings.append(f"仍有 {pending_count} 处 `待补充`，建议入库前补齐。")

    if not has_p1(markdown):
        score -= 15
        findings.append("未发现 P1 原因排序。")

    if "- [ ]" in markdown:
        findings.append("存在未勾选入库前待确认项，请人工确认。")

    if "关联知识" in markdown and "docs/" not in markdown:
        score -= 10
        findings.append("关联知识未引用 docs/ 来源。")

    score = max(0, score)
    if not findings:
        findings.append("草稿结构完整，未发现明显缺失。")
    return score, findings


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Review a generated case draft before confirmation.")
    parser.add_argument("draft", type=Path, help="Case draft Markdown file.")
    parser.add_argument("--min-score", type=int, default=70, help="Minimum score considered acceptable.")
    args = parser.parse_args()

    if not args.draft.exists():
        raise SystemExit(f"Draft file not found: {args.draft}")

    markdown = args.draft.read_text(encoding="utf-8")
    score, findings = build_review(markdown)

    print("# 案例草稿质量检查")
    print()
    print(f"文件：{args.draft}")
    print(f"评分：{score}/100")
    print()
    print("## 检查结果")
    print()
    for finding in findings:
        print(f"- {finding}")

    if score < args.min_score:
        raise SystemExit(f"Draft score {score} is below minimum {args.min_score}.")


if __name__ == "__main__":
    main()
