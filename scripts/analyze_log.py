from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Rule:
    category: str
    pattern: str
    description: str


RULES = [
    Rule("wakelock", r"\b(wakelock|wake_lock|wake lock)\b", "Wakelock or wake lock activity"),
    Rule("wakeup", r"\b(wakeup|wake up|wakeup_source|wakeup source)\b", "Wakeup source activity"),
    Rule("suspend", r"\b(suspend|s2idle|deep sleep|deepsleep)\b", "Suspend or deep sleep transition"),
    Rule("resume", r"\b(resume|resumed)\b", "Resume transition"),
    Rule("alarm", r"\b(alarm|alarmtimer|rtc)\b", "Alarm or RTC wakeup"),
    Rule("network", r"\b(wlan|wifi|wi-fi|modem|lte|nr|cellular|packet|rx|tx)\b", "Network-related activity"),
    Rule("wireless", r"\b(bt|bluetooth|gnss|gps)\b", "BT/GNSS-related activity"),
    Rule("sensor", r"\b(sensor|accel|gyro|als|proximity)\b", "Sensor-related activity"),
    Rule("power-rail", r"\b(pmic|regulator|ldo|buck|vreg|voltage)\b", "PMIC or regulator activity"),
    Rule("clock-irq", r"\b(clock|clk|irq|interrupt)\b", "Clock or interrupt activity"),
    Rule("error", r"\b(error|fail|failed|timeout|abort|blocked|blocker)\b", "Failure or blocker signal"),
]


@dataclass(frozen=True)
class Match:
    line_number: int
    categories: tuple[str, ...]
    text: str


def compile_rules(rules: Iterable[Rule]) -> list[tuple[Rule, re.Pattern[str]]]:
    return [(rule, re.compile(rule.pattern, re.IGNORECASE)) for rule in rules]


def extract_matches(log_file: Path, context_lines: int) -> list[Match]:
    compiled_rules = compile_rules(RULES)
    raw_lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    matched_numbers: set[int] = set()
    line_categories: dict[int, set[str]] = defaultdict(set)

    for line_number, line in enumerate(raw_lines, start=1):
        for rule, pattern in compiled_rules:
            if pattern.search(line):
                matched_numbers.add(line_number)
                line_categories[line_number].add(rule.category)

    if context_lines > 0:
        for line_number in list(matched_numbers):
            start = max(1, line_number - context_lines)
            end = min(len(raw_lines), line_number + context_lines)
            for context_number in range(start, end + 1):
                matched_numbers.add(context_number)
                if context_number not in line_categories:
                    line_categories[context_number].add("context")

    matches: list[Match] = []
    for line_number in sorted(matched_numbers):
        categories = tuple(sorted(line_categories[line_number]))
        matches.append(Match(line_number, categories, raw_lines[line_number - 1]))
    return matches


def build_report(log_file: Path, matches: list[Match]) -> str:
    category_counts = Counter(category for match in matches for category in match.categories if category != "context")
    lines = [
        "# 日志辅助分析结果",
        "",
        f"日志文件：{log_file.as_posix()}",
        f"命中行数：{len(matches)}",
        "",
        "## 分类统计",
        "",
        "| 分类 | 命中数 |",
        "|---|---:|",
    ]

    if category_counts:
        for category, count in category_counts.most_common():
            lines.append(f"| {category} | {count} |")
    else:
        lines.append("| 无 | 0 |")

    lines.extend(["", "## 关键日志行", ""])
    if not matches:
        lines.append("未发现待机功耗相关关键词。")
        return "\n".join(lines).rstrip() + "\n"

    for match in matches:
        categories = ", ".join(match.categories) or "unknown"
        lines.append(f"- L{match.line_number} [{categories}] {match.text}")

    lines.extend(
        [
            "",
            "## 初步提示",
            "",
            "- 如果 `wakelock` 或 `wakeup` 命中较多，优先查看 wakeup source 和 active 时间。",
            "- 如果 `suspend` 与 `error` 同时出现，优先检查 suspend blocker 或 driver suspend 回调。",
            "- 如果 `network` 命中较多，建议对比飞行模式、Wi-Fi、蜂窝网络等场景。",
            "- 如果 `power-rail`、`clock-irq` 命中较多，建议检查外设电源、clock、IRQ 和 GPIO 状态。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Extract standby-power-related evidence from a log file.")
    parser.add_argument("log_file", type=Path, help="Path to log file.")
    parser.add_argument("--output", type=Path, help="Optional Markdown output file path.")
    parser.add_argument("--context-lines", type=int, default=0, help="Include N lines before and after each match.")
    args = parser.parse_args()

    if not args.log_file.exists():
        raise SystemExit(f"Log file not found: {args.log_file}")
    if args.context_lines < 0:
        raise SystemExit("--context-lines must be >= 0.")

    matches = extract_matches(args.log_file, args.context_lines)
    report = build_report(args.log_file, matches)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote {len(matches)} matched lines to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
