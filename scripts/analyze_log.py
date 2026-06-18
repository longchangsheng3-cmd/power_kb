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


@dataclass(frozen=True)
class Match:
    line_number: int
    categories: tuple[str, ...]
    text: str


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
    Rule("usb", r"\b(11201000\.usb0|type-c|typec|usb_type|usb0)\b", "USB or Type-C activity"),
    Rule("charger", r"\b(charger|vbus|ibus)\b", "Charging or battery activity"),
    Rule("error", r"\b(error|fail|failed|timeout|abort|blocked|blocker)\b", "Failure or blocker signal"),
]

ACTIVE_WAKELOCK_RE = re.compile(
    r"PowerDet:active wake lock:\s*(?P<name>[^,]+),\s*active_since:\s*(?P<active_since>\d+)\s*ms\s*,\s*active_count:\s*(?P<active_count>\d+)",
    re.IGNORECASE,
)
PENDING_WAKEUP_RE = re.compile(r"Pending Wakeup Sources:\s*(?P<sources>.+)", re.IGNORECASE)
SPM_WAKE_RE = re.compile(r"mcusys_off wake up by\s+(?P<reason>[^,]+)", re.IGNORECASE)
CHARGER_STATE_RE = re.compile(r"(attach:\s*2\(Type-C\)|get_charger_type online:2|usb_type:1|vbus\s*=\s*\d+|ibus[:=]\s*\d+)", re.IGNORECASE)


def compile_rules(rules: Iterable[Rule]) -> list[tuple[Rule, re.Pattern[str]]]:
    return [(rule, re.compile(rule.pattern, re.IGNORECASE)) for rule in rules]


def extract_matches(raw_lines: list[str], context_lines: int) -> list[Match]:
    compiled_rules = compile_rules(RULES)
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


def aggregate_evidence(raw_lines: list[str]) -> dict[str, object]:
    wake_locks: dict[str, dict[str, int]] = defaultdict(lambda: {"samples": 0, "max_active_since_ms": 0, "max_active_count": 0})
    pending_wakeup_sources: Counter[str] = Counter()
    spm_wakeup_reasons: Counter[str] = Counter()
    charger_usb_lines: list[tuple[int, str]] = []

    for line_number, line in enumerate(raw_lines, start=1):
        wake_lock_match = ACTIVE_WAKELOCK_RE.search(line)
        if wake_lock_match:
            name = wake_lock_match.group("name").strip()
            active_since = int(wake_lock_match.group("active_since"))
            active_count = int(wake_lock_match.group("active_count"))
            wake_locks[name]["samples"] += 1
            wake_locks[name]["max_active_since_ms"] = max(wake_locks[name]["max_active_since_ms"], active_since)
            wake_locks[name]["max_active_count"] = max(wake_locks[name]["max_active_count"], active_count)

        pending_match = PENDING_WAKEUP_RE.search(line)
        if pending_match:
            for source in pending_match.group("sources").split():
                pending_wakeup_sources[source.strip()] += 1

        spm_match = SPM_WAKE_RE.search(line)
        if spm_match:
            spm_wakeup_reasons[spm_match.group("reason").strip()] += 1

        if CHARGER_STATE_RE.search(line):
            charger_usb_lines.append((line_number, line.strip()))

    return {
        "wake_locks": dict(wake_locks),
        "pending_wakeup_sources": pending_wakeup_sources,
        "spm_wakeup_reasons": spm_wakeup_reasons,
        "charger_usb_lines": charger_usb_lines,
    }


def format_seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.1f}s"


def build_report(log_file: Path, matches: list[Match], aggregates: dict[str, object]) -> str:
    category_counts = Counter(category for match in matches for category in match.categories if category != "context")
    wake_locks = aggregates["wake_locks"]
    pending_wakeup_sources = aggregates["pending_wakeup_sources"]
    spm_wakeup_reasons = aggregates["spm_wakeup_reasons"]
    charger_usb_lines = aggregates["charger_usb_lines"]

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

    lines.extend(["", "## Top Active Wake Locks", "", "| Wake lock | 样本数 | 最长 active_since | 最大 active_count |", "|---|---:|---:|---:|"])
    if wake_locks:
        sorted_wake_locks = sorted(
            wake_locks.items(),
            key=lambda item: (item[1]["max_active_since_ms"], item[1]["samples"]),
            reverse=True,
        )
        for name, stats in sorted_wake_locks[:10]:
            lines.append(
                f"| {name} | {stats['samples']} | {format_seconds(stats['max_active_since_ms'])} | {stats['max_active_count']} |"
            )
    else:
        lines.append("| 无 | 0 | 0s | 0 |")

    lines.extend(["", "## Top Pending Wakeup Sources", "", "| Wakeup source | 出现次数 |", "|---|---:|"])
    if pending_wakeup_sources:
        for source, count in pending_wakeup_sources.most_common(10):
            lines.append(f"| {source} | {count} |")
    else:
        lines.append("| 无 | 0 |")

    lines.extend(["", "## SPM Wakeup Reasons", "", "| Reason | 出现次数 |", "|---|---:|"])
    if spm_wakeup_reasons:
        for reason, count in spm_wakeup_reasons.most_common(10):
            lines.append(f"| {reason} | {count} |")
    else:
        lines.append("| 无 | 0 |")

    lines.extend(["", "## USB/Type-C/Charging 代表性证据", ""])
    if charger_usb_lines:
        for line_number, text in charger_usb_lines[:20]:
            lines.append(f"- L{line_number} {text}")
        if len(charger_usb_lines) > 20:
            lines.append(f"- ... 另有 {len(charger_usb_lines) - 20} 行 USB/Type-C/Charging 相关证据")
    else:
        lines.append("未发现明显 USB/Type-C/Charging 状态证据。")

    lines.extend(["", "## 关键日志行", ""])
    if not matches:
        lines.append("未发现待机功耗相关关键词。")
    else:
        for match in matches[:500]:
            categories = ", ".join(match.categories) or "unknown"
            lines.append(f"- L{match.line_number} [{categories}] {match.text}")
        if len(matches) > 500:
            lines.append(f"- ... 另有 {len(matches) - 500} 行命中，建议结合 Top 聚合结果优先分析。")

    lines.extend(
        [
            "",
            "## 初步提示",
            "",
            "- 优先看 `Top Active Wake Locks` 和 `Top Pending Wakeup Sources`，它们比原始关键词命中更接近根因。",
            "- 如果同一个 wake lock 的 `active_since` 持续增长，说明它长时间未释放。",
            "- 如果同一个 pending wakeup source 重复出现，说明系统低功耗路径被该源反复阻塞或唤醒。",
            "- 如果 USB/Type-C/Charging 证据同时存在，应确认测试场景是否允许连接 USB/充电器。",
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

    raw_lines = args.log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    matches = extract_matches(raw_lines, args.context_lines)
    aggregates = aggregate_evidence(raw_lines)
    report = build_report(args.log_file, matches, aggregates)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote {len(matches)} matched lines to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
