"""Step-by-step terminal prints — easy to see where problems happen."""

from rich.console import Console
from rich.panel import Panel

console = Console()


def banner(phase: str = "Arsenal Bot", subtitle: str = "Test mode first. Chelsea bot = later phase."):
    console.print(
        Panel(
            f"[bold green]{phase}[/]\n[dim]{subtitle}[/]",
            title="Starting",
        )
    )


def divider(title: str = ""):
    if title:
        console.print(f"\n[bold magenta]--- {title} ---[/]")
    else:
        console.print("[dim]" + "-" * 50 + "[/]")


def step(num: int, total: int, msg: str):
    console.print(f"\n[bold cyan][STEP {num}/{total}][/] {msg}")


def sub(msg: str):
    console.print(f"       [dim]>[/] {msg}")


def sub_ok(msg: str):
    console.print(f"       [green]OK[/] {msg}")


def sub_warn(msg: str):
    console.print(f"       [yellow]![/] {msg}")


def sub_err(msg: str):
    console.print(f"       [red]X[/] {msg}")


def info(msg: str):
    console.print(f"[cyan]>[/] {msg}")


def ok(msg: str):
    console.print(f"[green]OK[/] {msg}")


def warn(msg: str):
    console.print(f"[yellow]![/] {msg}")


def err(msg: str):
    console.print(f"[red]X[/] {msg}")


def hint(msg: str):
    console.print(f"[dim]   TIP:[/] {msg}")
