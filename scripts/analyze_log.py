from __future__ import annotations

import argparse
from pathlib import Path


KEYWORDS = [
    "wakelock",
    "wakeup",
    "suspend",
    "resume",
    "alarm",
    "wlan",
    "wifi",
    "modem",
    "gnss",
    "sensor",
    "pmic",
    "regulator",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract standby-power-related lines from a log file.")
    parser.add_argument("log_file", help="Path to log file.")
    parser.add_argument("--output", help="Optional output file path.")
    args = parser.parse_args()

    path = Path(args.log_file)
    lines = []
    with path.open("r", encoding="utf-8", errors="ignore") as file:
        for line_number, line in enumerate(file, start=1):
            lower = line.lower()
            if any(keyword in lower for keyword in KEYWORDS):
                lines.append(f"{line_number}: {line.rstrip()}")

    result = "\n".join(lines)
    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"Wrote {len(lines)} matched lines to {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
