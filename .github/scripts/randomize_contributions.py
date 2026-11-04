#!/usr/bin/env python3
"""Color empty cells in generated snake SVGs without changing real cells."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import random
import re
from pathlib import Path


SVG_STYLE = re.compile(r"<style>(.*?)</style>", re.DOTALL)
SVG_RECT = re.compile(r"<rect\b([^>]*)/>")
SVG_CLASS = re.compile(r"\bclass=(['\"])(.*?)\1")
SVG_COORDINATE = re.compile(r"\b([xy])=(['\"])(-?[\d.]+)\2")
SNAKE_TRANSLATION = re.compile(
    r"transform:\s*translate\(\s*(-?[\d.]+)px,\s*(-?[\d.]+)px\s*\)"
)
SIMULATION_NOTE = (
    "Simulated colors on empty cells; actual GitHub contribution history is unchanged."
)
LEVEL_WEIGHTS = (55, 30, 12, 3)


def _block_end(text: str, opening_brace: int) -> int:
    depth = 1
    for index in range(opening_brace + 1, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("Unbalanced CSS block in generated SVG")


def _snake_visit_times(style: str) -> dict[tuple[int, int], float]:
    marker = "@keyframes s0{"
    marker_index = style.find(marker)
    if marker_index < 0:
        raise ValueError("Generated SVG is missing the snk snake animation")

    opening_brace = marker_index + len(marker) - 1
    body = style[opening_brace + 1 : _block_end(style, opening_brace)]
    visit_times: dict[tuple[int, int], float] = {}
    for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", body):
        translation = SNAKE_TRANSLATION.search(declarations)
        if not translation:
            continue

        x, y = (round(float(value)) for value in translation.groups())
        if x < 0 or y < 0:
            continue
        times = [float(value) for value in re.findall(r"([\d.]+)%", selector)]
        if not times:
            continue

        position = (x, y)
        visit_times[position] = min(visit_times.get(position, times[0]), *times)
    return visit_times


def _rect_class(attributes: str) -> str | None:
    match = SVG_CLASS.search(attributes)
    return match.group(2) if match else None


def _rect_position(attributes: str) -> tuple[int, int]:
    coordinates = {
        axis: float(value)
        for axis, _, value in SVG_COORDINATE.findall(attributes)
    }
    if "x" not in coordinates or "y" not in coordinates:
        raise ValueError("Contribution cell is missing its x/y coordinates")
    return round(coordinates["x"] - 2), round(coordinates["y"] - 2)


def _seed_for_day(simulation_date: date) -> int:
    digest = hashlib.sha256(simulation_date.isoformat().encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big")


def random_levels(simulation_date: date, count: int) -> list[int]:
    generator = random.Random(_seed_for_day(simulation_date))
    return [
        generator.choices((1, 2, 3, 4), weights=LEVEL_WEIGHTS, k=1)[0]
        for _ in range(count)
    ]


def _format_percent(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _simulated_css(
    cells: list[tuple[int, tuple[int, int], int]],
    visit_times: dict[tuple[int, int], float],
) -> str:
    rules = ["/* simulated contribution cells */"]
    for index, position, level in cells:
        class_name = f"sim{index}"
        color = f"var(--c{level})"
        visit_time = visit_times.get(position)
        if visit_time is None:
            rules.append(f".c.{class_name}{{fill:{color}}}")
            continue

        empty_time = min(visit_time + 0.02, 100)
        rules.append(
            f"@keyframes {class_name}{{{_format_percent(visit_time)}%"
            f"{{fill:{color}}}{_format_percent(empty_time)}%,100%"
            f"{{fill:var(--ce)}}}}"
            f".c.{class_name}{{fill:{color};animation-name:{class_name}}}"
        )
    return "".join(rules)


def randomize_svg(svg: str, simulation_date: date) -> str:
    style_matches = list(SVG_STYLE.finditer(svg))
    if len(style_matches) != 1:
        raise ValueError("Expected exactly one style block in generated SVG")

    empty_cells: list[tuple[str, tuple[int, int]]] = []
    for match in SVG_RECT.finditer(svg):
        attributes = match.group(1)
        if _rect_class(attributes) == "c":
            empty_cells.append((match.group(0), _rect_position(attributes)))

    if not empty_cells:
        return svg

    style = style_matches[0].group(1)
    visit_times = _snake_visit_times(style)
    levels = random_levels(simulation_date, len(empty_cells))
    simulated_cells = [
        (index, position, levels[index])
        for index, (_, position) in enumerate(empty_cells)
    ]
    replacements = {
        original: SVG_CLASS.sub(
            lambda match, index=index: f'class={match.group(1)}c sim{index}{match.group(1)}',
            original,
            count=1,
        )
        for index, (original, _) in enumerate(empty_cells)
    }

    def replace_empty_cell(match: re.Match[str]) -> str:
        return replacements.get(match.group(0), match.group(0))

    randomized = SVG_RECT.sub(replace_empty_cell, svg)
    randomized = SVG_STYLE.sub(
        lambda match: f"<style>{match.group(1)}"
        f"{_simulated_css(simulated_cells, visit_times)}</style>",
        randomized,
        count=1,
    )
    if SIMULATION_NOTE not in randomized:
        svg_open = re.search(r"<svg\b[^>]*>", randomized)
        if svg_open is None:
            raise ValueError("Generated SVG is missing its root element")
        title = f"<title>{SIMULATION_NOTE}</title>"
        randomized = (
            randomized[: svg_open.end()]
            + title
            + randomized[svg_open.end() :]
        )
    return randomized


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "date must use YYYY-MM-DD format"
        ) from error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        type=_parse_date,
        default=datetime.now(timezone.utc).date(),
        help="UTC date used to seed the daily pattern (default: today in UTC)",
    )
    parser.add_argument("svg_files", nargs="+", type=Path)
    args = parser.parse_args()

    for svg_path in args.svg_files:
        original = svg_path.read_text(encoding="utf-8")
        randomized = randomize_svg(original, args.date)
        svg_path.write_text(randomized, encoding="utf-8")
        print(f"Randomized empty cells in {svg_path}")


if __name__ == "__main__":
    main()
