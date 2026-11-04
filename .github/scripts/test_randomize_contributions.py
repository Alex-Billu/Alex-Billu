import unittest
import xml.etree.ElementTree as ET
from datetime import date

from randomize_contributions import random_levels, randomize_svg


LIGHT_SVG = """<svg viewBox="-16 -32 880 192" width="880" height="192" xmlns="http://www.w3.org/2000/svg"><desc>Generated with snk</desc><style>:root{--ce:#ebedf0;--c1:#9be9a8;--c2:#40c463;--c3:#30a14e;--c4:#216e39}.c{fill:var(--ce);animation:none 76900ms linear infinite}@keyframes s0{1%{transform:translate(0px,0px)}2%{transform:translate(16px,0px)}}.c.c0{fill:var(--c3)}</style><rect class="c" x="2" y="2" rx="2" ry="2"/><rect class="c c0" x="18" y="2" rx="2" ry="2"/><rect class="c" x="34" y="2" rx="2" ry="2"/></svg>"""
DARK_SVG = LIGHT_SVG.replace(
    "--ce:#ebedf0;--c1:#9be9a8;--c2:#40c463;--c3:#30a14e;--c4:#216e39",
    "--ce:#161b22;--c1:#0e4429;--c2:#006d32;--c3:#26a641;--c4:#39d353",
)


class RandomizeContributionsTests(unittest.TestCase):
    def test_patterns_are_deterministic_per_date_and_vary_between_dates(self) -> None:
        first = random_levels(date(2026, 11, 4), 371)
        repeated = random_levels(date(2026, 11, 4), 371)
        next_day = random_levels(date(2026, 11, 5), 371)

        self.assertEqual(first, repeated)
        self.assertNotEqual(first, next_day)
        self.assertEqual(set(first), {1, 2, 3, 4})

    def test_rendered_pattern_changes_between_dates(self) -> None:
        first = randomize_svg(LIGHT_SVG, date(2026, 11, 4))
        next_day = randomize_svg(LIGHT_SVG, date(2026, 11, 5))

        self.assertNotEqual(first, next_day)
        self.assertIn(".c.c0{fill:var(--c3)}", first)
        self.assertIn(".c.c0{fill:var(--c3)}", next_day)

    def test_only_empty_cells_change_and_dimensions_are_preserved(self) -> None:
        result = randomize_svg(LIGHT_SVG, date(2026, 11, 4))

        self.assertIn('viewBox="-16 -32 880 192"', result)
        self.assertIn(
            '<rect class="c c0" x="18" y="2" rx="2" ry="2"/>',
            result,
        )
        self.assertIn(".c.c0{fill:var(--c3)}", result)
        self.assertIn('<rect class="c sim0" x="2" y="2"', result)
        self.assertIn('<rect class="c sim1" x="34" y="2"', result)
        self.assertIn("@keyframes sim0{1%", result)
        self.assertIn("animation-name:sim0", result)
        self.assertIn(".c.sim1{fill:var(--c", result)
        self.assertIn("actual GitHub contribution history is unchanged", result)
        self.assertIn("@keyframes s0", result)
        ET.fromstring(result)

    def test_reprocessing_an_svg_is_idempotent(self) -> None:
        once = randomize_svg(LIGHT_SVG, date(2026, 11, 4))
        twice = randomize_svg(once, date(2026, 11, 5))

        self.assertEqual(once, twice)

    def test_light_and_dark_palettes_use_their_own_green_variables(self) -> None:
        light = randomize_svg(LIGHT_SVG, date(2026, 11, 4))
        dark = randomize_svg(DARK_SVG, date(2026, 11, 4))

        for svg in (light, dark):
            ET.fromstring(svg)
            self.assertIn(".c.sim0{fill:var(--c", svg)
        self.assertIn("--c1:#9be9a8", light)
        self.assertIn("--c1:#0e4429", dark)


if __name__ == "__main__":
    unittest.main()
