from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "outputs" / "analysis" / "case_draft.md"


def extract_section(markdown: str, heading: str) -> str:
    pattern = re.compile(rf"## {re.escape(heading)}\n\n(?P<body>.*?)(?=\n## |\Z)", re.DOTALL)
    match = pattern.search(markdown)
    return match.group("body").strip() if match else "待补充。"


def extract_sources(rag_text: str) -> list[str]:
    sources: list[str] = []
    for line in rag_text.splitlines():
        if line.startswith("来源："):
            source = line.replace("来源：", "", 1).strip()
            if source and source not in sources:
                sources.append(source)
    return sources


def first_table_row(markdown: str, heading: str) -> list[str]:
    section = extract_section(markdown, heading)
    for line in section.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        columns = [column.strip() for column in line.strip("|").split("|")]
        if columns and columns[0] not in {"优先级", "分类", "Wake lock", "Wakeup source"}:
            return columns
    return []


def extract_log_summary(log_text: str) -> str:
    active = extract_section(log_text, "Top Active Wake Locks")
    pending = extract_section(log_text, "Top Pending Wakeup Sources")
    usb = extract_section(log_text, "USB/Type-C/Charging 代表性证据")
    return "\n\n".join(
        [
            "### Top Active Wake Locks",
            active,
            "### Top Pending Wakeup Sources",
            pending,
            "### USB/Type-C/Charging 代表性证据",
            usb,
        ]
    ).strip()


def infer_tags(title: str, conclusion: str) -> list[str]:
    text = f"{title}\n{conclusion}".lower()
    tags = ["standby"]
    mapping = {
        "wakelock": "wakelock",
        "wake lock": "wakelock",
        "usb": "usb",
        "type-c": "type-c",
        "typec": "type-c",
        "charger": "charger",
        "wlan": "wlan",
        "wifi": "wifi",
        "modem": "modem",
        "suspend": "suspend",
    }
    for keyword, tag in mapping.items():
        if keyword in text and tag not in tags:
            tags.append(tag)
    return tags


def build_frontmatter(title: str, platform: str, source_log: str, tags: list[str]) -> str:
    tag_lines = "\n".join(f"  - {tag}" for tag in tags)
    return f"""---
status: draft
title: {title}
tags:
{tag_lines}
platform: {platform or '待补充'}
source_log: {source_log or '待补充'}
created_at: {date.today().isoformat()}
---"""


def build_case_draft(
    title: str,
    issue: str,
    source_log: str,
    conclusion_text: str,
    log_text: str,
    rag_text: str,
    platform: str,
    software_version: str,
    hardware_version: str,
    scenario: str,
    expected_current: str,
    measured_current: str,
) -> str:
    summary = extract_section(conclusion_text, "结论摘要")
    causes = extract_section(conclusion_text, "可能原因排序")
    review = extract_section(conclusion_text, "人工复核清单")
    validation = extract_section(conclusion_text, "建议验证实验")
    rag_sources = extract_sources(rag_text)
    p1 = first_table_row(conclusion_text, "可能原因排序")
    root_candidate = p1[1] if len(p1) > 1 else "待补充"
    evidence_candidate = p1[2] if len(p1) > 2 else "待补充"
    tags = infer_tags(title, conclusion_text)

    related = "\n".join(f"- {source}" for source in rag_sources) if rag_sources else "- 待补充"
    log_summary = extract_log_summary(log_text) if log_text else "待补充"

    return f"""{build_frontmatter(title, platform, source_log, tags)}

# 案例：{title}

## 基本信息

- 平台：{platform or '待补充'}
- 软件版本：{software_version or '待补充'}
- 硬件版本：{hardware_version or '待补充'}
- 测试场景：{scenario or '待补充'}
- 期望电流：{expected_current or '待补充'}
- 实测电流：{measured_current or '待补充'}
- 草稿日期：{date.today().isoformat()}
- 状态：draft

## 问题现象

{issue}

## 输入材料

- 日志：{source_log or '待补充'}
- 日志辅助分析：自动生成
- RAG 检索结果：自动生成
- 结构化结论：自动生成

## 关键证据

{log_summary}

## 分析过程

{summary}

## 可能原因排序

{causes}

## 根因候选

{root_candidate}

依据：{evidence_candidate}

## 优化方案候选

- 如果确认与 USB/Type-C/Charging 相关，优先检查 USB controller、Type-C 检测、充电策略和调试连接是否符合待机场景。
- 如果复测后 USB wake lock 消失，进一步定位连接状态、驱动引用计数和 wakeup source 配置。
- 如果复测后异常仍存在，继续分析次优先级 wake lock 或 pending wakeup source。

## 验证建议

{validation}

## 人工复核清单

{review}

## 关联知识

{related}

## 入库前待确认

- [ ] 平台、版本、测试场景、电流数据已补充。
- [ ] P1 根因已由人工确认。
- [ ] 优化方案或验证实验已确认。
- [ ] 关联知识来源准确。
"""


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Generate an editable case draft from V0.3.1 analysis outputs.")
    parser.add_argument("--title", required=True, help="Case title.")
    parser.add_argument("--issue", required=True, help="Original issue description.")
    parser.add_argument("--source-log", default="", help="Source log file path or description.")
    parser.add_argument("--conclusion", type=Path, required=True, help="Structured conclusion Markdown file.")
    parser.add_argument("--log-extract", type=Path, required=True, help="Log extract Markdown file.")
    parser.add_argument("--rag-result", type=Path, required=True, help="RAG result Markdown file.")
    parser.add_argument("--platform", default="", help="Platform.")
    parser.add_argument("--software-version", default="", help="Software version.")
    parser.add_argument("--hardware-version", default="", help="Hardware version.")
    parser.add_argument("--scenario", default="", help="Test scenario.")
    parser.add_argument("--expected-current", default="", help="Expected standby current.")
    parser.add_argument("--measured-current", default="", help="Measured standby current.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output draft path.")
    args = parser.parse_args()

    for path in [args.conclusion, args.log_extract, args.rag_result]:
        if not path.exists():
            raise SystemExit(f"Input file not found: {path}")

    draft = build_case_draft(
        title=args.title,
        issue=args.issue,
        source_log=args.source_log,
        conclusion_text=args.conclusion.read_text(encoding="utf-8"),
        log_text=args.log_extract.read_text(encoding="utf-8"),
        rag_text=args.rag_result.read_text(encoding="utf-8"),
        platform=args.platform,
        software_version=args.software_version,
        hardware_version=args.hardware_version,
        scenario=args.scenario,
        expected_current=args.expected_current,
        measured_current=args.measured_current,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(draft, encoding="utf-8")
    print(f"Wrote case draft to {args.output}")


if __name__ == "__main__":
    main()
