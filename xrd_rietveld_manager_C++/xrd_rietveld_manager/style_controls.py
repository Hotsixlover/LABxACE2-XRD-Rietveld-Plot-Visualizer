# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *
import matplotlib as mpl
from matplotlib.font_manager import FontProperties


from xrd_rietveld_manager.color_settings import ColorSettingsMixin


class StyleControlsMixin(ColorSettingsMixin):
    def pick_residual_label_color(self):
        c = choose_color(self.root, title="Color Setting", initial_color=self.residual_label_color)
        if c:
            self.residual_label_color = c
            self._set_residual_label_color_preview()
            self.draw_plot()

    def _set_residual_label_color_preview(self):
        if not hasattr(self, "lbl_residual_label_color"):
            return
        color = str(getattr(self, "residual_label_color", "#1f77b4"))
        try:
            self.lbl_residual_label_color.configure(
                text=color.upper(),
                bg=color,
                fg=self._memo_color_contrast(color),
            )
        except Exception:
            pass

    def pick_tick_label_color(self):
        base = self.var_tick_label_color.get() if hasattr(self, "var_tick_label_color") else self.tick_label_color
        c = choose_color(self.root, title="Tick Label Color", initial_color=base)
        if c:
            self.tick_label_color = c
            if hasattr(self, "var_tick_label_color"):
                self.var_tick_label_color.set(c)
            self.draw_plot()

    def pick_axis_label_color(self):
        base = self.var_axis_label_color.get() if hasattr(self, "var_axis_label_color") else self.axis_label_color
        c = choose_color(self.root, title="Axis Title Color", initial_color=base)
        if c:
            self.axis_label_color = c
            if hasattr(self, "var_axis_label_color"):
                self.var_axis_label_color.set(c)
            self.draw_plot()

    def pick_plot_bg_color(self):
        base = self.var_plot_bg_color.get() if hasattr(self, "var_plot_bg_color") else self.plot_bg_color
        c = choose_color(self.root, title="Plot Background Color", initial_color=base)
        if c:
            self.plot_bg_color = c
            if hasattr(self, "var_plot_bg_color"):
                self.var_plot_bg_color.set(c)
            self.draw_plot()

    def pick_plot_bg_grad_start(self):
        base = self.var_plot_bg_grad_start.get() if hasattr(self, "var_plot_bg_grad_start") else self.plot_bg_grad_start
        c = choose_color(self.root, title="Plot Gradient Start Color", initial_color=base)
        if c:
            self.plot_bg_grad_start = c
            if hasattr(self, "var_plot_bg_grad_start"):
                self.var_plot_bg_grad_start.set(c)
            self.draw_plot()

    def pick_plot_bg_grad_end(self):
        base = self.var_plot_bg_grad_end.get() if hasattr(self, "var_plot_bg_grad_end") else self.plot_bg_grad_end
        c = choose_color(self.root, title="Plot Gradient End Color", initial_color=base)
        if c:
            self.plot_bg_grad_end = c
            if hasattr(self, "var_plot_bg_grad_end"):
                self.var_plot_bg_grad_end.set(c)
            self.draw_plot()

    def _truncate_label(self, text, max_chars=24):
        if text is None:
            return ""
        text = str(text)
        if len(text) <= max_chars:
            return text
        return text[:max_chars-3] + "..."

    def set_plot_font(self, display_name):
        spec = get_font_spec(display_name)
        self.plot_font_display = spec["display"]
        self.plot_font_family = spec["family"]
        self.plot_base_weight = spec["base_weight"]
        self.plot_font_path = spec["path"]
        mpl.rcParams["font.family"] = self.plot_font_family
        mpl.rcParams["font.sans-serif"] = [self.plot_font_family, "Calibri", "Arial", "DejaVu Sans"]
        mpl.rcParams["font.weight"] = self.plot_base_weight
        mpl.rcParams["axes.labelweight"] = self.plot_base_weight
        mpl.rcParams["axes.titleweight"] = self.plot_base_weight
        mpl.rcParams["mathtext.fontset"] = "custom"
        mpl.rcParams["mathtext.rm"] = self.plot_font_family
        mpl.rcParams["mathtext.it"] = f"{self.plot_font_family}:italic"
        mpl.rcParams["mathtext.bf"] = f"{self.plot_font_family}:bold"
        if hasattr(self, "var_plot_font_display"):
            self.var_plot_font_display.set(self.plot_font_display)
        font_path_text = self.plot_font_path if self.plot_font_path else "Matplotlib fallback"
        for active_label, path_label in getattr(self, "plot_font_status_labels", []):
            try:
                active_label.config(text=f"Active: {self.plot_font_display}")
                path_label.config(text=f"Font file: {font_path_text}")
            except Exception:
                pass
        if hasattr(self, "lbl_active_font"):
            self.lbl_active_font.config(text=f"Active: {self.plot_font_display}")
        if hasattr(self, "lbl_plot_font_path"):
            self.lbl_plot_font_path.config(text=f"Font file: {font_path_text}")
        self._request_draw_plot()

    def _font_prop(self, size=None, weight=None, bold=False):
        weight = "bold" if bold else (weight or self.plot_base_weight)
        kwargs = {"family": self.plot_font_family, "weight": weight}
        if size is not None:
            kwargs["size"] = size
        path = getattr(self, "plot_font_path", None)
        if path and os.path.exists(path) and not bold:
            kwargs["fname"] = path
        return FontProperties(**kwargs)

    def _apply_forced_font(self, text_artist, size=None, weight=None, bold=False):
        if text_artist is None:
            return
        if size is None:
            try:
                size = text_artist.get_fontsize()
            except Exception:
                size = None
        if weight is None and not bold:
            try:
                current_weight = text_artist.get_fontweight()
                current_weight_text = str(current_weight).lower()
                if current_weight_text in ["bold", "heavy", "semibold", "demibold"] or (
                    isinstance(current_weight, (int, float)) and current_weight >= 600
                ):
                    bold = True
                else:
                    weight = self.plot_base_weight
            except Exception:
                weight = self.plot_base_weight
        try:
            text_artist.set_fontproperties(self._font_prop(size=size, weight=weight, bold=bold))
        except Exception:
            try:
                text_artist.set_fontname(self.plot_font_family)
                if size is not None:
                    text_artist.set_fontsize(size)
                text_artist.set_fontweight("bold" if bold else (weight or self.plot_base_weight))
            except Exception:
                pass

    def _apply_axis_grid(self, ax, show_x, show_y, alpha=0.5):
        self.paper_style.apply_axis_grid(ax, show_x, show_y, alpha=alpha)

    def _apply_axis_font(self, ax):
        self.paper_style.apply_axis_font(ax)

    def _get_ratio_height_scale(self):
        ratio = self._parse_ratio(self.plot_aspect_ratio)
        if ratio is None:
            return 1.0
        return max(0.5, min(1.8, 1.0 / float(ratio)))

    def _get_residual_height_weight(self):
        return max(0.15, 0.5 * self.residual_ratio * self._get_ratio_height_scale())

    def _get_ratio_font_scale(self):
        ratio = self._parse_ratio(self.plot_aspect_ratio)
        if ratio is None:
            return 1.0
        return max(0.72, min(1.25, math.sqrt(max(1e-6, 1.0 / float(ratio)))))

    def _scale_font_size(self, value, min_size=6, max_size=96):
        size = int(round(float(value)))
        return max(min_size, min(max_size, size))

    def _scaled_line_width(self, value):
        return max(0.2, float(value) * self._get_ratio_font_scale())

    def _scaled_marker_size(self, value):
        scale = self._get_ratio_font_scale()
        return max(1.0, float(value) * (scale * scale))

    def _get_axis_label_size(self):
        base = int(self.var_axis_size.get()) if hasattr(self, "var_axis_size") else 10
        return self._scale_font_size(base, min_size=6, max_size=72)

    def _get_title_font_size(self):
        base = int(self.var_title_size.get()) if hasattr(self, "var_title_size") else 12
        return self._scale_font_size(base, min_size=8, max_size=96)

    def _get_residual_label_size(self):
        base = int(self.var_resid_size.get()) if hasattr(self, "var_resid_size") else 10
        return self._scale_font_size(base, min_size=6, max_size=30)

    def _get_legend_font_size(self):
        base = self.var_legend_font_size.get() if hasattr(self, "var_legend_font_size") else self.legend_font_size
        return self._scale_font_size(base, min_size=6, max_size=30)

    def _get_axis_label_weight(self):
        is_bold = self.var_axis_label_bold.get() if hasattr(self, "var_axis_label_bold") else self.axis_label_bold
        return "bold" if is_bold else self.plot_base_weight

    def _apply_axis_box_style(self, ax):
        self.paper_style.apply_axis_box_style(ax)

    def _panel_canvas_mode_value(self):
        mode = getattr(self, "panel_canvas_mode", "fit")
        if hasattr(self, "var_panel_canvas_mode"):
            try:
                mode = self.var_panel_canvas_mode.get()
            except Exception:
                pass
        return "preserve" if str(mode).strip().lower() == "preserve" else "fit"

    def _panel_canvas_ratio_is_preserved(self):
        return self._panel_canvas_mode_value() == "preserve"

    def _preserved_canvas_layout_is_active(self):
        return (
            self._panel_canvas_ratio_is_preserved()
            and bool(getattr(self, "_gui_draw_plot_active", False))
        )

    def _record_panel_canvas_scales(self, row_scale=1.0, column_scale=1.0, n_cols=1):
        try:
            scales = (max(1.0, float(row_scale)), max(1.0, float(column_scale)))
        except Exception:
            scales = (1.0, 1.0)
        self._last_panel_canvas_scales = scales
        self._last_panel_canvas_n_cols = max(1, int(n_cols))
        return scales

    def _sync_panel_canvas_mode_transition(self):
        mode = self._panel_canvas_mode_value()
        previous = getattr(self, "_active_panel_canvas_mode", None)
        if mode != previous:
            self._active_panel_canvas_mode = mode
            self._preserved_canvas_expansion = (1.0, 1.0)
            if mode == "preserve":
                # A single main plot is the permanent Fit-sized sheet. Every
                # auxiliary row/column is appended beyond that sheet, so mode
                # toggles always produce a real size change when panels exist.
                self._preserved_panel_baseline_scales = (1.0, 1.0)
                self._preserved_panel_baseline_n_cols = 1
                self._preserved_panel_baseline_compensation = 1.0
            else:
                self._preserved_panel_baseline_scales = None
                self._preserved_panel_baseline_n_cols = None
                self._preserved_panel_baseline_compensation = None
        return mode

    def _preserved_canvas_has_expansion(self):
        try:
            row_factor, column_factor = getattr(self, "_preserved_canvas_expansion", (1.0, 1.0))
            return float(row_factor) > 1.001 or float(column_factor) > 1.001
        except Exception:
            return False

    def on_panel_canvas_mode_change(self):
        self.panel_canvas_mode = self._panel_canvas_mode_value()
        self._active_panel_canvas_mode = None
        self._sync_panel_canvas_mode_transition()
        self._last_resize_size = None
        self._resize_pending_size = None
        self._request_draw_plot(delay_ms=1)

    def _preserved_canvas_pixel_size(self, viewport_width, viewport_height, row_scale=1.0, column_scale=1.0):
        """Expand the current Fit-to-Window canvas by relative panel growth."""
        view_w = max(2.0, float(viewport_width))
        view_h = max(2.0, float(viewport_height))
        row_scale = max(1.0, float(row_scale))
        column_scale = max(1.0, float(column_scale))
        baseline_n_cols = max(1, int(getattr(self, "_preserved_panel_baseline_n_cols", 1) or 1))
        bounds = self._fit_canvas_subplot_bounds(
            view_w,
            view_h,
            baseline_n_cols,
            compensation=getattr(self, "_preserved_panel_baseline_compensation", 1.0),
        )
        left, right, bottom, top = bounds

        # Keep the original margins and content region in absolute pixels. Only
        # append new content pixels, like attaching more paper to the right/bottom.
        fixed_w = view_w * (1.0 - (right - left))
        fixed_h = view_h * (1.0 - (top - bottom))
        target_w = max(2.0, fixed_w + (view_w - fixed_w) * column_scale)
        target_h = max(2.0, fixed_h + (view_h - fixed_h) * row_scale)

        # Protect the interactive renderer from pathological project sizes while
        # scaling both dimensions together so the requested ratio is unchanged.
        max_dimension = 12000.0
        max_area = 48_000_000.0
        downscale = min(
            1.0,
            max_dimension / target_w,
            max_dimension / target_h,
            math.sqrt(max_area / max(1.0, target_w * target_h)),
        )
        return (
            max(2, int(round(target_w * downscale))),
            max(2, int(round(target_h * downscale))),
        )

    def _apply_preserved_panel_canvas_size(self, row_scale=1.0, column_scale=1.0):
        if not self._preserved_canvas_layout_is_active():
            return False
        if hasattr(self, "_fixed_plot_box_is_enabled") and self._fixed_plot_box_is_enabled():
            return False

        viewport = getattr(self, "plot_page_frame", None) or getattr(self, "plot_canvas_view", None)
        if viewport is None:
            return False
        view_w = max(1, int(viewport.winfo_width()))
        view_h = max(1, int(viewport.winfo_height()))
        if view_w <= 1 or view_h <= 1:
            return False
        self._preserved_canvas_base_pixels = (view_w, view_h)
        current_row, current_column = self._record_panel_canvas_scales(
            row_scale, column_scale, getattr(self, "_last_panel_canvas_n_cols", 1)
        )
        baseline = getattr(self, "_preserved_panel_baseline_scales", None)
        if not baseline:
            baseline = (current_row, current_column)
            self._preserved_panel_baseline_scales = baseline
        baseline_row = max(1.0, float(baseline[0]))
        baseline_column = max(1.0, float(baseline[1]))
        row_growth = max(1.0, current_row / baseline_row)
        column_growth = max(1.0, current_column / baseline_column)
        self._preserved_canvas_expansion = (row_growth, column_growth)
        target_w, target_h = self._preserved_canvas_pixel_size(
            view_w, view_h, row_scale=row_growth, column_scale=column_growth
        )
        return self._apply_plot_aspect_ratio(width=target_w, height=target_h)

    def _should_apply_split_panel_ratio(self):
        ratio = self._parse_ratio(self.plot_aspect_ratio)
        if ratio is None:
            return False
        if self.plot_layout_mode != "split":
            return False
        return True

    def _apply_split_panel_aspect(self, ax):
        ratio = self._parse_ratio(self.plot_aspect_ratio)
        if ratio is None:
            return
        # set_box_aspect expects height / width. For W:H ratio, use H/W.
        box_aspect = max(1e-6, 1.0 / float(ratio))
        try:
            ax.set_box_aspect(box_aspect)
            # Keep main panel visually attached to residual panel below.
            ax.set_anchor('S')
        except Exception:
            # Older Matplotlib versions may not support set_box_aspect.
            pass

    def _apply_residual_panel_aspect(self, ax):
        # Keep the residual axis under the same aspect-policy as its main axis.
        # The matching residual fraction makes both axes resolve to the same
        # physical width, including on an expanded Preserve Plot Ratio canvas.
        if not self._should_apply_split_panel_ratio():
            return
        ratio = self._parse_ratio(self.plot_aspect_ratio)
        main_box_aspect = max(1e-6, 1.0 / float(ratio))
        residual_frac = max(0.05, min(0.8, self._get_residual_height_weight() / 3.0))
        try:
            ax.set_box_aspect(main_box_aspect * residual_frac)
            # Keep residual panel attached to the main panel above.
            ax.set_anchor('N')
        except Exception:
            pass

    def _parse_ratio(self, ratio_text):
        try:
            txt = str(ratio_text).strip()
            if txt.lower() in ["auto", "auto scale", ""]:
                return None
            if txt.lower() == "custom":
                txt = str(getattr(self, "custom_plot_aspect_ratio", "1:2")).strip()
                if hasattr(self, "var_custom_plot_aspect_ratio"):
                    try:
                        txt = str(self.var_custom_plot_aspect_ratio.get()).strip()
                    except Exception:
                        pass
            if txt == "16:4":
                txt = "16:9"
            if ":" in txt:
                w_txt, h_txt = txt.split(":", 1)
                w = float(w_txt.strip())
                h = float(h_txt.strip())
            elif "/" in txt:
                w_txt, h_txt = txt.split("/", 1)
                w = float(w_txt.strip())
                h = float(h_txt.strip())
            else:
                w = float(txt)
                h = 1.0
            if w <= 0 or h <= 0:
                raise ValueError
            return w / h
        except Exception:
            return 1.0

    def _get_adaptive_hspace(self, base_hspace, n_rows):
        selected_ratio = self._parse_ratio(self.plot_aspect_ratio)
        aspect = selected_ratio if selected_ratio is not None else self._get_canvas_aspect()
        row_boost = max(0, int(n_rows) - 2) * 0.015
        aspect_boost = max(0.0, aspect - 1.0) * 0.12
        return min(0.55, base_hspace + row_boost + aspect_boost)

    def _get_plot_top_space(self):
        value = getattr(self, "plot_top_space", 0.0)
        if hasattr(self, "var_plot_top_space"):
            try:
                value = self.var_plot_top_space.get()
            except Exception:
                pass
        try:
            return max(0.0, min(0.35, float(value)))
        except Exception:
            return 0.0

    def _fit_canvas_subplot_bounds(self, canvas_width, canvas_height, n_cols=1, compensation=None):
        """Mirror Fit-to-Window subplot bounds for an arbitrary canvas size."""
        canvas_width = max(1.0, float(canvas_width))
        canvas_height = max(1.0, float(canvas_height))
        canvas_aspect = canvas_width / canvas_height
        target_ratio = self._parse_ratio(self.plot_aspect_ratio)
        if compensation is None:
            compensation = getattr(self, "_grid_target_ratio_compensation", 1.0)
        try:
            compensation = max(0.05, min(1.0, float(compensation or 1.0)))
            if target_ratio is not None:
                target_ratio *= compensation
            elif compensation < 0.999:
                target_ratio = canvas_aspect * compensation
        except Exception:
            pass
        if self.plot_layout_mode == "split" and target_ratio is not None:
            target_ratio = None

        if int(n_cols) > 1:
            base_left, base_right_margin = 0.06, 0.02
        else:
            base_left, base_right_margin = 0.08, 0.05
        top_margin = 0.04 if canvas_aspect >= 1.4 else 0.05
        top_margin = min(0.45, top_margin + self._get_plot_top_space())
        bottom_margin = 0.10 if canvas_aspect >= 1.6 else 0.08
        avail_w = 1.0 - base_left - base_right_margin
        avail_h = 1.0 - top_margin - bottom_margin
        if target_ratio is None or avail_w <= 0 or avail_h <= 0:
            return base_left, 1.0 - base_right_margin, bottom_margin, 1.0 - top_margin

        width_from_full_height = (target_ratio / canvas_aspect) * avail_h
        if width_from_full_height <= avail_w:
            use_w = width_from_full_height
            use_h = avail_h
        else:
            use_w = avail_w
            use_h = (canvas_aspect / target_ratio) * avail_w
        pad_x = (avail_w - use_w) * 0.5
        pad_y = (avail_h - use_h) * 0.5
        left = base_left + pad_x
        bottom = bottom_margin + pad_y
        return left, left + use_w, bottom, bottom + use_h

    def _apply_adaptive_margins(self, n_cols=1):
        preserve_canvas = (
            self._preserved_canvas_layout_is_active()
            and self._preserved_canvas_has_expansion()
        )
        if preserve_canvas:
            try:
                canvas_w, canvas_h = self.canvas.get_width_height(physical=True)
                canvas_aspect = max(1, canvas_w) / max(1, canvas_h)
            except Exception:
                canvas_aspect = self._get_canvas_aspect()
            # The physical figure has already been expanded to the GridSpec's
            # total row/column ratio. Figure-level boxing would squeeze it again.
            target_ratio = None
        else:
            canvas_aspect = self._get_canvas_aspect()
            target_ratio = self._parse_ratio(self.plot_aspect_ratio)
        try:
            # When extra rows such as CIF reference patterns are appended, keep the
            # original plot rows at the selected physical aspect instead of squeezing
            # the main diffraction panel vertically.
            if not preserve_canvas:
                compensation = max(0.05, min(1.0, float(getattr(self, '_grid_target_ratio_compensation', 1.0) or 1.0)))
                if target_ratio is not None:
                    target_ratio *= compensation
                elif compensation < 0.999:
                    target_ratio = canvas_aspect * compensation
        except Exception:
            pass
        # In split mode, non-auto ratio is applied per panel via set_box_aspect.
        # Skip figure-level ratio boxing to avoid conflicts/clipping.
        if self.plot_layout_mode == "split" and target_ratio is not None:
            target_ratio = None
        if preserve_canvas:
            try:
                base_w, base_h = self._preserved_canvas_base_pixels
                canvas_w, canvas_h = self.canvas.get_width_height(physical=True)
                baseline_n_cols = max(1, int(getattr(self, "_preserved_panel_baseline_n_cols", 1) or 1))
                base_left, base_right, base_bottom, base_top = self._fit_canvas_subplot_bounds(
                    base_w,
                    base_h,
                    baseline_n_cols,
                    compensation=getattr(self, "_preserved_panel_baseline_compensation", 1.0),
                )
                left = (base_left * base_w) / max(1, canvas_w)
                right = 1.0 - (((1.0 - base_right) * base_w) / max(1, canvas_w))
                top = 1.0 - (((1.0 - base_top) * base_h) / max(1, canvas_h))
                bottom = (base_bottom * base_h) / max(1, canvas_h)
                self.fig.subplots_adjust(left=left, right=right, top=top, bottom=bottom)
                return
            except Exception:
                pass
        if n_cols > 1:
            base_left, base_right_margin = 0.06, 0.02
        else:
            base_left, base_right_margin = 0.08, 0.05
        top_margin = 0.04 if canvas_aspect >= 1.4 else 0.05
        top_margin = min(0.45, top_margin + self._get_plot_top_space())
        bottom_margin = 0.10 if canvas_aspect >= 1.6 else 0.08

        avail_w = 1.0 - base_left - base_right_margin
        avail_h = 1.0 - top_margin - bottom_margin
        if avail_w <= 0 or avail_h <= 0:
            self.fig.subplots_adjust(left=base_left, right=1.0 - base_right_margin, top=1.0 - top_margin, bottom=bottom_margin)
            return

        if target_ratio is None:
            left = base_left
            right = 1.0 - base_right_margin
            bottom = bottom_margin
            top = 1.0 - top_margin
            self.fig.subplots_adjust(left=left, right=right, top=top, bottom=bottom)
            return

        width_from_full_height = (target_ratio / canvas_aspect) * avail_h
        if width_from_full_height <= avail_w:
            use_w = width_from_full_height
            use_h = avail_h
        else:
            use_w = avail_w
            use_h = (canvas_aspect / target_ratio) * avail_w

        pad_x = (avail_w - use_w) * 0.5
        pad_y = (avail_h - use_h) * 0.5

        left = base_left + pad_x
        right = left + use_w
        bottom = bottom_margin + pad_y
        top = bottom + use_h
        self.fig.subplots_adjust(left=left, right=right, top=top, bottom=bottom)

    def _get_canvas_aspect(self):
        # Use the outer viewport as the zoom-neutral baseline. The inner view
        # becomes narrower when scrollbars appear, so using it here would feed
        # the zoomed canvas size back into the next default-size calculation.
        widget = (
            getattr(self, "plot_page_frame", None)
            or getattr(self, "plot_canvas_view", None)
            or self.canvas.get_tk_widget()
        )
        w = max(widget.winfo_width(), 1)
        h = max(widget.winfo_height(), 1)
        if w <= 1 or h <= 1:
            fw, fh = self.fig.get_size_inches()
            if fh <= 0:
                return 1.0
            return max(fw / fh, 1e-6)
        return w / h

    def _apply_plot_aspect_ratio(self, width=None, height=None):
        # Ctrl+wheel zoom scales the rendered canvas, not the data limits. Keep
        # the factor here so it survives redraws and viewport resizes. Scaling
        # DPI with the pixel dimensions makes this a true view zoom: text and
        # lines grow on screen without changing the figure's export dimensions.
        try:
            canvas_zoom = max(0.25, min(4.0, float(getattr(self, "_plot_canvas_zoom", 1.0))))
        except Exception:
            canvas_zoom = 1.0
        try:
            base_dpi = max(1.0, float(getattr(self, "_plot_canvas_base_dpi", 100.0)))
        except Exception:
            base_dpi = 100.0

        if hasattr(self, "_fixed_plot_box_is_enabled") and self._fixed_plot_box_is_enabled():
            target_dpi = base_dpi * canvas_zoom
            dpi_changed = abs(float(self.fig.get_dpi()) - target_dpi) > 1e-6
            if dpi_changed:
                self.fig.set_dpi(target_dpi)
            if hasattr(self, "_sync_plot_canvas_viewport"):
                self._sync_plot_canvas_viewport()
            return dpi_changed

        widget = (
            getattr(self, "plot_page_frame", None)
            or getattr(self, "plot_canvas_view", None)
            or self.canvas.get_tk_widget()
        )
        w = int(width) if width is not None else max(widget.winfo_width(), 1)
        h = int(height) if height is not None else max(widget.winfo_height(), 1)
        if w <= 1 or h <= 1:
            return False

        # Keep one zoom-neutral canvas size.  Ctrl+wheel may change the
        # Matplotlib widget and make scrollbars appear, but neither of those
        # changes is allowed to become the next Preserve-mode baseline.
        self._plot_canvas_unzoomed_pixels = (max(2, int(w)), max(2, int(h)))

        w = max(2, int(round(w * canvas_zoom)))
        h = max(2, int(round(h * canvas_zoom)))
        max_dimension = 12000.0
        max_area = 48_000_000.0
        downscale = min(
            1.0,
            max_dimension / w,
            max_dimension / h,
            math.sqrt(max_area / max(1.0, float(w * h))),
        )
        if downscale < 1.0:
            w = max(2, int(round(w * downscale)))
            h = max(2, int(round(h * downscale)))
        target_dpi = base_dpi * canvas_zoom * downscale

        # Tk Configure sizes and its backing image use physical pixels. The
        # default logical size divides by the monitor scale and causes repeated
        # shrinking when it is fed back into the embedded canvas geometry.
        cur_w_px, cur_h_px = self.canvas.get_width_height(physical=True)
        dpi_changed = abs(float(self.fig.get_dpi()) - target_dpi) > 1e-6
        if abs(cur_w_px - w) <= 1 and abs(cur_h_px - h) <= 1 and not dpi_changed:
            return False
        if dpi_changed:
            self.fig.set_dpi(target_dpi)

        # Use backend resize path to keep Tk canvas and renderer in exactly the same pixel size.
        if hasattr(self.canvas, "resize"):
            evt = type("ResizeEvent", (), {"width": w, "height": h})()
            self.canvas.resize(evt)
        else:
            dpi = self.fig.get_dpi()
            fig_w_in = w / dpi
            fig_h_in = h / dpi
            self.fig.set_size_inches(fig_w_in, fig_h_in, forward=True)
        return True

    def _fixed_plot_box_is_enabled(self):
        if hasattr(self, "var_fixed_plot_box_enabled"):
            try:
                return bool(self.var_fixed_plot_box_enabled.get())
            except Exception:
                pass
        return bool(getattr(self, "fixed_plot_box_enabled", False))

    def _get_fixed_plot_box_cm(self):
        width = getattr(self, "plot_box_width_cm", 12.0)
        height = getattr(self, "plot_box_height_cm", 8.0)
        if hasattr(self, "var_plot_box_width_cm"):
            try:
                width = self.var_plot_box_width_cm.get()
            except Exception:
                pass
        if hasattr(self, "var_plot_box_height_cm"):
            try:
                height = self.var_plot_box_height_cm.get()
            except Exception:
                pass
        try:
            width = max(0.5, min(100.0, float(width)))
        except Exception:
            width = 12.0
        try:
            height = max(0.5, min(100.0, float(height)))
        except Exception:
            height = 8.0
        return width, height

    def _axes_position_union(self, axes):
        boxes = []
        for ax in axes or []:
            try:
                if ax is not None and ax.get_visible():
                    boxes.append(ax.get_position())
            except Exception:
                pass
        if not boxes:
            return None
        x0 = min(box.x0 for box in boxes)
        y0 = min(box.y0 for box in boxes)
        x1 = max(box.x1 for box in boxes)
        y1 = max(box.y1 for box in boxes)
        if x1 <= x0 or y1 <= y0:
            return None
        return x0, y0, x1 - x0, y1 - y0

    def _apply_fixed_plot_box_size(self):
        if not self._fixed_plot_box_is_enabled():
            return False
        if self.fig is None:
            return False
        axes = getattr(self, "fixed_plot_box_axes", None)
        if not axes:
            axes = getattr(self, "plot_axes", [])
        bbox = self._axes_position_union(axes)
        if bbox is None:
            return False
        _x0, _y0, box_w_frac, box_h_frac = bbox
        if box_w_frac <= 0 or box_h_frac <= 0:
            return False
        width_cm, height_cm = self._get_fixed_plot_box_cm()
        self.plot_box_width_cm = width_cm
        self.plot_box_height_cm = height_cm
        target_w_in = width_cm / 2.54
        target_h_in = height_cm / 2.54
        fig_w = max(0.5, target_w_in / box_w_frac)
        fig_h = max(0.5, target_h_in / box_h_frac)
        try:
            cur_w, cur_h = self.fig.get_size_inches()
            if abs(cur_w - fig_w) < 1e-4 and abs(cur_h - fig_h) < 1e-4:
                return False
            self.fig.set_size_inches(fig_w, fig_h, forward=True)
            return True
        except Exception:
            return False

    def on_plot_ratio_change(self):
        if hasattr(self, "var_plot_aspect_ratio"):
            self.plot_aspect_ratio = self.var_plot_aspect_ratio.get()
        if hasattr(self, "var_custom_plot_aspect_ratio"):
            self.custom_plot_aspect_ratio = self.var_custom_plot_aspect_ratio.get()
        self._request_draw_plot()

    def on_canvas_resize(self, event=None):
        if not getattr(self, "_canvas_ready", False) or self.canvas is None:
            return
        if hasattr(self, "_fixed_plot_box_is_enabled") and self._fixed_plot_box_is_enabled():
            if hasattr(self, "_sync_plot_canvas_viewport"):
                self._sync_plot_canvas_viewport()
            return
        # The outer frame is the stable, zoom-neutral viewport in both modes.
        # Inner Configure events may describe a scrollbar-reduced viewport or
        # a zoomed figure; using those sizes makes Fit mode feed back on itself.
        size_widget = (
            getattr(self, "plot_page_frame", None)
            or getattr(self, "plot_canvas_view", None)
            or self.canvas.get_tk_widget()
        )
        target_w = size_widget.winfo_width()
        target_h = size_widget.winfo_height()
        try:
            target_size = (int(target_w), int(target_h))
        except Exception:
            return
        if target_size[0] <= 1 or target_size[1] <= 1:
            return
        if self._last_resize_size and abs(self._last_resize_size[0] - target_size[0]) <= 1 and abs(self._last_resize_size[1] - target_size[1]) <= 1:
            return
        self._last_resize_size = target_size
        self._resize_pending_size = target_size
        if self._resize_after_id is not None:
            try:
                self.root.after_cancel(self._resize_after_id)
            except Exception:
                pass
        self._resize_after_id = self.root.after(260, self._redraw_after_resize)

    def _redraw_after_resize(self):
        self._resize_after_id = None
        if self._is_redrawing:
            self._resize_after_id = self.root.after(260, self._redraw_after_resize)
            return
        pending = self._resize_pending_size
        self._resize_pending_size = None
        if pending:
            # Read the settled outer geometry instead of an earlier event size.
            self._apply_plot_aspect_ratio()
        if self.is_3d_mode or self.loaded_files:
            self.draw_plot()
        else:
            self.canvas.draw_idle()
        # FigureCanvasTkAgg is embedded through a Canvas create_window item.
        # Resizing the Matplotlib widget alone does not update that item's
        # explicit width/height, leaving the white figure at its old size and
        # exposing the gray viewport after the application is maximized.
        if hasattr(self, "_sync_plot_canvas_viewport"):
            self._sync_plot_canvas_viewport()

    def _get_plot_bg_settings(self):
        enabled = self.var_plot_bg_enabled.get() if hasattr(self, "var_plot_bg_enabled") else self.plot_bg_enabled
        mode = self.var_plot_bg_mode.get() if hasattr(self, "var_plot_bg_mode") else self.plot_bg_mode
        direction = self.var_plot_bg_direction.get() if hasattr(self, "var_plot_bg_direction") else self.plot_bg_direction
        alpha = self.var_plot_bg_alpha.get() if hasattr(self, "var_plot_bg_alpha") else self.plot_bg_alpha
        alpha = max(0.0, min(1.0, float(alpha)))
        return enabled, mode, direction, alpha

    def _apply_plot_background(self, ax):
        enabled, mode, direction, alpha = self._get_plot_bg_settings()
        if not enabled:
            ax.set_facecolor("white")
            return

        if mode == "solid":
            ax.set_facecolor(self.plot_bg_color)
            return

        # Gradient mode
        ax.set_facecolor("none")
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        if (x1 - x0) == 0 or (y1 - y0) == 0:
            ax.set_facecolor(self.plot_bg_grad_start)
            return

        if direction == "horizontal":
            grad = np.tile(np.linspace(0, 1, 256), (2, 1))
        else:
            grad = np.tile(np.linspace(0, 1, 256)[:, None], (1, 2))
        cmap = LinearSegmentedColormap.from_list("xrd_plot_bg", [self.plot_bg_grad_start, self.plot_bg_grad_end])
        ax.imshow(
            grad,
            cmap=cmap,
            origin='lower',
            aspect='auto',
            extent=[x0, x1, y0, y1],
            interpolation='bicubic',
            alpha=alpha,
            zorder=-100
        )

    def _reserve_top_headroom(self, ax, has_top_title=False):
        if not has_top_title:
            return
        y_min, y_max = ax.get_ylim()
        span = y_max - y_min
        if span <= 0:
            return
        # Reserve only modest headroom for in-plot titles. The previous rule
        # expanded Y range too aggressively for large title sizes and pushed
        # XRD patterns far down in the axis.
        title_size = self._get_title_font_size() if hasattr(self, "_get_title_font_size") else 12
        extra_frac = 0.035 + max(0, title_size - 12) * 0.0015
        extra_frac = max(0.035, min(0.12, extra_frac))
        ax.set_ylim(y_min, y_max + span * extra_frac)

    def _apply_2d_tick_style(self, ax, tick_dir, show_x_ticks, show_y_ticks, show_x_labels=None, show_y_labels=None):
        self.paper_style.apply_2d_tick_style(
            ax,
            tick_dir,
            show_x_ticks,
            show_y_ticks,
            show_x_labels=show_x_labels,
            show_y_labels=show_y_labels,
        )

    def reset_plot_title_position(self):
        self.plot_title_pos = [0.02, 0.98]
        self.draw_plot()

    def _apply_plot_title(self, ax):
        self.paper_style.apply_plot_title(ax)

    def _plot_memo_text_from_editor(self):
        if not hasattr(self, "txt_plot_memo"):
            return ""
        try:
            return self.txt_plot_memo.get("1.0", "end-1c").strip()
        except Exception:
            return ""

    def _get_selected_plot_memo_index(self):
        if not hasattr(self, "lb_plot_memos"):
            return None
        try:
            selection = self.lb_plot_memos.curselection()
            if not selection:
                return None
            idx = int(selection[0])
            if 0 <= idx < len(self.plot_memos):
                return idx
        except Exception:
            return None
        return None

    def _memo_color_contrast(self, color):
        try:
            color = str(color).strip()
            if color.startswith("#") and len(color) == 7:
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                return "black" if (0.299 * r + 0.587 * g + 0.114 * b) > 160 else "white"
        except Exception:
            pass
        return "white"

    def _set_plot_memo_color_label(self):
        if not hasattr(self, "lbl_plot_memo_color"):
            return
        color = getattr(self, "plot_memo_default_color", "#111827")
        try:
            self.lbl_plot_memo_color.config(text=color, bg=color, fg=self._memo_color_contrast(color))
        except Exception:
            pass

    def _refresh_plot_memo_list(self):
        if not hasattr(self, "lb_plot_memos"):
            return
        try:
            current = self._get_selected_plot_memo_index()
            self.lb_plot_memos.delete(0, tk.END)
            for idx, memo in enumerate(getattr(self, "plot_memos", []), start=1):
                text = str(memo.get("text", "")).replace("\n", " ").strip()
                if len(text) > 42:
                    text = text[:39] + "..."
                self.lb_plot_memos.insert(tk.END, f"{idx}. {text or '(empty memo)'}")
            if current is not None and current < len(self.plot_memos):
                self.lb_plot_memos.selection_set(current)
        except Exception:
            pass
        self._set_plot_memo_color_label()

    def _on_plot_memo_select(self, event=None):
        idx = self._get_selected_plot_memo_index()
        if idx is None:
            return
        memo = self.plot_memos[idx]
        if hasattr(self, "txt_plot_memo"):
            try:
                self.txt_plot_memo.delete("1.0", tk.END)
                self.txt_plot_memo.insert("1.0", str(memo.get("text", "")))
            except Exception:
                pass
        if hasattr(self, "var_plot_memo_font"):
            self.var_plot_memo_font.set(str(memo.get("font", self.plot_memo_default_font)))
        if hasattr(self, "var_plot_memo_size"):
            try:
                self.var_plot_memo_size.set(int(memo.get("size", self.plot_memo_default_size)))
            except Exception:
                pass
        if hasattr(self, "var_plot_memo_bold"):
            self.var_plot_memo_bold.set(bool(memo.get("bold", self.plot_memo_default_bold)))
        self.plot_memo_default_color = str(memo.get("color", self.plot_memo_default_color))
        self._set_plot_memo_color_label()

    def _current_plot_memo_font(self):
        if hasattr(self, "var_plot_memo_font"):
            try:
                return str(self.var_plot_memo_font.get() or "Use Plot Font")
            except Exception:
                pass
        return getattr(self, "plot_memo_default_font", "Use Plot Font")

    def _current_plot_memo_size(self):
        if hasattr(self, "var_plot_memo_size"):
            try:
                return max(6, min(96, int(float(self.var_plot_memo_size.get()))))
            except Exception:
                pass
        return max(6, min(96, int(getattr(self, "plot_memo_default_size", 11))))

    def _current_plot_memo_bold(self):
        if hasattr(self, "var_plot_memo_bold"):
            try:
                return bool(self.var_plot_memo_bold.get())
            except Exception:
                pass
        return bool(getattr(self, "plot_memo_default_bold", False))

    def _make_plot_memo(self, text, x=None, y=None):
        n = len(getattr(self, "plot_memos", []))
        if x is None:
            x = 0.035
        if y is None:
            y = max(0.06, 0.965 - n * 0.055)
        return {
            "text": str(text),
            "x": float(max(0.0, min(1.0, x))),
            "y": float(max(0.0, min(1.0, y))),
            "font": self._current_plot_memo_font(),
            "size": self._current_plot_memo_size(),
            "bold": self._current_plot_memo_bold(),
            "color": str(getattr(self, "plot_memo_default_color", "#111827")),
        }

    def _choose_plot_memo_color(self):
        base = getattr(self, "plot_memo_default_color", "#111827")
        c = choose_color(self.root, title="Plot Memo Color", initial_color=base)
        if not c:
            return
        self.plot_memo_default_color = c
        self._set_plot_memo_color_label()
        idx = self._get_selected_plot_memo_index()
        if idx is not None:
            self.plot_memos[idx]["color"] = c
        self._request_draw_plot()

    def _add_plot_memo_from_editor(self):
        text = self._plot_memo_text_from_editor()
        if not text:
            messagebox.showinfo("Plot Memo", "Memo text is empty.")
            return
        self.plot_memos.append(self._make_plot_memo(text))
        self.plot_memos_enabled = True
        if hasattr(self, "var_plot_memos_enabled"):
            self.var_plot_memos_enabled.set(True)
        self._refresh_plot_memo_list()
        if hasattr(self, "lb_plot_memos"):
            try:
                self.lb_plot_memos.selection_clear(0, tk.END)
                self.lb_plot_memos.selection_set(len(self.plot_memos) - 1)
            except Exception:
                pass
        self._request_draw_plot()

    def _update_selected_plot_memo(self):
        idx = self._get_selected_plot_memo_index()
        if idx is None:
            messagebox.showinfo("Plot Memo", "Select a memo to update.")
            return
        text = self._plot_memo_text_from_editor()
        if not text:
            messagebox.showinfo("Plot Memo", "Memo text is empty.")
            return
        memo = self.plot_memos[idx]
        memo.update({
            "text": text,
            "font": self._current_plot_memo_font(),
            "size": self._current_plot_memo_size(),
            "bold": self._current_plot_memo_bold(),
            "color": str(getattr(self, "plot_memo_default_color", memo.get("color", "#111827"))),
        })
        self._refresh_plot_memo_list()
        self._request_draw_plot()

    def _delete_selected_plot_memo(self):
        idx = self._get_selected_plot_memo_index()
        if idx is None:
            return
        try:
            del self.plot_memos[idx]
        except Exception:
            return
        self._refresh_plot_memo_list()
        self._request_draw_plot()

    def _clear_plot_memos(self):
        self.plot_memos = []
        self._refresh_plot_memo_list()
        self._request_draw_plot()

    def _plot_memo_font_prop(self, memo):
        size = self._scale_font_size(float(memo.get("size", 11)), min_size=6, max_size=96)
        bold = bool(memo.get("bold", False))
        font_name = str(memo.get("font", "Use Plot Font") or "Use Plot Font")
        if font_name == "Use Plot Font":
            return self._font_prop(size=size, bold=bold)
        try:
            spec = get_font_spec(font_name)
            family = spec.get("family", font_name)
            path = spec.get("path")
            kwargs = {"family": family, "size": size, "weight": "bold" if bold else spec.get("base_weight", self.plot_base_weight)}
            if path and os.path.exists(path) and not bold:
                kwargs["fname"] = path
            return FontProperties(**kwargs)
        except Exception:
            return self._font_prop(size=size, bold=bold)

    def _draw_plot_memos(self):
        self.plot_memo_artists = []
        if not bool(getattr(self, "plot_memos_enabled", False)):
            return
        for idx, memo in enumerate(getattr(self, "plot_memos", [])):
            text = str(memo.get("text", "")).strip()
            if not text:
                continue
            try:
                x = max(0.0, min(1.0, float(memo.get("x", 0.035))))
                y = max(0.0, min(1.0, float(memo.get("y", 0.965))))
            except Exception:
                x, y = 0.035, 0.965
            artist = self.fig.text(
                x,
                y,
                text,
                ha="left",
                va="top",
                color=str(memo.get("color", "#111827")),
                fontproperties=self._plot_memo_font_prop(memo),
                zorder=2000,
                clip_on=False,
                picker=True,
            )
            artist._labx_memo_index = idx
            try:
                self.art_engine.apply_text_art(artist)
            except Exception:
                pass
            self.plot_memo_artists.append(artist)

    def _estimate_horizontal_legend_ncol(self, ax_main, labels, legend_size, max_width_ratio):
        if not labels:
            return 1
        max_width_ratio = max(0.40, min(1.00, float(max_width_ratio)))
        try:
            canvas_w = max(self.canvas.get_width_height(physical=True)[0], 1)
            ax_frac_w = float(ax_main.get_position().width)
            avail_px = max(80.0, canvas_w * ax_frac_w * max_width_ratio)

            char_px = max(5.0, legend_size * 0.62)
            marker_pad = max(14.0, legend_size * 1.6)
            col_pad = max(10.0, legend_size * 0.8)
            widths = [len(str(lbl)) * char_px + marker_pad + col_pad for lbl in labels]

            if not widths:
                return 1

            avg_item = float(np.mean(widths))
            longest_item = float(np.max(widths))
            if longest_item >= avail_px:
                return 1

            ncol = int(avail_px // max(avg_item, 1.0))
            ncol = max(1, min(len(labels), ncol))
            return ncol
        except Exception:
            count = len(labels)
            if count <= 4:
                return count
            if count <= 8:
                return max(2, int(math.ceil(count / 2)))
            return max(2, int(math.ceil(count / 3)))

    def _draw_legend(self, ax_main, legend_handles):
        self.paper_style.draw_legend(ax_main, legend_handles)

    def _get_sample_display_name(self, loader):
        name = str(loader.display_names.get("Observed", "") or "").strip()
        return name if name else loader.filename

    def _get_split_panel_title(self, loader):
        if self.split_panel_title_source == "filename":
            return loader.filename
        return self._get_sample_display_name(loader)

    def _get_split_main_title(self, loader):
        custom = self.split_main_title_overrides.get(loader.filepath, "").strip()
        if custom:
            return custom
        return self._get_split_panel_title(loader)

    def _get_split_diff_title(self, loader):
        custom = self.split_diff_title_overrides.get(loader.filepath, "").strip()
        if custom:
            return custom
        return "Difference"

    def _get_split_main_title_size(self, loader):
        custom = self.split_main_title_size_overrides.get(loader.filepath)
        if isinstance(custom, int) and custom > 0:
            base_size = custom
        else:
            if hasattr(self, "var_split_panel_title_size"):
                base_size = int(self.var_split_panel_title_size.get())
            else:
                base_size = int(self.split_panel_title_size)
        return self._scale_font_size(base_size, min_size=6, max_size=72)

    def _get_split_diff_title_size(self, loader):
        custom = self.split_diff_title_size_overrides.get(loader.filepath)
        if isinstance(custom, int) and custom > 0:
            base_size = custom
        else:
            base_size = int(self.var_resid_size.get())
        return self._scale_font_size(base_size, min_size=6, max_size=30)

    def open_split_title_editor(self):
        rows = []
        ordered_ids = self.file_tree.get_children()
        for iid in ordered_ids:
            if iid in self.loaded_files:
                loader = self.loaded_files[iid]
                rows.append((iid, self._get_sample_display_name(loader)))
        if not rows:
            messagebox.showwarning("Warning", "No loaded files to edit.")
            return
        SplitTitlesDialog(
            self.root,
            rows,
            self.split_main_title_overrides,
            self.split_diff_title_overrides,
            self.split_main_title_size_overrides,
            self.split_diff_title_size_overrides,
            self.var_split_panel_title_size.get() if hasattr(self, "var_split_panel_title_size") else self.split_panel_title_size,
            self.var_resid_size.get(),
            self._apply_split_title_overrides
        )

    def _apply_split_title_overrides(self, main_map, diff_map, main_size_map, diff_size_map):
        self.split_main_title_overrides = main_map
        self.split_diff_title_overrides = diff_map
        self.split_main_title_size_overrides = main_size_map
        self.split_diff_title_size_overrides = diff_size_map
        self.draw_plot()

