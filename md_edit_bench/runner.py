"""Benchmark runner for diff algorithms."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

from lmnr import observe
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from md_edit_bench import config
from md_edit_bench.algorithms import (
    Algorithm,
    get_algorithm,
    get_all_algorithms,
    list_algorithm_names,
)
from md_edit_bench.models import (
    AlgorithmResult,
    BenchmarkRun,
    Fixture,
    LLMUsage,
    TestResult,
    discover_fixtures,
)
from md_edit_bench.scoring import score_output

RESULTS_DIR = Path(__file__).parent.parent / "results"

console = Console()


async def run_single(
    fixture: Fixture,
    algorithm: Algorithm,
    model: str,
) -> TestResult:
    """Run a single algorithm on a single fixture."""
    start_time = time.perf_counter()

    try:
        result = await algorithm.apply(fixture.initial, fixture.changes, model)
    except Exception as e:
        result = AlgorithmResult(
            output=None,
            success=False,
            error=str(e),
            usage=LLMUsage(),
        )

    duration = time.perf_counter() - start_time
    score = score_output(result.output, fixture.expected)

    return TestResult(
        fixture=fixture.name,
        algorithm=algorithm.name,
        model=model,
        algorithm_result=result,
        exact_match=score.exact_match,
        similarity_score=score.overall_score,
        lines_missing=score.lines_missing,
        lines_extra=score.lines_extra,
        diff_from_expected=score.unified_diff,
        duration_seconds=duration,
    )


async def run_benchmark(
    algorithms: list[str] | None = None,
    models: list[str] | None = None,
    category: str | None = None,
    fixtures_dir: Path | None = None,
) -> BenchmarkRun:
    """Run benchmark across algorithms, models, and fixtures."""
    fixtures_dir = fixtures_dir or config.FIXTURES_DIR
    fixtures = discover_fixtures(fixtures_dir)

    if category:
        fixtures = [f for f in fixtures if f.name.startswith(f"{category}/")]

    if not fixtures:
        console.print("[yellow]No fixtures found![/yellow]")
        return BenchmarkRun(timestamp=datetime.now(), results=[])

    if algorithms:
        algo_instances = [get_algorithm(name) for name in algorithms]
    else:
        algo_instances = get_all_algorithms()

    if not algo_instances:
        console.print("[yellow]No algorithms found![/yellow]")
        return BenchmarkRun(timestamp=datetime.now(), results=[])

    test_models = models if models else config.DEFAULT_MODELS

    total_tasks = len(fixtures) * len(algo_instances) * len(test_models)
    console.print(f"\n[bold blue]Running {total_tasks} tests...[/bold blue]")
    console.print(f"  Fixtures: {len(fixtures)}")
    console.print(f"  Algorithms: {[a.name for a in algo_instances]}")

    results: list[TestResult] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        progress_task = progress.add_task("Processing...", total=total_tasks)

        async def run_fixture_and_track(fixture: Fixture) -> list[TestResult]:
            fixture_results = await _run_fixture(fixture, algo_instances, test_models)
            for result in fixture_results:
                status = "✓" if result.passed else "✗"
                desc = f"[{status}] {result.algorithm}/{result.fixture}"
                progress.update(progress_task, advance=1, description=desc)
            return fixture_results

        all_fixture_results = await asyncio.gather(
            *[run_fixture_and_track(fixture) for fixture in fixtures]
        )
        for fixture_results in all_fixture_results:
            results.extend(fixture_results)

    return BenchmarkRun(timestamp=datetime.now(), results=results)


async def _run_fixture(
    fixture: Fixture,
    algorithms: list[Algorithm],
    models: list[str],
) -> list[TestResult]:
    """Run all algorithms on a single fixture (traced as a span)."""

    @observe(name=f"fixture:{fixture.name}")
    async def _traced() -> list[TestResult]:
        coros = [_run_algorithm(fixture, algo, model) for algo in algorithms for model in models]
        return list(await asyncio.gather(*coros))

    return await _traced()


async def _run_algorithm(
    fixture: Fixture,
    algorithm: Algorithm,
    model: str,
) -> TestResult:
    """Run a single algorithm on a fixture (traced as a span)."""
    model_suffix = f"({model.split('/')[-1]})"
    span_name = f"algorithm:{algorithm.name}{model_suffix}"

    @observe(name=span_name)
    async def _traced() -> TestResult:
        return await run_single(fixture, algorithm, model)

    return await _traced()


def print_summary(run: BenchmarkRun) -> None:
    """Print summary table of benchmark results."""
    if not run.results:
        console.print("[yellow]No results to display[/yellow]")
        return

    # Main results table
    table = Table(title="Diff Algorithm Benchmark Results")
    table.add_column("Algorithm", style="cyan")
    table.add_column("Model", style="dim")
    table.add_column("Fixture", style="white")
    table.add_column("Match", justify="center")
    table.add_column("Warn", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Time", justify="right")
    table.add_column("Cost", justify="right")

    for r in sorted(run.results, key=lambda x: (x.algorithm, x.model, x.fixture)):
        has_error = r.algorithm_result.error is not None
        if has_error:
            status = "[yellow]ERR[/yellow]"
        elif r.passed:
            status = "[green]✓[/green]"
        else:
            status = "[red]✗[/red]"
        model_str = r.model.split("/")[-1]
        warn_str = str(r.warning_count) if r.warning_count > 0 else "-"
        score_str = f"{r.similarity_score:.2f}"
        time_str = f"{r.duration_seconds:.1f}s"
        cost_str = f"${r.cost_usd:.4f}"

        table.add_row(
            r.algorithm,
            model_str,
            r.fixture.split("/")[-1],
            status,
            warn_str,
            score_str,
            time_str,
            cost_str,
        )

    console.print(table)

    # Summary by algorithm
    console.print("\n[bold]Summary by Algorithm:[/bold]")

    for algo_name, results in sorted(run.by_algorithm().items()):
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        pct = (passed / total * 100) if total else 0
        avg_time = sum(r.duration_seconds for r in results) / total if total else 0
        total_cost = sum(r.cost_usd for r in results)
        avg_missing = sum(r.lines_missing for r in results) / total if total else 0
        avg_extra = sum(r.lines_extra for r in results) / total if total else 0
        total_warnings = sum(r.warning_count for r in results)

        style = "green" if pct >= 80 else "yellow" if pct >= 50 else "red"
        warn_part = f"  [yellow]warnings: {total_warnings}[/yellow]" if total_warnings > 0 else ""
        console.print(
            f"  {algo_name}: [{style}]{passed}/{total} ({pct:.0f}%)[/{style}] "
            f"avg: {avg_time:.1f}s  ${total_cost:.4f}  "
            f"lines: [red]-{avg_missing:.1f}[/red]/[green]+{avg_extra:.1f}[/green]{warn_part}"
        )

    # Overall summary
    console.print(
        f"\n[bold]Overall: {run.total_passed}/{run.total_tests} passed "
        f"({run.total_passed / run.total_tests * 100:.1f}%)[/bold]"
    )
    console.print(f"Total time: {run.total_duration_seconds:.1f}s")
    console.print(f"Total cost: ${run.total_cost_usd:.4f}")


def print_failures(run: BenchmarkRun, show_diff: bool = False) -> None:
    """Print details about failed tests."""
    failures = [r for r in run.results if not r.passed]

    if not failures:
        console.print("\n[green]All tests passed![/green]")
        return

    console.print(f"\n[bold red]Failed Tests ({len(failures)}):[/bold red]")

    for r in failures:
        console.print(f"\n[cyan]{r.algorithm}[/cyan]", end="")
        if r.model:
            console.print(f" ({r.model.split('/')[-1]})", end="")
        console.print(f" on [white]{r.fixture}[/white]")

        if r.algorithm_result.error:
            console.print(f"  Error: {r.algorithm_result.error}", style="red")
        else:
            console.print(f"  Similarity: {r.similarity_score:.2f}")

        if r.algorithm_result.warnings:
            console.print(f"  Warnings ({len(r.algorithm_result.warnings)}):", style="yellow")
            for w in r.algorithm_result.warnings[:5]:
                console.print(f"    - {w[:100]}", style="yellow")
            if len(r.algorithm_result.warnings) > 5:
                console.print(
                    f"    ... and {len(r.algorithm_result.warnings) - 5} more", style="dim"
                )

        if show_diff and r.diff_from_expected:
            console.print("  Diff from expected:")
            for line in r.diff_from_expected.split("\n")[:20]:
                if line.startswith("+"):
                    console.print(f"    {line}", style="green")
                elif line.startswith("-"):
                    console.print(f"    {line}", style="red")
                else:
                    console.print(f"    {line}", style="dim")
            if r.diff_from_expected.count("\n") > 20:
                console.print("    ... (truncated)")


def save_results(run: BenchmarkRun) -> None:
    """Save benchmark results to results/ directory."""
    # if RESULTS_DIR.exists():
    #    shutil.rmtree(RESULTS_DIR)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for r in run.results:
        # Build directory path: results/{category}/{fixture}/{algorithm}/{model}/
        category, fixture_name = (
            r.fixture.split("/", 1) if "/" in r.fixture else ("default", r.fixture)
        )
        model_part = r.model.split("/")[-1]
        result_dir = RESULTS_DIR / category / fixture_name / r.algorithm / model_part
        result_dir.mkdir(parents=True, exist_ok=True)

        # result.json - metrics and metadata
        result_data = {
            "fixture": r.fixture,
            "algorithm": r.algorithm,
            "model": r.model,
            "success": r.algorithm_result.success,
            "error": r.algorithm_result.error,
            "warning_count": r.warning_count,
            "warnings": r.algorithm_result.warnings[:20],
            "exact_match": r.exact_match,
            "similarity_score": r.similarity_score,
            "lines_missing": r.lines_missing,
            "lines_extra": r.lines_extra,
            "duration_seconds": r.duration_seconds,
            "tokens_in": r.algorithm_result.usage.tokens_in,
            "tokens_out": r.algorithm_result.usage.tokens_out,
            "cost_usd": r.algorithm_result.usage.cost_usd,
        }
        (result_dir / "result.json").write_text(json.dumps(result_data, indent=2), encoding="utf-8")

        # output.md - algorithm's output
        if r.algorithm_result.output:
            (result_dir / "output.md").write_text(r.algorithm_result.output, encoding="utf-8")

        # diff.txt - diff from expected
        if r.diff_from_expected:
            (result_dir / "diff.txt").write_text(r.diff_from_expected, encoding="utf-8")

        # LLM calls
        for i, call in enumerate(r.algorithm_result.usage.calls, 1):
            prefix = f"llm_{i}_" if len(r.algorithm_result.usage.calls) > 1 else "llm_"
            (result_dir / f"{prefix}request.txt").write_text(
                f"Model: {call.model}\n\n{call.request}", encoding="utf-8"
            )
            (result_dir / f"{prefix}response.txt").write_text(call.response, encoding="utf-8")

    console.print(f"\n[dim]Results saved to {RESULTS_DIR}/[/dim]")


@observe(name="benchmark_run")
async def _run_benchmark_traced(
    algorithms: list[str] | None,
    models: list[str] | None,
    category: str | None,
) -> BenchmarkRun:
    """Wrapper to trace the entire benchmark run as a root span."""
    return await run_benchmark(
        algorithms=algorithms,
        models=models,
        category=category,
    )


async def main_async() -> None:
    """Run benchmarks from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run diff algorithm benchmarks")
    parser.add_argument(
        "--algorithm",
        "-a",
        type=str,
        action="append",
        dest="algorithms",
        help=f"Algorithm(s) to test. Available: {list_algorithm_names()}",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        action="append",
        dest="models",
        help="Model(s) to test (for algorithms that accept models)",
    )
    parser.add_argument(
        "--category",
        "-c",
        type=str,
        choices=config.CATEGORIES,
        help="Fixture category to test (default: all)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed failure information",
    )
    parser.add_argument(
        "--diff",
        "-d",
        action="store_true",
        help="Show diffs for failures (implies --verbose)",
    )

    args = parser.parse_args()

    # Extract typed values from argparse
    algorithms: list[str] | None = args.algorithms  # pyright: ignore[reportAny]
    models: list[str] | None = args.models  # pyright: ignore[reportAny]
    category: str | None = args.category  # pyright: ignore[reportAny]
    verbose: bool = args.verbose  # pyright: ignore[reportAny]
    show_diff: bool = args.diff  # pyright: ignore[reportAny]

    console.print("[bold]Markdown Edit LLM Benchmark[/bold]\n")
    console.print(f"Fixtures directory: {config.FIXTURES_DIR}")

    if config.LAMINAR_ENABLED:
        console.print("[green]Laminar tracing: enabled[/green]")
    else:
        console.print("[dim]Laminar tracing: disabled[/dim]")

    run = await _run_benchmark_traced(
        algorithms=algorithms,
        models=models,
        category=category,
    )

    console.print()
    print_summary(run)

    if verbose or show_diff:
        print_failures(run, show_diff=show_diff)

    save_results(run)


def main() -> None:
    """Entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
