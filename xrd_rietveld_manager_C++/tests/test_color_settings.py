# SPDX-License-Identifier: GPL-2.0-or-later
import tkinter as tk
import unittest
from types import SimpleNamespace

from xrd_rietveld_manager.color_settings import (
    ColorSettingsDialog,
    ColorSettingsMixin,
    normalize,
)
from xrd_rietveld_manager.palettes import available_palette_names


class _ColorSettingsHarness(ColorSettingsMixin):
    def __init__(self, root):
        self.root = root
        self.ui_bg = "#eef1f5"
        self.ui_surface = "#f5f7fa"
        self.ui_panel = "#ffffff"
        self.ui_border = "#d9dee7"
        self.ui_text = "#202124"
        self.ui_muted = "#6b7280"
        self.ui_accent = "#4285f4"
        self.ui_accent_deep = "#245fbe"
        self.ui_button_light = "#eef1f5"
        self.ui_font = ("Calibri", 9)
        self.ui_font_bold = ("Calibri", 9, "bold")
        self.loaded_files = {}
        self.reference_peaks = []
        self.plot_memos = []
        self.element_colors = {}
        self.plot_bg_enabled = False
        self.plot_bg_mode = "solid"
        self.preview_requests = 0

    def _phase_color_group_key(self, _loader, role):
        return str(role).casefold()

    def _apply_phase_group_color(self, _group, _color):
        pass

    def _set_residual_label_color_preview(self):
        pass

    def _set_plot_memo_color_label(self):
        pass

    def rebuild_layer_controls(self):
        pass

    def _request_draw_plot(self):
        self.preview_requests += 1


class ColorSettingsTests(unittest.TestCase):
    def test_3d_curves_category_is_immediately_right_of_labels(self):
        groups = ColorSettingsDialog.GROUPS
        self.assertNotIn("Files & 3D", groups)
        self.assertEqual(groups[groups.index("Labels & Guides") + 1], "3D Curves")

    def test_active_dialog_contains_theme_button_builder(self):
        self.assertTrue(hasattr(ColorSettingsDialog, "_theme_button"))
        self.assertTrue(hasattr(ColorSettingsDialog, "_theme_checkbutton"))
        self.assertIn("theme_bg", ColorSettingsDialog.__init__.__code__.co_names)
        self.assertNotIn("grab_set", ColorSettingsDialog.__init__.__code__.co_names)
        self.assertNotIn("grab_set", ColorSettingsDialog.pick.__code__.co_names)
        self.assertIn("RoundedScrollbar", ColorSettingsDialog._build_scroller.__code__.co_names)

    def test_curve_file_header_has_no_palette_button(self):
        constants = ColorSettingsDialog._build_curve_file_header.__code__.co_consts
        self.assertNotIn("Palette", constants)
        self.assertFalse(hasattr(ColorSettingsDialog, "apply_color_list_to_file"))

    def test_data_curve_rows_use_fixed_alignment_columns(self):
        self.assertEqual(
            ColorSettingsDialog.ROW_COLUMN_MINSIZES,
            (54, 0, 126, 58, 48, 68),
        )
        self.assertFalse(ColorSettingsDialog._show_column_heading("Data Curves"))
        self.assertFalse(ColorSettingsDialog._show_column_heading("Phases"))
        self.assertFalse(ColorSettingsDialog._show_column_heading("Reference Peaks"))
        self.assertFalse(ColorSettingsDialog._show_column_heading("Labels & Guides"))

    def test_normalize_accepts_hex_and_auto(self):
        self.assertEqual(normalize("4285F4"), "#4285f4")
        self.assertEqual(normalize("auto", allow_auto=True), "auto")
        with self.assertRaises(ValueError):
            normalize("auto", allow_auto=False)

    def test_primary_data_curves_only_expose_line_color(self):
        app = _ColorSettingsHarness(None)
        roles = ("Observed", "Calculated", "Background", "Difference")
        styles = {
            role: {
                "color": "#112233",
                "markerfacecolor": "#445566",
                "markeredgecolor": "#778899",
            }
            for role in roles
        }
        styles["Fe2O3"] = {
            "color": "#00aa55", "markerfacecolor": "auto",
            "markeredgecolor": "auto", "fill_color": "#00aa55",
        }
        loader = SimpleNamespace(
            filename="sample.dia", project_color="#123456", styles=styles,
            phase_names=["Fe2O3"], display_names={"Fe2O3": "Fe2O3"}, visibility={},
            _get_default_style=lambda role: {"color": "black"},
        )
        app.loaded_files = {"sample.dia": loader}
        rows = app._color_setting_rows()
        for role in roles:
            role_rows = [row for row in rows if row["tab"] == "Data" and f" / {role} / " in row["label"]]
            self.assertEqual([row["key"] for row in role_rows], ["color"])
        phase_keys = [row["key"] for row in rows if row["tab"] == "Phases"]
        self.assertEqual(phase_keys, ["color", "fill_color"])
        phase_color = next(row for row in rows if row["tab"] == "Phases" and row["key"] == "color")
        self.assertEqual(phase_color["default"], "#00aa55")
        project_color = next(row for row in rows if row["kind"] == "file")
        self.assertEqual(project_color["default"], "#123456")

    def test_curve_rows_expose_file_and_compact_role_label(self):
        loader = SimpleNamespace(filename="sample-a.dia")
        row = {
            "kind": "style",
            "target": (loader, "Calculated", None),
            "label": "sample-a.dia / Calculated / Line",
        }
        grouped_loader, label = ColorSettingsDialog._curve_row_context(row)
        self.assertIs(grouped_loader, loader)
        self.assertEqual(label, "Calculated / Line")

    def test_label_colors_are_grouped_by_plot_function(self):
        group_for = ColorSettingsDialog._label_group_for_row
        self.assertEqual(group_for({"key": "reference_label"}), "Reference Panel")
        self.assertEqual(group_for({"key": "reference_separator"}), "Reference Panel")
        self.assertEqual(group_for({"key": "reference_background"}), "Reference Panel")
        self.assertEqual(group_for({"key": "legend_text"}), "Legend")
        self.assertEqual(group_for({"key": "residual_label_color"}), "Residual Panel")
        self.assertEqual(group_for({"key": "plot_bg_grad_start"}), "Plot Background & 3D")
        self.assertEqual(group_for({"key": "axis_label_color"}), "Axes & Guides")

    def test_hidden_files_and_layers_are_omitted(self):
        app = _ColorSettingsHarness(None)

        def make_loader(filename, global_visible=True):
            return SimpleNamespace(
                filename=filename, project_color="#123456", default_project_color="#123456",
                global_visible=global_visible,
                styles={
                    "Observed": {"color": "black"},
                    "Calculated": {"color": "red"},
                    "Fe2O3": {"color": "#00aa55"},
                },
                default_styles={}, phase_names=["Fe2O3"],
                display_names={"Fe2O3": "Fe2O3"},
                visibility={"Observed": True, "Calculated": False, "Fe2O3": True},
                _get_default_style=lambda role: {"color": "black"},
            )

        app.loaded_files = {
            "visible.dia": make_loader("visible.dia"),
            "hidden.dia": make_loader("hidden.dia", global_visible=False),
        }
        rows = app._color_setting_rows()
        labels = [row["label"] for row in rows]
        self.assertTrue(any("visible.dia / Observed" in label for label in labels))
        self.assertFalse(any("visible.dia / Calculated" in label for label in labels))
        self.assertFalse(any("hidden.dia" in label for label in labels))

    def test_phase_rows_follow_layer_order_for_color_list_assignment(self):
        app = _ColorSettingsHarness(None)
        loader = SimpleNamespace(
            filename="ordered.dia",
            project_color="#123456",
            default_project_color="#123456",
            global_visible=True,
            styles={
                "Observed": {"color": "black"},
                "phase_a": {"color": "#aa0000", "fill_color": "#aa0000"},
                "phase_b": {"color": "#0000aa", "fill_color": "#0000aa"},
            },
            default_styles={},
            phase_names=["phase_a", "phase_b"],
            display_names={"phase_a": "A", "phase_b": "B"},
            visibility={"Observed": True, "phase_a": True, "phase_b": True},
            layer_order=["Observed", "phase_b", "phase_a"],
            _get_default_style=lambda role: {"color": "black"},
        )
        app.loaded_files = {"ordered.dia": loader}

        phase_rows = [
            row for row in app._color_setting_rows()
            if row["tab"] == "Phases"
        ]

        self.assertEqual(
            [row["label"] for row in phase_rows],
            ["B / Line", "B / Area fill", "A / Line", "A / Area fill"],
        )

    def test_reference_color_list_follows_current_reference_peak_order(self):
        reference_a = {"label": "A", "color": "#aa0000"}
        reference_b = {"label": "B", "color": "#0000aa"}
        dialog = object.__new__(ColorSettingsDialog)
        dialog.app = SimpleNamespace(reference_peaks=[reference_b, reference_a])
        dialog.rows = [
            {"tab": "References", "kind": "mapping", "target": reference_a},
            {"tab": "References", "kind": "mapping", "target": reference_b},
        ]

        indexes = ColorSettingsDialog._ordered_section_indices(
            dialog, "Reference Peaks", [0, 1]
        )

        self.assertEqual(indexes, [1, 0])

    def test_dialog_builds_role_groups_and_color_lists(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk is unavailable: {exc}")
        root.withdraw()
        try:
            app = _ColorSettingsHarness(root)
            dialog = ColorSettingsDialog(app)
            dialog.withdraw()
            self.assertEqual(tuple(dialog.section_buttons), ColorSettingsDialog.GROUPS)
            self.assertEqual(dialog.active_section, "Labels & Guides")
            self.assertEqual(dialog.COLOR_LIST, tuple(available_palette_names()))
            self.assertFalse(hasattr(dialog, "PRESETS"))
            self.assertTrue(all("default" in row for row in dialog.rows))
            dialog.cancel()
            self.assertGreaterEqual(app.preview_requests, 1)
        finally:
            root.destroy()

    def test_cancel_helper_restores_observed_custom_flag(self):
        style_existing = {"observed_custom_color": False}
        style_missing = {}
        ColorSettingsDialog._restore_observed_flags([
            (style_existing, True, False),
            (style_missing, False, False),
        ])
        self.assertFalse(style_existing["observed_custom_color"])
        self.assertNotIn("observed_custom_color", style_missing)

    def test_color_list_uses_color_director_palettes(self):
        self.assertEqual(ColorSettingsDialog.COLOR_LIST, tuple(available_palette_names()))
        self.assertIn("Journal Muted", ColorSettingsDialog.COLOR_LIST)
        self.assertIn("Matplotlib Viridis", ColorSettingsDialog.COLOR_LIST)
        self.assertTrue(hasattr(ColorSettingsDialog, "apply_color_list"))

    def test_color_list_can_be_reversed(self):
        forward = ColorSettingsDialog._color_list_colors("Journal Muted", 8)
        reverse = ColorSettingsDialog._color_list_colors("Journal Muted", 8, True)
        self.assertEqual(reverse, list(reversed(forward)))

    def test_color_list_is_disabled_for_labels_only(self):
        enabled = ColorSettingsDialog._color_list_enabled_for_section
        self.assertFalse(enabled("Labels & Guides"))
        self.assertTrue(enabled("Data Curves"))
        self.assertTrue(enabled("Phases"))

    def test_color_scope_filters_current_category_role_and_file(self):
        loader_a = SimpleNamespace(filename="a.dia")
        loader_b = SimpleNamespace(filename="b.dia")
        rows = [
            {"tab": "Data", "kind": "style", "target": (loader_a, "Observed", None)},
            {"tab": "Data", "kind": "style", "target": (loader_a, "Calculated", None)},
            {"tab": "Data", "kind": "style", "target": (loader_b, "Observed", None)},
            {"tab": "Phases", "kind": "phase", "target": (loader_a, "FeO", "feo")},
        ]
        dialog = object.__new__(ColorSettingsDialog)
        dialog.rows = rows
        dialog.active_section = "Data Curves"
        dialog._apply_scope_targets = {}
        dialog.apply_scope = SimpleNamespace(get=lambda: "All curves")
        all_curves = ColorSettingsDialog._color_scope_indices(
            dialog, scope=("category", None)
        )
        observed = ColorSettingsDialog._color_scope_indices(
            dialog, scope=("role", "Observed")
        )
        file_a = ColorSettingsDialog._color_scope_indices(
            dialog, scope=("file", loader_a)
        )
        phases = ColorSettingsDialog._color_scope_indices(
            dialog, section="Phases", scope=("category", None)
        )
        self.assertEqual(all_curves, [0, 1, 2])
        self.assertEqual(observed, [0, 2])
        self.assertEqual(file_a, [0, 1])
        self.assertEqual(phases, [3])

    def test_moved_rules_and_line_effect_update_shared_app_state(self):
        class ValueStub:
            def __init__(self, value):
                self.value = value

            def get(self):
                return self.value

        app = SimpleNamespace(draw_requests=0)
        app._request_draw_plot = lambda: setattr(app, "draw_requests", app.draw_requests + 1)
        dialog = SimpleNamespace(
            app=app,
            rule_lock_var=ValueStub(False),
            rule_preserve_var=ValueStub(True),
            line_effects_enabled_var=ValueStub(True),
            line_effect_var=ValueStub("glow"),
        )
        ColorSettingsDialog._apply_rule_effect_settings(dialog)
        self.assertFalse(app.lock_same_phase_colors)
        self.assertTrue(app.preserve_manual_colors)
        self.assertTrue(app.art_effects_enabled)
        self.assertEqual(app.art_line_effect, "glow")
        self.assertEqual(app.draw_requests, 1)


if __name__ == "__main__":
    unittest.main()
