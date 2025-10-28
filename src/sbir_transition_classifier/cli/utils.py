"""CLI utilities for shared console and logger setup."""

from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Iterator, Callable, Any

from loguru import logger
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table


class CliContext:
    """Shared context for CLI commands with console and logger."""

    def __init__(self, verbose: bool = False, console: Optional[Console] = None):
        """
        Initialize CLI context.

        Args:
            verbose: Enable verbose (DEBUG) logging
            console: Optional pre-configured Console; creates new if None
        """
        self.console = console or Console()
        self.verbose = verbose
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configure logger with optional verbose output."""
        logger.remove()  # Remove default handler

        if self.verbose:
            # Debug logging to console
            logger.add(
                lambda msg: self.console.print(msg, style="dim"),
                level="DEBUG",
                format="{message}",
            )
        else:
            # Info and above only
            logger.add(
                RichHandler(console=self.console, show_path=False),
                level="INFO",
                format="{message}",
            )

    def success(self, message: str, **kwargs) -> None:
        """Print success message."""
        self.console.print(f"✓ {message}", style="green", **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Print error message."""
        self.console.print(f"✗ {message}", style="red", **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Print warning message."""
        self.console.print(f"⚠ {message}", style="yellow", **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Print info message."""
        self.console.print(f"ℹ {message}", style="blue", **kwargs)

    def create_table(self, *columns: str, **kwargs) -> Table:
        """Create a Rich table with standard styling."""
        table = Table(*columns, show_header=True, **kwargs)
        return table


@contextmanager
def cli_context(
    verbose: bool = False, console: Optional[Console] = None
) -> Iterator[CliContext]:
    """
    Context manager for CLI command execution with shared setup.

    Usage:
        with cli_context(verbose=verbose) as ctx:
            ctx.console.print("Hello")
            logger.info("Message")

    Args:
        verbose: Enable verbose logging
        console: Optional pre-configured console

    Yields:
        CliContext with console and logger configured
    """
    ctx = CliContext(verbose=verbose, console=console)
    try:
        yield ctx
    except Exception as e:
        ctx.error(f"Command failed: {e}")
        raise


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_size(bytes_count: int) -> str:
    """Format byte count to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} TB"


def format_count(count: int) -> str:
    """Format number with thousands separators."""
    return f"{count:,}"


class ProgressTracker:
    """Simple progress tracking for CLI operations."""

    def __init__(self, ctx: CliContext, total: int, label: str = "Processing"):
        """
        Initialize progress tracker.

        Args:
            ctx: CliContext instance
            total: Total items to process
            label: Label for progress output
        """
        self.ctx = ctx
        self.total = total
        self.label = label
        self.current = 0
        self.errors = 0

    def advance(self, count: int = 1, error: bool = False) -> None:
        """Advance progress counter."""
        self.current += count
        if error:
            self.errors += count

        # Show progress every 10% or at end
        percent = (self.current / self.total) * 100
        if self.current % max(1, self.total // 10) == 0 or self.current == self.total:
            status = f"{format_count(self.current)}/{format_count(self.total)}"
            if self.errors > 0:
                status += f" ({self.errors} errors)"
            self.ctx.console.print(f"  {self.label}: {status} ({percent:.0f}%)")

    def summary(self) -> None:
        """Print summary of progress."""
        success_count = self.current - self.errors
        self.ctx.success(
            f"{self.label} complete: {format_count(success_count)} processed"
            + (f", {format_count(self.errors)} errors" if self.errors > 0 else "")
        )


class DataValidator:
    """Validate common data file patterns."""

    @staticmethod
    def validate_csv_exists(file_path: Path) -> bool:
        """Check if CSV file exists and is readable."""
        if not file_path.exists():
            return False
        if not file_path.is_file():
            return False
        return file_path.suffix.lower() == ".csv"

    @staticmethod
    def validate_dir_exists(dir_path: Path) -> bool:
        """Check if directory exists and is readable."""
        if not dir_path.exists():
            return False
        return dir_path.is_dir()

    @staticmethod
    def validate_output_path(path: Path, must_be_dir: bool = False) -> bool:
        """Validate output path is writable."""
        if path.exists():
            if must_be_dir:
                return path.is_dir()
            return path.is_file()
        # Parent must exist and be writable
        return path.parent.exists() and path.parent.is_dir()


def safe_command(func: Callable) -> Callable:
    """
    Decorator for CLI commands to handle common setup and error handling.

    Usage:
        @click.command()
        @safe_command
        def my_command(ctx: CliContext, ...):
            ctx.console.print("Hello")

    Args:
        func: CLI command function that accepts ctx as first parameter

    Returns:
        Wrapped function with error handling
    """

    def wrapper(*args, verbose: bool = False, **kwargs) -> Any:
        try:
            with cli_context(verbose=verbose) as ctx:
                return func(*args, ctx=ctx, **kwargs)
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise

    return wrapper
