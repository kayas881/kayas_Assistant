from __future__ import annotations

import sys
from rich import print

from .agent.dialog import dialog_once


def main(argv):
    print("[cyan]Speak after the beep. Listening for 5 seconds…[/cyan]")
    out = dialog_once(listen_seconds=5.0)
    print("[green]Heard:[/green]", out.get("heard"))
    print("[green]Response:[/green]", out.get("response"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
