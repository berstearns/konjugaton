#!/usr/bin/env python3
"""
RAM tracker: snapshot baseline, run a command, poll /proc/meminfo, report peak.

Usage:
    python3 track.py [--interval 0.5] [--out path/to/report.json] -- <cmd> [args...]

Exit code mirrors the tracked command's exit code.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def _meminfo() -> dict[str, int]:
    """Parse /proc/meminfo → {key: value_in_kB}."""
    info: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            info[key.strip()] = int(val.strip().split()[0])
    return info


def _used_gb(info: dict[str, int]) -> float:
    return (info["MemTotal"] - info["MemAvailable"]) / 1_048_576


def _fmt(gb: float) -> str:
    return f"{gb:.2f} GB"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--interval", type=float, default=0.5, metavar="S", help="Poll interval in seconds (default 0.5)")
    parser.add_argument("--out", type=Path, default=None, metavar="FILE", help="Override output JSON path")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    cmd: list[str] = args.command
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        parser.error("No command provided. Separate it with --: track.py -- make build")

    # ── baseline ────────────────────────────────────────────────────────────
    baseline_info = _meminfo()
    total_gb = baseline_info["MemTotal"] / 1_048_576
    baseline_gb = _used_gb(baseline_info)
    start_ts = datetime.now()

    print(f"[mem-track] {'─'*52}")
    print(f"[mem-track] command   : {' '.join(cmd)}")
    print(f"[mem-track] started   : {start_ts.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[mem-track] total RAM : {_fmt(total_gb)}")
    print(f"[mem-track] baseline  : {_fmt(baseline_gb)}  (before spawn)")
    print(f"[mem-track] {'─'*52}")

    samples: list[float] = [baseline_gb]
    t0 = time.monotonic()

    # ── run + poll ───────────────────────────────────────────────────────────
    proc = subprocess.Popen(cmd)
    try:
        while proc.poll() is None:
            samples.append(_used_gb(_meminfo()))
            time.sleep(args.interval)
        # one final sample after exit
        samples.append(_used_gb(_meminfo()))
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
        sys.exit(130)

    elapsed = time.monotonic() - t0
    end_ts = datetime.now()
    peak_gb = max(samples)
    delta_gb = peak_gb - baseline_gb

    # ── report ───────────────────────────────────────────────────────────────
    print(f"[mem-track] {'─'*52}")
    print(f"[mem-track] baseline  : {_fmt(baseline_gb)}")
    print(f"[mem-track] peak      : {_fmt(peak_gb)}  (+{_fmt(delta_gb)})")
    print(f"[mem-track] final     : {_fmt(samples[-1])}")
    print(f"[mem-track] elapsed   : {elapsed:.1f}s")
    print(f"[mem-track] samples   : {len(samples)}  (every {args.interval}s)")
    print(f"[mem-track] exit code : {proc.returncode}")
    print(f"[mem-track] {'─'*52}")

    tag = Path(cmd[-1]).stem if len(cmd) == 1 else cmd[0].split("/")[-1]
    default_out = (
        Path(__file__).parent / "reports" /
        f"{start_ts.strftime('%Y%m%d_%H%M%S')}-{tag}.json"
    )
    out: Path = args.out or default_out
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "command": cmd,
        "start": start_ts.isoformat(),
        "end": end_ts.isoformat(),
        "elapsed_s": round(elapsed, 1),
        "total_ram_gb": round(total_gb, 3),
        "baseline_gb": round(baseline_gb, 3),
        "peak_gb": round(peak_gb, 3),
        "delta_gb": round(delta_gb, 3),
        "final_gb": round(samples[-1], 3),
        "exit_code": proc.returncode,
        "sample_count": len(samples),
        "poll_interval_s": args.interval,
    }
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"[mem-track] report    → {out}")

    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
