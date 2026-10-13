# SPDX-License-Identifier: GPL-2.0-or-later
import unittest

from xrd_rietveld_manager.color_director import ColorDirectorMixin
from xrd_rietveld_manager.ui_tabs import UiTabsMixin


class UiTabsThemeTests(unittest.TestCase):
    def test_plot_axes_tab_comes_before_style_tab(self):
        constants = UiTabsMixin._create_plot_section_shell.__code__.co_consts
        section_specs = next(
            value for value in constants
            if isinstance(value, tuple)
            and ("axes", "AXES") in value
            and ("style", "STYLE") in value
        )
        self.assertLess(
            section_specs.index(("axes", "AXES")),
            section_specs.index(("style", "STYLE")),
        )

    def test_axis_number_rotation_card_only_keeps_rotation_controls(self):
        constants = UiTabsMixin._setup_axes_tab.__code__.co_consts
        self.assertIn("Axis Number Rotation", constants)
        self.assertIn("X Rotation:", constants)
        self.assertIn("Y Rotation:", constants)
        self.assertNotIn("Tick Labels", constants)
        self.assertNotIn("Max X Labels:", constants)
        self.assertNotIn("Max Y Labels:", constants)

    def test_plot_quick_tools_are_moved_below_layer_offset_tools(self):
        layer_constants = UiTabsMixin._setup_layers_tab.__code__.co_consts
        plot_constants = UiTabsMixin._setup_plot_tab.__code__.co_consts
        self.assertIn("Offset Tools", layer_constants)
        self.assertIn("Plot Layout", layer_constants)
        self.assertIn("Quick Tools", layer_constants)
        self.assertIn("Combined", layer_constants)
        self.assertIn("Split by File", layer_constants)
        self.assertIn("Crosshair", layer_constants)
        names = UiTabsMixin._setup_layers_tab.__code__.co_names
        self.assertIn("_style_settings_card", names)
        self.assertIn("_make_plot_card_collapsible", names)
        self.assertNotIn("Quick Tools", plot_constants)
        self.assertNotIn("Split by File", plot_constants)

    def test_legacy_color_director_boxes_are_not_built_in_style(self):
        names = ColorDirectorMixin._setup_color_tab.__code__.co_names
        self.assertNotIn("LabelFrame", names)
        self.assertNotIn("_refresh_color_preview", names)

    def test_canvas_sizing_uses_themed_radio_controls(self):
        self.assertTrue(hasattr(UiTabsMixin, "_themed_radio_button"))
        names = UiTabsMixin._setup_main_tab.__code__.co_names
        self.assertIn("_themed_radio_button", names)
        self.assertIn("radio_panel_canvas_fit", names)
        self.assertIn("radio_panel_canvas_preserve", names)


if __name__ == "__main__":
    unittest.main()
