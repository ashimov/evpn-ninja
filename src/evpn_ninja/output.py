"""Output formatters for table, JSON, and YAML output."""

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

console = Console()


def configure_console(no_color: bool = False) -> None:
    """Configure the global console instance.

    Args:
        no_color: If True, disable colors and formatting
    """
    global console
    console = Console(no_color=no_color, force_terminal=not no_color)


class OutputFormat(str, Enum):
    """Output format options."""
    TABLE = "table"
    JSON = "json"
    YAML = "yaml"


def _serialize(obj: Any) -> Any:
    """Convert dataclasses and enums to serializable format."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, list):
        return [_serialize(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def output_json(data: Any, indent: int = 2) -> None:
    """Output data as JSON."""
    serialized = _serialize(data)
    console.print(json.dumps(serialized, indent=indent, ensure_ascii=False))


def output_yaml(data: Any) -> None:
    """Output data as YAML."""
    serialized = _serialize(data)
    yaml_str = yaml.dump(serialized, allow_unicode=True, default_flow_style=False, sort_keys=False)
    console.print(yaml_str.rstrip())


def output_table(
    title: str,
    columns: list[str],
    rows: list[list[str]],
    caption: str | None = None,
) -> None:
    """Output data as a rich table."""
    table = Table(title=title, show_header=True, header_style="bold cyan")

    for col in columns:
        table.add_column(col)

    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    if caption:
        table.caption = caption

    console.print(table)


def output_key_value(title: str, data: dict[str, Any]) -> None:
    """Output key-value pairs in a panel."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold yellow")
    table.add_column("Value", style="green")

    for key, value in data.items():
        table.add_row(key, str(value))

    console.print(Panel(table, title=title, border_style="blue"))


def output_config(title: str, config: str, language: str = "text") -> None:
    """Output configuration snippet with syntax highlighting."""
    syntax = Syntax(config, language, theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title=title, border_style="green"))


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]{message}[/bold green]")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[bold blue]Info:[/bold blue] {message}")
