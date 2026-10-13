# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *
from xrd_rietveld_manager.branding import APP_NAME, APP_VERSION


class TemplateManagerMixin:
    def _get_ui_value(self, attr, fallback=None):
        obj = getattr(self, attr, None)
        if obj is None:
            return fallback
        try:
            return obj.get()
        except Exception:
            return fallback

    def _set_ui_value(self, attr, value):
        obj = getattr(self, attr, None)
        if obj is None:
            return False
        try:
            obj.set(value)
            return True
        except Exception:
            return False

    def _json_safe(self, value):
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, dict):
            return {str(k): self._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe(v) for v in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _collect_template_data(self):
        ordered_paths = list(self.file_tree.get_children()) if hasattr(self, "file_tree") else list(self.loaded_files.keys())
        files = {}
        for path in ordered_paths:
            loader = self.loaded_files.get(path)
            if loader is None:
                continue
            files[path] = {
                "filename": loader.filename,
                "project_color": getattr(loader, "project_color", "#000000"),
                "global_visible": bool(loader.global_visible),
                "display_names": dict(loader.display_names),
                "visibility": dict(loader.visibility),
                "styles": self._json_safe(loader.styles),
                "offsets": self._json_safe(loader.offsets),
                "layer_order": list(self._get_loader_layer_order(loader)),
                "phase_auto_stack_order": list(getattr(loader, "phase_auto_stack_order", [])),
                "phase_auto_stack_offsets": self._json_safe(
                    getattr(loader, "phase_auto_stack_offsets", {})
                ),
            }

        settings = {
            "element_colors": dict(getattr(self, "element_colors", {})),
            "var_3d": bool(self._get_ui_value("var_3d", self.is_3d_mode)),
            "crosshair_enabled": bool(self.crosshair_enabled),
            "bg_sub_enabled": bool(self.bg_sub_enabled),
            "custom_xlim": list(self.custom_xlim) if self.custom_xlim else None,
            "custom_ylim": list(self.custom_ylim) if getattr(self, "custom_ylim", None) else None,
            "y_autoscale_to_x_range": bool(self._get_ui_value("var_y_autoscale_to_x_range", self.y_autoscale_to_x_range)),
            "normalize_y_in_x_range": bool(self._get_ui_value("var_normalize_y_in_x_range", self.normalize_y_in_x_range)),
            "y_autoscale_padding_percent": float(self._get_ui_value("var_y_autoscale_padding", self.y_autoscale_padding_percent)),
            "intensity_scale": float(self._get_ui_value("var_int_scale", self.intensity_scale)),
            "depth_scale": float(self._get_ui_value("var_depth_scale", self.depth_scale)),
            "show_legend": bool(self._get_ui_value("var_show_legend", True)),
            "merge_legend": bool(self._get_ui_value("var_merge_legend", True)),
            "show_residual": bool(self._get_ui_value("var_show_residual", True)),
            "link_same_phase_colors": bool(self._get_ui_value("var_link_phase_colors", True)),
            "show_phase_peaks_top": bool(self._get_ui_value("var_show_phase_peaks_top", self.show_phase_peaks_top)),
            "show_phase_display_labels": bool(self._get_ui_value("var_show_phase_display_labels", self.show_phase_display_labels)),
            "phase_display_label_position": str(self._get_ui_value("var_phase_display_label_position", self.phase_display_label_position)),
            "phase_display_label_size": max(6, min(30, int(self._get_ui_value("var_phase_display_label_size", self.phase_display_label_size)))),
            "phase_display_label_bold": bool(self._get_ui_value("var_phase_display_label_bold", self.phase_display_label_bold)),
            "phase_label_vertical_shift": float(self._get_ui_value("var_phase_label_vertical_shift", self.phase_label_vertical_shift)),
            "legend_transparent": bool(self._get_ui_value("var_legend_transparent", self.legend_transparent)),
            "legend_font_size": max(6, min(30, int(self._get_ui_value("var_legend_font_size", self.legend_font_size)))),
            "legend_bold": bool(self._get_ui_value("var_legend_bold", getattr(self, "legend_bold", False))),
            "legend_orientation": str(self._get_ui_value("var_legend_orientation", self.legend_orientation)),
            "legend_column_mode": str(self._get_ui_value("var_legend_column_mode", self.legend_column_mode)),
            "legend_ncol": int(self._get_ui_value("var_legend_ncol", self.legend_ncol)),
            "legend_max_width": int(self._get_ui_value("var_legend_max_width", int(self.legend_max_width_ratio * 100))),
            "legend_location": str(self._get_ui_value("var_legend_location", self.legend_location)),
            "plot_layout": str(self._get_ui_value("var_plot_layout", self.plot_layout_mode)),
            "panel_canvas_mode": str(self._get_ui_value("var_panel_canvas_mode", self.panel_canvas_mode)),
            "plot_aspect_ratio": str(self._get_ui_value("var_plot_aspect_ratio", self.plot_aspect_ratio)),
            "custom_plot_aspect_ratio": str(self._get_ui_value("var_custom_plot_aspect_ratio", self.custom_plot_aspect_ratio)),
            "show_split_panel_titles": bool(self._get_ui_value("var_show_split_panel_titles", self.show_split_panel_titles)),
            "split_panel_title_source": str(self._get_ui_value("var_split_panel_title_source", self.split_panel_title_source)),
            "split_arrangement": str(self._get_ui_value("var_split_arrangement", self.split_arrangement)),
            "split_panel_title_size": int(self._get_ui_value("var_split_panel_title_size", self.split_panel_title_size)),
            "plot_title_text": str(self._get_ui_value("var_plot_title", self.plot_title_text)),
            "plot_title_bold": bool(self._get_ui_value("var_plot_title_bold", self.plot_title_bold)),
            "plot_title_drag_enabled": bool(self._get_ui_value("var_plot_title_drag", self.plot_title_drag_enabled)),
            "plot_title_pos": list(self.plot_title_pos),
            "plot_title_size": int(self._get_ui_value("var_title_size", 12)),
            "zoom_panels_enabled": bool(self._get_ui_value("var_zoom_panels_enabled", self.zoom_panels_enabled)),
            "zoom_panel_ranges": str(self._get_ui_value("var_zoom_panel_ranges", self.zoom_panel_ranges)),
            "zoom_panel_width": float(self._get_ui_value("var_zoom_panel_width", self.zoom_panel_width)),
            "zoom_panel_gap": float(self._get_ui_value("var_zoom_panel_gap", self.zoom_panel_gap)),
            "zoom_highlight_ranges": bool(self._get_ui_value("var_zoom_highlight_ranges", self.zoom_highlight_ranges)),
            "plot_top_space": float(self._get_ui_value("var_plot_top_space", self.plot_top_space)),
            "plot_memos_enabled": bool(self._get_ui_value("var_plot_memos_enabled", self.plot_memos_enabled)),
            "plot_memo_default_font": self._get_ui_value("var_plot_memo_font", self.plot_memo_default_font),
            "plot_memo_default_size": int(self._get_ui_value("var_plot_memo_size", self.plot_memo_default_size)),
            "plot_memo_default_bold": bool(self._get_ui_value("var_plot_memo_bold", self.plot_memo_default_bold)),
            "plot_memo_default_color": self.plot_memo_default_color,
            "plot_memos": list(getattr(self, "plot_memos", [])),
            "reference_peaks_enabled": bool(self._get_ui_value("var_reference_peaks_enabled", self.reference_peaks_enabled)),
            "reference_wavelength": float(self._get_ui_value("var_reference_wavelength", self.reference_wavelength)),
            "reference_panel_height": float(self._get_ui_value("var_reference_panel_height", self.reference_panel_height)),
            "reference_label_size": int(self._get_ui_value("var_reference_label_size", self.reference_label_size)),
            "reference_label_bold": bool(self._get_ui_value("var_reference_label_bold", self.reference_label_bold)),
            "reference_label_position": str(self._get_ui_value("var_reference_label_position", self.reference_label_position)),
            "reference_stick_width": float(self._get_ui_value("var_reference_stick_width", self.reference_stick_width)),
            "reference_peaks": self._json_safe([{"path": ref.get("path"), "label": ref.get("label"), "color": ref.get("color"), "visible": ref.get("visible", True), "height": ref.get("height", 1.0)} for ref in getattr(self, "reference_peaks", [])]),
            "grid_x": bool(self._get_ui_value("var_grid_x", self.show_grid_x)),
            "grid_y": bool(self._get_ui_value("var_grid_y", self.show_grid_y)),
            "tick_direction_2d": str(self.cmb_tick_dir_2d.get()) if hasattr(self, "cmb_tick_dir_2d") else self.tick_direction_2d,
            "tick_length_2d": float(self._get_ui_value("var_tick_length_2d", self.tick_length_2d)),
            "minor_tick_length_2d": float(self._get_ui_value("var_minor_tick_length_2d", self.minor_tick_length_2d)),
            "tick_width_2d": float(self._get_ui_value("var_tick_width_2d", self.tick_width_2d)),
            "show_tick_x_2d": bool(self._get_ui_value("var_tick_x_2d", self.show_tick_x_2d)),
            "show_tick_y_2d": bool(self._get_ui_value("var_tick_y_2d", self.show_tick_y_2d)),
            "show_minor_tick_x_2d": bool(self._get_ui_value("var_minor_tick_x_2d", self.show_minor_tick_x_2d)),
            "show_minor_tick_y_2d": bool(self._get_ui_value("var_minor_tick_y_2d", self.show_minor_tick_y_2d)),
            "show_tick_label_x_2d": bool(self._get_ui_value("var_tick_label_x_2d", self.show_tick_label_x_2d)),
            "show_tick_label_y_2d": bool(self._get_ui_value("var_tick_label_y_2d", self.show_tick_label_y_2d)),
            "tick_label_size": int(self._get_ui_value("var_tick_label_size", self.tick_label_size)),
            "tick_label_bold": bool(self._get_ui_value("var_tick_label_bold", self.tick_label_bold)),
            "tick_label_font": str(self._get_ui_value("var_tick_label_font", self.tick_label_font)),
            "tick_label_color": str(self._get_ui_value("var_tick_label_color", self.tick_label_color)),
            "tick_label_x_rotation": float(self._get_ui_value("var_tick_label_x_rotation", self.tick_label_x_rotation)),
            "tick_label_y_rotation": float(self._get_ui_value("var_tick_label_y_rotation", self.tick_label_y_rotation)),
            "max_x_tick_labels": int(self._get_ui_value("var_max_x_tick_labels", self.max_x_tick_labels)),
            "max_y_tick_labels": int(self._get_ui_value("var_max_y_tick_labels", self.max_y_tick_labels)),
            "show_axis_title_x_2d": bool(self._get_ui_value("var_axis_title_x_2d", self.show_axis_title_x_2d)),
            "show_axis_title_y_2d": bool(self._get_ui_value("var_axis_title_y_2d", self.show_axis_title_y_2d)),
            "axis_label_size": int(self._get_ui_value("var_axis_size", 10)),
            "axis_label_bold": bool(self._get_ui_value("var_axis_label_bold", self.axis_label_bold)),
            "axis_label_font": str(self._get_ui_value("var_axis_label_font", self.axis_label_font)),
            "axis_label_color": str(self._get_ui_value("var_axis_label_color", self.axis_label_color)),
            "axis_label_x_pad": float(self._get_ui_value("var_axis_label_x_pad", self.axis_label_x_pad)),
            "axis_label_y_pad": float(self._get_ui_value("var_axis_label_y_pad", self.axis_label_y_pad)),
            "axis_label_y_coord": float(self._get_ui_value("var_axis_label_y_coord", self.axis_label_y_coord)),
            "plot_box_linewidth": float(self._get_ui_value("var_plot_box_linewidth", self.plot_box_linewidth)),
            "fixed_plot_box_enabled": bool(self._get_ui_value("var_fixed_plot_box_enabled", self.fixed_plot_box_enabled)),
            "plot_box_width_cm": float(self._get_ui_value("var_plot_box_width_cm", self.plot_box_width_cm)),
            "plot_box_height_cm": float(self._get_ui_value("var_plot_box_height_cm", self.plot_box_height_cm)),
            "residual_ratio": float(self._get_ui_value("var_resid_ratio", self.residual_ratio)),
            "residual_scale": float(self._get_ui_value("var_resid_scale", self.residual_scale)),
            "residual_label_color": self.residual_label_color,
            "residual_label_size": max(6, min(30, int(self._get_ui_value("var_resid_size", 10)))),
            "plot_bg_enabled": bool(self._get_ui_value("var_plot_bg_enabled", self.plot_bg_enabled)),
            "plot_bg_mode": str(self._get_ui_value("var_plot_bg_mode", self.plot_bg_mode)),
            "plot_bg_color": str(self._get_ui_value("var_plot_bg_color", self.plot_bg_color)),
            "plot_bg_grad_start": str(self._get_ui_value("var_plot_bg_grad_start", self.plot_bg_grad_start)),
            "plot_bg_grad_end": str(self._get_ui_value("var_plot_bg_grad_end", self.plot_bg_grad_end)),
            "plot_bg_direction": str(self._get_ui_value("var_plot_bg_direction", self.plot_bg_direction)),
            "plot_bg_alpha": float(self._get_ui_value("var_plot_bg_alpha", self.plot_bg_alpha)),
            "art_effects_enabled": bool(self._get_ui_value("var_art_effects_enabled", self.art_effects_enabled)),
            "art_line_effect": str(self._get_ui_value("var_art_line_effect", self.art_line_effect)),
            "art_text_halo": bool(self._get_ui_value("var_art_text_halo", self.art_text_halo)),
            "art_marker_depth": bool(self._get_ui_value("var_art_marker_depth", self.art_marker_depth)),
            "art_label_adjust": bool(self._get_ui_value("var_art_label_adjust", self.art_label_adjust)),
            "art_palette_name": str(self._get_ui_value("var_art_palette", self.art_palette_name)),
            "view_ylabel": str(self._get_ui_value("var_ylabel", "Scan / Depth")),
            "view_tick_direction": self.cmb_tick_dir.get() if hasattr(self, "cmb_tick_dir") else "in",
            "view_tick_x": bool(self._get_ui_value("var_tick_x", True)),
            "view_tick_y": bool(self._get_ui_value("var_tick_y", False)),
            "view_tick_z": bool(self._get_ui_value("var_tick_z", False)),
        }

        return {
            "template_version": 1,
            "app": APP_NAME,
            "app_version": APP_VERSION,
            "settings": self._json_safe(settings),
            "phase_name_overrides": dict(self.phase_name_overrides),
            "phase_color_overrides": dict(self.phase_color_overrides),
            "split_titles": {
                "main": dict(self.split_main_title_overrides),
                "diff": dict(self.split_diff_title_overrides),
                "main_size": self._json_safe(self.split_main_title_size_overrides),
                "diff_size": self._json_safe(self.split_diff_title_size_overrides),
            },
            "file_order": ordered_paths,
            "file_order_basenames": [os.path.basename(p) for p in ordered_paths],
            "files": files,
        }

    def _apply_template_data(self, tpl):
        if not isinstance(tpl, dict):
            raise ValueError("Invalid template format.")

        settings = tpl.get("settings", {})
        if isinstance(settings, dict):
            from xrd_rietveld_manager.color_settings import PLOT_COLORS, normalize
            restored_colors = {}
            saved_colors = settings.get("element_colors", {})
            if not isinstance(saved_colors, dict):
                saved_colors = {}
            for key, value in saved_colors.items():
                if key in PLOT_COLORS:
                    try:
                        restored_colors[key] = normalize(value)
                    except ValueError:
                        pass
            self.element_colors = restored_colors
            bool_vars = {
                "var_3d": "var_3d",
                "show_legend": "var_show_legend",
                "merge_legend": "var_merge_legend",
                "show_residual": "var_show_residual",
                "link_same_phase_colors": "var_link_phase_colors",
                "show_phase_peaks_top": "var_show_phase_peaks_top",
                "legend_transparent": "var_legend_transparent",
                "legend_bold": "var_legend_bold",
                "show_split_panel_titles": "var_show_split_panel_titles",
                "plot_title_bold": "var_plot_title_bold",
                "plot_title_drag_enabled": "var_plot_title_drag",
                "zoom_panels_enabled": "var_zoom_panels_enabled",
                "zoom_highlight_ranges": "var_zoom_highlight_ranges",
                "plot_memos_enabled": "var_plot_memos_enabled",
                "plot_memo_default_bold": "var_plot_memo_bold",
                "reference_peaks_enabled": "var_reference_peaks_enabled",
                "reference_label_bold": "var_reference_label_bold",
                "grid_x": "var_grid_x",
                "grid_y": "var_grid_y",
                "show_tick_x_2d": "var_tick_x_2d",
                "show_tick_y_2d": "var_tick_y_2d",
                "show_minor_tick_x_2d": "var_minor_tick_x_2d",
                "show_minor_tick_y_2d": "var_minor_tick_y_2d",
                "show_tick_label_x_2d": "var_tick_label_x_2d",
                "show_tick_label_y_2d": "var_tick_label_y_2d",
                "tick_label_bold": "var_tick_label_bold",
                "show_axis_title_x_2d": "var_axis_title_x_2d",
                "show_axis_title_y_2d": "var_axis_title_y_2d",
                "axis_label_bold": "var_axis_label_bold",
                "fixed_plot_box_enabled": "var_fixed_plot_box_enabled",
                "plot_bg_enabled": "var_plot_bg_enabled",
                "art_effects_enabled": "var_art_effects_enabled",
                "art_text_halo": "var_art_text_halo",
                "art_marker_depth": "var_art_marker_depth",
                "art_label_adjust": "var_art_label_adjust",
                "view_tick_x": "var_tick_x",
                "view_tick_y": "var_tick_y",
                "view_tick_z": "var_tick_z",
                "y_autoscale_to_x_range": "var_y_autoscale_to_x_range",
                "normalize_y_in_x_range": "var_normalize_y_in_x_range",
                "show_phase_display_labels": "var_show_phase_display_labels",
                "phase_display_label_bold": "var_phase_display_label_bold",
            }
            value_vars = {
                "intensity_scale": "var_int_scale",
                "depth_scale": "var_depth_scale",
                "legend_font_size": "var_legend_font_size",
                "legend_orientation": "var_legend_orientation",
                "legend_column_mode": "var_legend_column_mode",
                "legend_ncol": "var_legend_ncol",
                "legend_max_width": "var_legend_max_width",
                "legend_location": "var_legend_location",
                "phase_display_label_position": "var_phase_display_label_position",
                "phase_display_label_size": "var_phase_display_label_size",
                "phase_label_vertical_shift": "var_phase_label_vertical_shift",
                "plot_layout": "var_plot_layout",
                "panel_canvas_mode": "var_panel_canvas_mode",
                "plot_aspect_ratio": "var_plot_aspect_ratio",
                "custom_plot_aspect_ratio": "var_custom_plot_aspect_ratio",
                "split_panel_title_source": "var_split_panel_title_source",
                "split_arrangement": "var_split_arrangement",
                "split_panel_title_size": "var_split_panel_title_size",
                "plot_title_text": "var_plot_title",
                "plot_title_size": "var_title_size",
                "zoom_panel_ranges": "var_zoom_panel_ranges",
                "zoom_panel_width": "var_zoom_panel_width",
                "zoom_panel_gap": "var_zoom_panel_gap",
                "plot_top_space": "var_plot_top_space",
                "plot_memo_default_font": "var_plot_memo_font",
                "plot_memo_default_size": "var_plot_memo_size",
                "reference_wavelength": "var_reference_wavelength",
                "reference_panel_height": "var_reference_panel_height",
                "reference_label_size": "var_reference_label_size",
                "reference_label_position": "var_reference_label_position",
                "reference_stick_width": "var_reference_stick_width",
                "tick_length_2d": "var_tick_length_2d",
                "minor_tick_length_2d": "var_minor_tick_length_2d",
                "tick_width_2d": "var_tick_width_2d",
                "tick_label_size": "var_tick_label_size",
                "tick_label_font": "var_tick_label_font",
                "tick_label_color": "var_tick_label_color",
                "tick_label_x_rotation": "var_tick_label_x_rotation",
                "tick_label_y_rotation": "var_tick_label_y_rotation",
                "max_x_tick_labels": "var_max_x_tick_labels",
                "max_y_tick_labels": "var_max_y_tick_labels",
                "axis_label_size": "var_axis_size",
                "axis_label_font": "var_axis_label_font",
                "axis_label_color": "var_axis_label_color",
                "axis_label_x_pad": "var_axis_label_x_pad",
                "axis_label_y_pad": "var_axis_label_y_pad",
                "axis_label_y_coord": "var_axis_label_y_coord",
                "plot_box_linewidth": "var_plot_box_linewidth",
                "plot_box_width_cm": "var_plot_box_width_cm",
                "plot_box_height_cm": "var_plot_box_height_cm",
                "residual_ratio": "var_resid_ratio",
                "residual_scale": "var_resid_scale",
                "residual_label_size": "var_resid_size",
                "plot_bg_mode": "var_plot_bg_mode",
                "plot_bg_color": "var_plot_bg_color",
                "plot_bg_grad_start": "var_plot_bg_grad_start",
                "plot_bg_grad_end": "var_plot_bg_grad_end",
                "plot_bg_direction": "var_plot_bg_direction",
                "plot_bg_alpha": "var_plot_bg_alpha",
                "art_line_effect": "var_art_line_effect",
                "art_palette_name": "var_art_palette",
                "view_ylabel": "var_ylabel",
                "y_autoscale_padding_percent": "var_y_autoscale_padding",
            }
            for key, attr in bool_vars.items():
                if key in settings:
                    self._set_ui_value(attr, bool(settings[key]))
            for key, attr in value_vars.items():
                if key in settings:
                    value = settings[key]
                    if key == "legend_column_mode" and value == "manual":
                        value = "custom"
                    elif key == "reference_label_size":
                        value = max(5, min(30, int(float(value))))
                    self._set_ui_value(attr, value)

            if "tick_direction_2d" in settings and hasattr(self, "cmb_tick_dir_2d"):
                self.cmb_tick_dir_2d.set(str(settings["tick_direction_2d"]))
            if "view_tick_direction" in settings and hasattr(self, "cmb_tick_dir"):
                self.cmb_tick_dir.set(str(settings["view_tick_direction"]))
            if "crosshair_enabled" in settings:
                self.crosshair_enabled = bool(settings["crosshair_enabled"])
                if hasattr(self, "btn_cross"):
                    self.btn_cross.config(relief="sunken" if self.crosshair_enabled else "raised")
            if "bg_sub_enabled" in settings:
                self.bg_sub_enabled = bool(settings["bg_sub_enabled"])
                if hasattr(self, "btn_bg"):
                    self.btn_bg.config(relief="sunken" if self.bg_sub_enabled else "raised")
            if "custom_xlim" in settings:
                custom_xlim = settings.get("custom_xlim")
                if isinstance(custom_xlim, (list, tuple)) and len(custom_xlim) == 2:
                    try:
                        self.custom_xlim = (float(custom_xlim[0]), float(custom_xlim[1]))
                    except (TypeError, ValueError):
                        self.custom_xlim = None
                else:
                    self.custom_xlim = None
            if "custom_ylim" in settings:
                custom_ylim = settings.get("custom_ylim")
                if isinstance(custom_ylim, (list, tuple)) and len(custom_ylim) == 2:
                    try:
                        self.custom_ylim = (float(custom_ylim[0]), float(custom_ylim[1]))
                    except (TypeError, ValueError):
                        self.custom_ylim = None
                else:
                    self.custom_ylim = None
            if "plot_title_pos" in settings and isinstance(settings["plot_title_pos"], (list, tuple)) and len(settings["plot_title_pos"]) == 2:
                try:
                    self.plot_title_pos = [float(settings["plot_title_pos"][0]), float(settings["plot_title_pos"][1])]
                except (TypeError, ValueError):
                    pass
            if "plot_memos" in settings and isinstance(settings["plot_memos"], list):
                clean_memos = []
                for memo in settings["plot_memos"]:
                    if not isinstance(memo, dict):
                        continue
                    clean_memos.append({
                        "text": str(memo.get("text", "")),
                        "x": float(memo.get("x", 0.02)),
                        "y": float(memo.get("y", 0.96)),
                        "font": str(memo.get("font", self.plot_memo_default_font)),
                        "size": int(memo.get("size", self.plot_memo_default_size)),
                        "bold": bool(memo.get("bold", self.plot_memo_default_bold)),
                        "color": str(memo.get("color", self.plot_memo_default_color)),
                    })
                self.plot_memos = clean_memos
                if hasattr(self, "_refresh_plot_memo_list"):
                    self._refresh_plot_memo_list()
            if "plot_memo_default_color" in settings:
                self.plot_memo_default_color = str(settings["plot_memo_default_color"])
                if hasattr(self, "_set_plot_memo_color_label"):
                    self._set_plot_memo_color_label()
            if "plot_memo_editor_text" in settings and hasattr(self, "txt_plot_memo"):
                self.txt_plot_memo.delete("1.0", tk.END)
                self.txt_plot_memo.insert("1.0", str(settings["plot_memo_editor_text"]))
            if "reference_peaks" in settings and isinstance(settings["reference_peaks"], list):
                self.reference_peaks = []
                for saved_ref in settings["reference_peaks"]:
                    if not isinstance(saved_ref, dict) or not saved_ref.get("path"):
                        continue
                    if self._add_reference_cif(saved_ref.get("path"), refresh_ui=False, redraw=False, silent=True):
                        ref = self.reference_peaks[-1]
                        ref["label"] = str(saved_ref.get("label", ref.get("label", "Reference")))
                        ref["color"] = str(saved_ref.get("color", ref.get("color", "#555555")))
                        ref["visible"] = bool(saved_ref.get("visible", True))
                        ref["height"] = float(saved_ref.get("height", 1.0))
                if hasattr(self, "_refresh_reference_peak_list"):
                    self._refresh_reference_peak_list()
            if "residual_label_color" in settings:
                self.residual_label_color = str(settings["residual_label_color"])
                if hasattr(self, "_set_residual_label_color_preview"):
                    self._set_residual_label_color_preview()
            for attr in (
                "tick_label_color",
                "axis_label_color",
                "plot_bg_color",
                "plot_bg_grad_start",
                "plot_bg_grad_end",
            ):
                if attr in settings:
                    setattr(self, attr, str(settings[attr]))

        phase_overrides = tpl.get("phase_name_overrides", {})
        if isinstance(phase_overrides, dict):
            self.phase_name_overrides = {str(k): str(v) for k, v in phase_overrides.items()}

        phase_color_overrides = tpl.get("phase_color_overrides", {})
        if isinstance(phase_color_overrides, dict):
            self.phase_color_overrides = {str(k): str(v) for k, v in phase_color_overrides.items()}

        split_titles = tpl.get("split_titles", {})
        if isinstance(split_titles, dict):
            self.split_main_title_overrides = {str(k): str(v) for k, v in split_titles.get("main", {}).items()} if isinstance(split_titles.get("main"), dict) else {}
            self.split_diff_title_overrides = {str(k): str(v) for k, v in split_titles.get("diff", {}).items()} if isinstance(split_titles.get("diff"), dict) else {}
            self.split_main_title_size_overrides = dict(split_titles.get("main_size", {})) if isinstance(split_titles.get("main_size"), dict) else {}
            self.split_diff_title_size_overrides = dict(split_titles.get("diff_size", {})) if isinstance(split_titles.get("diff_size"), dict) else {}

        files = tpl.get("files", {})
        if isinstance(files, dict):
            by_path = files
            by_base = {}
            for saved_path, saved in files.items():
                if isinstance(saved, dict):
                    by_base.setdefault(os.path.basename(saved_path), saved)
                    if saved.get("filename"):
                        by_base.setdefault(os.path.basename(str(saved["filename"])), saved)

            for path, loader in self.loaded_files.items():
                saved = by_path.get(path)
                if not isinstance(saved, dict):
                    saved = by_base.get(os.path.basename(path), {})
                if not isinstance(saved, dict):
                    continue

                if "project_color" in saved:
                    try:
                        from xrd_rietveld_manager.color_settings import normalize
                        loader.project_color = normalize(saved["project_color"])
                    except ValueError:
                        pass
                if "global_visible" in saved:
                    loader.global_visible = bool(saved["global_visible"])
                for attr in (
                    "display_names",
                    "visibility",
                    "styles",
                    "offsets",
                    "phase_auto_stack_offsets",
                ):
                    val = saved.get(attr)
                    if isinstance(val, dict):
                        target = getattr(loader, attr, {})
                        if not isinstance(target, dict):
                            continue
                        for k, v in val.items():
                            target[k] = v
                order = saved.get("phase_auto_stack_order", [])
                if isinstance(order, list):
                    loader.phase_auto_stack_order = [str(p) for p in order if str(p) in loader.phase_names]
                layer_order = saved.get("layer_order", [])
                if isinstance(layer_order, list):
                    loader.layer_order = [str(key) for key in layer_order]
                    self._get_loader_layer_order(loader)
                self._apply_phase_name_overrides_to_loader(loader)

        if self._phase_color_link_enabled():
            for loader in self.loaded_files.values():
                self._apply_phase_color_overrides_to_loader(loader)
            self.sync_phase_colors_by_name(redraw=False, rebuild=False)

        saved_order = tpl.get("file_order", []) if isinstance(tpl.get("file_order", []), list) else []
        saved_bases = tpl.get("file_order_basenames", []) if isinstance(tpl.get("file_order_basenames", []), list) else []
        if hasattr(self, "file_tree") and self.file_tree.get_children():
            current = list(self.file_tree.get_children())
            rank_path = {p: i for i, p in enumerate(saved_order)}
            rank_base = {b: i for i, b in enumerate(saved_bases)}

            def rank(path):
                if path in rank_path:
                    return (0, rank_path[path])
                base = os.path.basename(path)
                if base in rank_base:
                    return (1, rank_base[base])
                return (2, current.index(path))

            for new_idx, path in enumerate(sorted(current, key=rank)):
                self.file_tree.move(path, "", new_idx)

            for path in self.file_tree.get_children():
                loader = self.loaded_files.get(path)
                if loader is not None:
                    self._refresh_file_tree_visibility_item(path, loader)

        if hasattr(self, "_refresh_legend_layout_controls"):
            self._refresh_legend_layout_controls(redraw=False)
        self.rebuild_layer_controls()
        self._draw_plot_now()

    def save_template(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Template JSON", "*.json"), ("All files", "*.*")],
            title=f"{APP_NAME} - Save Template"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._collect_template_data(), f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Template", "Template saved.")
        except Exception as e:
            messagebox.showerror("Template Error", f"Failed to save template.\n{e}")

    def load_template(self):
        path = filedialog.askopenfilename(
            filetypes=[("Template JSON", "*.json"), ("All files", "*.*")],
            title=f"{APP_NAME} - Load Template"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                tpl = json.load(f)
            self._apply_template_data(tpl)
            messagebox.showinfo("Template", "Template loaded.")
        except Exception as e:
            messagebox.showerror("Template Error", f"Failed to load template.\n{e}")

    # ========================================================
    # Logic: Layer Controls & Auto Plot
    # ========================================================

