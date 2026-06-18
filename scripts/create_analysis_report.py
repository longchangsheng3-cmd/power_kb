from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def extract_sources(markdown: str) -> list[str]:
    sources = []
    for line in markdown.splitlines():
        if line.startswith("来源："):
            source = line.replace("来源：", "", 1).strip()
            if source and source not in sources:
                sources.append(source)
    return sources


def extract_categories(markdown: str) -> list[str]:
    categories = []
    for line in markdown.splitlines():
        match = re.match(r"\| ([^|]+) \|\s*(\d+) \|", line)
        if match and match.group(1) not in {"分类", "无"}:
            categories.append(f"{match.group(1)}：{match.group(2)}")
    return categories


def build_report(issue: str, context_file: Path | None, log_extract: Path | None, rag_result: Path | None) -> str:
    log_text = log_extract.read_text(encoding="utf-8") if log_extract and log_extract.exists() else ""
    rag_text = rag_result.read_text(encoding="utf-8") if rag_result and rag_result.exists() else ""
    context_note = f"分析上下文：{context_file.as_posix()}" if context_file else "分析上下文：未提供"
    categories = extract_categories(log_text)
    sources = extract_sources(rag_text)

    lines = [
        "# 待机功耗问题分析报告草稿",
        "",
        "## 结论摘要",
        "",
        "当前报告为 V0.3 自动生成草稿，需要结合 Claude Code 和人工判断补充最终结论。",
        "",
        "## 已知现象",
        "",
        f"- 问题描述：{issue}",
        f"- {context_note}",
        "",
        "## 关键证据",
        "",
        "| 证据 | 来源 | 说明 |",
        "|---|---|---|",
    ]

    if categories:
        for category in categories:
            lines.append(f"| 日志分类命中 | 日志辅助分析 | {category} |")
    else:
        lines.append("| 待补充 | 日志/RAG | 暂无自动提取证据 |")

    lines.extend(["", "## RAG 参考来源", ""])
    if sources:
        for source in sources:
            lines.append(f"- {source}")
    else:
        lines.append("- 暂无 RAG 来源，请先执行 `python rag/query.py`。")

    lines.extend(
        [
            "",
            "## 可能原因排序",
            "",
            "| 优先级 | 可能原因 | 依据 | 下一步 |",
            "|---|---|---|---|",
            "| P1 | 待 Claude Code 分析 | 结合日志证据和 RAG 片段 | 补充关键日志、对比正常样机 |",
            "",
            "## 排查步骤",
            "",
            "1. 确认测试条件、平台版本、期望电流和实测电流。",
            "2. 根据日志分类命中情况，优先排查 wakelock、wakeup source、suspend error 或网络唤醒。",
            "3. 对比正常样机的 wakeup_sources、suspend_stats 和电流曲线。",
            "4. 对可疑模块做隔离验证。",
            "",
            "## 优化建议",
            "",
            "- 待 Claude Code 基于上下文补充具体优化建议。",
            "",
            "## 需要补充的信息",
            "",
            "- 平台、软件版本、硬件版本。",
            "- 测试场景、期望电流、实测电流和电流曲线。",
            "- wakeup_sources、suspend_stats、kernel log 和模块日志。",
            "- 正常样机对比数据。",
            "",
            "## 验证方法",
            "",
            "- 修改前后使用相同场景复测平均电流和深睡占比。",
            "- 对关键功能做回归验证，避免误关必要唤醒。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Create a standard standby power analysis report draft.")
    parser.add_argument("--issue", required=True, help="Issue description.")
    parser.add_argument("--context", type=Path, help="Analysis context Markdown file.")
    parser.add_argument("--log-extract", type=Path, help="Log extract Markdown file.")
    parser.add_argument("--rag-result", type=Path, help="RAG result Markdown file.")
    parser.add_argument("--output", type=Path, required=True, help="Output Markdown report path.")
    args = parser.parse_args()

    report = build_report(args.issue, args.context, args.log_extract, args.rag_result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote analysis report draft to {args.output}")


if __name__ == "__main__":
    main()
