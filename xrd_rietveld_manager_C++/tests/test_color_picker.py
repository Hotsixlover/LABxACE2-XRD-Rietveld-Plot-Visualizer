# SPDX-License-Identifier: GPL-2.0-or-later
import tempfile
import unittest
from pathlib import Path

from xrd_rietveld_manager.color_picker import (
    ColorPickerDialog,
    MAX_SAVED_COLORS,
    _load_saved_colors,
    _notice_screen_position,
    _screen_to_capture_point,
    _store_saved_colors,
)


class ColorPickerTests(unittest.TestCase):
    def test_hsv_picker_reaches_primary_colors(self):
        self.assertEqual(ColorPickerDialog._hsv_color(0.0, 1.0, 1.0), "#ff0000")
        self.assertEqual(ColorPickerDialog._hsv_color(1 / 3, 1.0, 1.0), "#00ff00")
        self.assertEqual(ColorPickerDialog._hsv_color(2 / 3, 1.0, 1.0), "#0000ff")

    def test_saved_colors_are_normalized_deduplicated_and_persistent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "saved_colors.json"
            self.assertTrue(_store_saved_colors(["red", "#FF0000", "#123456"], path))
            self.assertEqual(_load_saved_colors(path), ["#ff0000", "#123456"])

    def test_saved_colors_are_limited(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "saved_colors.json"
            colors = [f"#{index:06x}" for index in range(MAX_SAVED_COLORS + 5)]
            self.assertTrue(_store_saved_colors(colors, path))
            self.assertEqual(len(_load_saved_colors(path)), MAX_SAVED_COLORS)

    def test_role_presets_are_removed_from_active_picker(self):
        constants = ColorPickerDialog._build_ui.__code__.co_consts
        self.assertNotIn("Role presets", constants)
        self.assertIn("Color Palette", constants)
        self.assertIn("Color List", constants)

    def test_screen_picker_has_visible_click_instructions(self):
        constants = ColorPickerDialog._open_eyedropper_overlay.__code__.co_consts
        self.assertTrue(any(
            isinstance(value, str) and "Click anywhere on the screen" in value
            for value in constants
        ))

    def test_screen_picker_banner_uses_active_monitor_top_center(self):
        self.assertEqual(
            _notice_screen_position((-1920, 0, 0, 1040), 600),
            (-1260, 24),
        )
        self.assertEqual(
            _notice_screen_position((0, 0, 1920, 1040), 600),
            (660, 24),
        )

    def test_secondary_monitor_click_maps_into_full_screen_capture(self):
        virtual = (-1920, 0, 3840, 1080)
        self.assertEqual(
            _screen_to_capture_point(-960, 540, virtual, (3840, 1080)),
            (960, 540),
        )
        self.assertEqual(
            _screen_to_capture_point(960, 540, virtual, (3840, 1080)),
            (2880, 540),
        )


if __name__ == "__main__":
    unittest.main()
