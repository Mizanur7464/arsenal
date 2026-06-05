#!/usr/bin/env python3
"""Run the bot (only command you need):

    python run.py

Ticket scan + Telegram commands (/start, /status, /start_on, /stop).
Press Ctrl+C in the terminal when you want to stop.
"""

import sys

from src.phase5 import run_phase5


def main():
    if len(sys.argv) == 1:
        raise SystemExit(0 if run_phase5() else 1)

    cmd = sys.argv[1].lower()
    if cmd in ("phase1", "1", "check"):
        from src.phase1 import check_phase1
        raise SystemExit(0 if check_phase1() else 1)
    if cmd == "test":
        from src.bot import run_test_flow
        run_test_flow()
        return

    print("Use only:  python run.py")
    print("(Ticket scan + Telegram. Ctrl+C to stop.)")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
