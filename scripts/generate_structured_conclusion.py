from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TableRow:
    columns: tuple[str, ...]


def parse_markdown_table(markdown: str, heading: str) -> list[TableRow]:
    lines = markdown.splitlines()
    rows: list[TableRow] = []
    in_section = False

    for line in lines:
        if line.startswith("## "):
            in_section = line.strip() == f"## {heading}"
            continue
        if not in_section:
            continue
        if line.startswith("## "):
            break
        if not line.startswith("|") or "---" in line:
            continue
        columns = tuple(column.strip() for column in line.strip("|").split("|"))
        if columns and columns[0] not in {"Wake lock", "Wakeup source", "Reason", "分类"}:
            rows.append(TableRow(columns))
    return rows


def parse_sources(rag_text: str) -> list[str]:
    sources: list[str] = []
    for line in rag_text.splitlines():
        if line.startswith("来源："):
            source = line.replace("来源：", "", 1).strip()
            if source and source not in sources:
                sources.append(source)
    return sources


def parse_category_counts(log_text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in parse_markdown_table(log_text, "分类统计"):
        if len(row.columns) >= 2 and row.columns[1].isdigit():
            counts[row.columns[0]] = int(row.columns[1])
    return counts


def build_findings(log_text: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    wake_locks = parse_markdown_table(log_text, "Top Active Wake Locks")
    pending_sources = parse_markdown_table(log_text, "Top Pending Wakeup Sources")
    categories = parse_category_counts(log_text)

    if wake_locks:
        top = wake_locks[0].columns
        findings.append(
            {
                "priority": "P1",
                "title": f"{top[0]} 长时间持有 wake lock",
                "evidence": f"Top Active Wake Locks 显示样本数 {top[1]}，最长 active_since {top[2]}，最大 active_count {top[3]}。",
                "next_step": "检查该 wake lock 对应驱动/子系统是否符合待机场景，确认是否应释放或降频。",
            }
        )

    if pending_sources:
        top = pending_sources[0].columns
        priority = "P1" if not findings else "P2"
        findings.append(
            {
                "priority": priority,
                "title": f"{top[0]} 重复出现在 Pending Wakeup Sources",
                "evidence": f"Top Pending Wakeup Sources 显示出现 {top[1]} 次。",
                "next_step": "结合 wakeup source 统计和驱动日志确认该源是否反复阻塞 suspend 或唤醒系统。",
            }
        )

    if categories.get("usb", 0) or categories.get("charger", 0):
        findings.append(
            {
                "priority": "P2",
                "title": "USB/Type-C/Charging 状态可能影响待机功耗",
                "evidence": f"分类统计 usb={categories.get('usb', 0)}，charger={categories.get('charger', 0)}。",
                "next_step": "确认测试是否连接 USB/充电器；若是纯待机测试，建议拔线复测并对比 wake lock。",
            }
        )

    if categories.get("network", 0):
        findings.append(
            {
                "priority": "P3",
                "title": "网络日志命中较多但需结合具体 wake lock 判断",
                "evidence": f"分类统计 network={categories.get('network', 0)}。",
                "next_step": "检查是否存在 wlan/modem 相关 active wake lock；没有时不要直接归因为网络。",
            }
        )

    return findings


def build_conclusion(issue: str, log_extract: Path, rag_result: Path, output_case_hint: bool) -> str:
    log_text = log_extract.read_text(encoding="utf-8")
    rag_text = rag_result.read_text(encoding="utf-8") if rag_result.exists() else ""
    findings = build_findings(log_text)
    sources = parse_sources(rag_text)

    lines = [
        "# 结构化分析结论",
        "",
        "## 结论摘要",
        "",
    ]

    if findings:
        lines.append(f"最可疑方向：{findings[0]['title']}。该结论基于 V0.3.1 日志聚合结果生成，需要人工结合测试场景确认。")
    else:
        lines.append("未从日志聚合结果中识别出明确 Top wake lock 或 wakeup source，需要补充 wakeup_sources、suspend_stats 和电流曲线。")

    lines.extend(
        [
            "",
            "## 已知问题",
            "",
            f"- {issue}",
            "",
            "## 可能原因排序",
            "",
            "| 优先级 | 可能原因 | 关键依据 | 下一步验证 |",
            "|---|---|---|---|",
        ]
    )

    if findings:
        for finding in findings:
            lines.append(f"| {finding['priority']} | {finding['title']} | {finding['evidence']} | {finding['next_step']} |")
    else:
        lines.append("| P1 | 待补充 | 日志中缺少明确聚合证据 | 补充 wakeup_sources、suspend_stats、电流曲线 |")

    lines.extend(["", "## RAG 参考知识", ""])
    if sources:
        for source in sources:
            lines.append(f"- {source}")
    else:
        lines.append("- 未提供 RAG 检索结果。")

    lines.extend(
        [
            "",
            "## 人工复核清单",
            "",
            "- 确认测试场景是否允许 USB/充电器连接。",
            "- 对比拔掉 USB/充电器后的待机电流和 wake lock。",
            "- 补充 `/sys/kernel/debug/wakeup_sources` 和 `/sys/power/suspend_stats`。",
            "- 对比正常样机同一场景下的 Top wake locks 和 Pending Wakeup Sources。",
            "- 确认日志时间段是否覆盖完整待机异常窗口。",
            "",
            "## 建议验证实验",
            "",
            "1. 纯电池、断开 USB/Type-C 后复测待机电流。",
            "2. 若异常消失，进一步定位 USB controller、Type-C 检测、充电策略或调试连接。",
            "3. 若异常仍存在，继续分析第二优先级 wake lock/wakeup source。",
        ]
    )

    if output_case_hint:
        lines.extend(
            [
                "",
                "## 确认后入库建议",
                "",
                "人工确认结论正确后，可使用 `scripts/confirm_case.py` 将本结论沉淀为 `docs/cases/` 案例，然后运行 `python rag/ingest.py` 更新向量库。",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Generate a structured standby power conclusion for human review.")
    parser.add_argument("--issue", required=True, help="Issue description.")
    parser.add_argument("--log-extract", type=Path, required=True, help="Markdown log extract generated by analyze_log.py.")
    parser.add_argument("--rag-result", type=Path, required=True, help="Markdown RAG result generated by rag/query.py.")
    parser.add_argument("--output", type=Path, required=True, help="Output Markdown conclusion path.")
    parser.add_argument("--case-hint", action="store_true", help="Append instructions for confirmed case ingestion.")
    args = parser.parse_args()

    if not args.log_extract.exists():
        raise SystemExit(f"Log extract not found: {args.log_extract}")

    conclusion = build_conclusion(args.issue, args.log_extract, args.rag_result, args.case_hint)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(conclusion, encoding="utf-8")
    print(f"Wrote structured conclusion to {args.output}")


if __name__ == "__main__":
    main()
