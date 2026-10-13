# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *

from pathlib import Path

from xrd_rietveld_manager.chemical_formula import parse_formula_element_counts


class PlotterMixin:
    @staticmethod
    def _phase_reference_match_key(value):
        """Return a compact key for matching phase and reference formulas."""
        return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())

    @staticmethod
    def _phase_reference_composition_key(value):
        """Return a reduced composition key so equivalent formulas match."""
        counts = parse_formula_element_counts(str(value or ""))
        if not counts:
            return ""
        divisor = 0
        for count in counts.values():
            divisor = math.gcd(divisor, int(count))
        divisor = max(1, divisor)
        return "|".join(
            f"{element.casefold()}:{int(count) // divisor}"
            for element, count in sorted(counts.items())
        )

    def _phase_reference_keys(self, value):
        return {
            key
            for key in (
                self._phase_reference_match_key(value),
                self._phase_reference_composition_key(value),
            )
            if key
        }

    def _reference_for_phase(self, phase_name, loaders):
        """Find the visible reference pattern that represents ``phase_name``."""
        phase_keys = self._phase_reference_keys(phase_name)
        phase_keys.update(
            self._phase_reference_keys(
                getattr(self, "phase_name_overrides", {}).get(phase_name, phase_name)
            )
        )
        for loader in loaders:
            if phase_name in getattr(loader, "phase_names", []):
                phase_keys.update(
                    self._phase_reference_keys(
                        getattr(loader, "display_names", {}).get(phase_name, phase_name)
                    )
                )
        phase_keys.discard("")

        for ref in getattr(self, "reference_peaks", []):
            if not ref.get("visible", True) or not ref.get("peaks"):
                continue
            structure = ref.get("structure", {})
            if not isinstance(structure, dict):
                structure = {}
            ref_keys = self._phase_reference_keys(ref.get("label", ""))
            ref_keys.update(self._phase_reference_keys(structure.get("formula", "")))
            path = ref.get("path", "")
            if path:
                ref_keys.update(self._phase_reference_keys(Path(path).stem))
            ref_keys.discard("")
            if phase_keys.intersection(ref_keys):
                return ref
        return None

    @staticmethod
    def _main_reference_peak_positions(reference, x_min, x_max, threshold_fraction=0.05):
        """Return in-range positions of the reference's main intensity peaks."""
        peaks = reference.get("peaks", []) if reference else []
        if not peaks:
            return []
        max_intensity = max(max(float(peak[1]), 0.0) for peak in peaks)
        if max_intensity <= 0.0:
            return []
        threshold = max_intensity * float(threshold_fraction)
        return [
            float(peak[0])
            for peak in peaks
            if x_min <= float(peak[0]) <= x_max and float(peak[1]) >= threshold
        ]

    def _axis_label_color(self):
        if hasattr(self, "var_axis_label_color"):
            try:
                return self.var_axis_label_color.get() or self.axis_label_color
            except Exception:
                pass
        return getattr(self, "axis_label_color", "#000000")

    def _show_axis_title(self, axis):
        attr = "var_axis_title_x_2d" if axis == "x" else "var_axis_title_y_2d"
        fallback_attr = "show_axis_title_x_2d" if axis == "x" else "show_axis_title_y_2d"
        if hasattr(self, attr):
            try:
                return bool(getattr(self, attr).get())
            except Exception:
                pass
        return bool(getattr(self, fallback_attr, True))

    def _set_x_axis_title(self, ax, text=None, labelpad=None):
        title = text if text is not None else r"$2\theta\ (^\circ)$"
        if not self._show_axis_title("x"):
            title = ""
        kwargs = {
            "fontsize": self._get_axis_label_size(),
            "fontname": self.plot_font_family,
            "fontweight": self._get_axis_label_weight(),
        }
        if labelpad is not None:
            kwargs["labelpad"] = labelpad
        ax.set_xlabel(title, **kwargs)
        try:
            ax.xaxis.label.set_color(self._axis_label_color())
        except Exception:
            pass

    def _set_y_axis_title(self, ax, text="Intensity (a.u.)", labelpad=None):
        title = text if self._show_axis_title("y") else ""
        kwargs = {
            "fontsize": self._get_axis_label_size(),
            "fontname": self.plot_font_family,
            "fontweight": self._get_axis_label_weight(),
        }
        if labelpad is not None:
            kwargs["labelpad"] = labelpad
        ax.set_ylabel(title, **kwargs)
        try:
            ax.yaxis.label.set_color(self._axis_label_color())
        except Exception:
            pass

    def _loader_x(self, loader):
        arr = getattr(loader, "x_np", None)
        if arr is not None and getattr(arr, "size", 0):
            return arr
        return np.asarray(loader.x, dtype=float)

    def _loader_y(self, loader, key, fallback=None):
        if hasattr(loader, "array_for"):
            return loader.array_for(key, fallback)
        if fallback is None:
            return np.array([], dtype=float)
        return np.asarray(fallback, dtype=float)

    def _loader_has_data(self, loader):
        arr = getattr(loader, "x_np", None)
        return bool(getattr(arr, "size", 0)) if arr is not None else bool(loader.x)

    def _curve_y_base(self, loader, key, y_raw):
        y = self._loader_y(loader, key, y_raw) * self.intensity_scale
        if not y.size:
            return y
        back_vals = self._loader_y(loader, "Background", loader.back)
        if self.bg_sub_enabled and back_vals.size and key in ["Observed", "Calculated"]:
            y = y - (back_vals * self.intensity_scale)
        return y

    def _x_range_mask(self, x_vals):
        if not self.custom_xlim:
            return None
        try:
            x0, x1 = sorted((float(self.custom_xlim[0]), float(self.custom_xlim[1])))
            xs = np.asarray(x_vals, dtype=float)
            return np.isfinite(xs) & (xs >= x0) & (xs <= x1)
        except Exception:
            return None

    def _range_norm_factor_for_loader(self, loader):
        if not getattr(self, "normalize_y_in_x_range", False) or not self.custom_xlim:
            return 1.0
        x_vals = self._loader_x(loader)
        mask = self._x_range_mask(x_vals)
        if mask is None or not np.any(mask):
            return 1.0

        chunks = []
        primary_keys = ["Observed", "Calculated"]
        for key in primary_keys:
            if not loader.visibility.get(key, True):
                continue
            if key == "Calculated":
                raw = loader.calc
            else:
                raw = loader.obs
            y = self._curve_y_base(loader, key, raw)
            if y.size == mask.size and np.any(np.isfinite(y[mask])):
                chunks.append(y[mask])

        if not chunks:
            for phase in getattr(loader, "phase_names", []):
                if not loader.visibility.get(phase, True):
                    continue
                y = self._curve_y_base(loader, phase, loader.phases.get(phase, []))
                if y.size == mask.size and np.any(np.isfinite(y[mask])):
                    chunks.append(y[mask])

        if not chunks:
            return 1.0
        y_all = np.concatenate(chunks)
        y_all = y_all[np.isfinite(y_all)]
        if y_all.size == 0:
            return 1.0
        ymax = float(np.max(y_all))
        ymin = float(np.min(y_all))
        # XRD data is normally non-negative. Use positive peak height first;
        # fall back to span when baseline-subtracted data crosses zero.
        scale_ref = ymax if ymax > 0 else (ymax - ymin)
        if not np.isfinite(scale_ref) or abs(scale_ref) < 1e-12:
            return 1.0
        return 1.0 / scale_ref

    def _split_panel_stack_layout(self, loader, range_norm):
        """Build a per-file phase stack while preserving that file's Y units."""
        if getattr(self, "plot_layout_mode", "combined") != "split":
            return None

        auto_stack_active = bool(getattr(loader, "phase_auto_stack_order", []) or [])
        stack_order = self._get_loader_phase_order(loader, visible_only=True) if auto_stack_active else []
        if not stack_order:
            return None

        x_vals = self._loader_x(loader)
        x_mask = self._x_range_mask(x_vals)
        core_chunks = []
        for key, raw in (("Observed", loader.obs), ("Calculated", loader.calc)):
            if not loader.visibility.get(key, True):
                continue
            values = self._curve_y_base(loader, key, raw) * range_norm
            if values.size != x_vals.size:
                continue
            finite = np.isfinite(values)
            if x_mask is not None:
                finite &= x_mask
            if np.any(finite):
                core_chunks.append(values[finite])

        if not core_chunks:
            return None
        core_values = np.concatenate(core_chunks)
        core_values = core_values[np.isfinite(core_values)]
        if core_values.size == 0:
            return None

        # A low percentile is a more stable diffraction baseline than a single
        # noisy minimum. Each panel keeps its own absolute intensity values.
        baseline = float(np.percentile(core_values, 5.0))
        peak = float(np.max(core_values))
        core_span = peak - baseline
        if not np.isfinite(core_span) or core_span <= 1e-12:
            core_span = max(abs(peak), 1.0)

        phase_step = core_span * 0.22
        automatic_offsets = getattr(loader, "phase_auto_stack_offsets", {})
        if not isinstance(automatic_offsets, dict):
            automatic_offsets = {}

        def manual_delta(key):
            current = float(loader.offsets.get(key, 0.0))
            automatic = float(automatic_offsets.get(key, current))
            return current - automatic

        offsets = {
            "Observed": manual_delta("Observed"),
            "Calculated": manual_delta("Calculated"),
            "Background": manual_delta("Background"),
        }
        for index, phase in enumerate(stack_order):
            offsets[phase] = baseline - (index + 1) * phase_step + manual_delta(phase)

        # Identical ratios make the baseline and phase rows line up in screen
        # space, while baseline/peak remain different data values per DIA.
        core_deltas = [
            offsets[key]
            for key in ("Observed", "Calculated")
            if loader.visibility.get(key, True)
        ] or [0.0]
        lower = min(
            baseline + min(core_deltas),
            min(offsets[phase] for phase in stack_order) - 0.25 * phase_step,
        )
        upper = peak + max(core_deltas)

        # Keep manually shifted phase traces inside the Split panel range.
        for phase in stack_order:
            raw = loader.phases.get(phase, [])
            values = self._curve_y_base(loader, phase, raw) * range_norm
            if values.size != x_vals.size:
                continue
            finite = np.isfinite(values)
            if x_mask is not None:
                finite &= x_mask
            if np.any(finite):
                visible_values = values[finite] + offsets[phase]
                lower = min(lower, float(np.min(visible_values)) - 0.10 * phase_step)
                upper = max(upper, float(np.max(visible_values)) + 0.10 * phase_step)
        return {
            "offsets": offsets,
            "y_bounds": (lower, upper),
            "baseline": baseline,
            "phase_step": phase_step,
        }

    def _apply_split_panel_y_range(self, ax, layout):
        if not layout or getattr(self, "custom_ylim", None):
            self._apply_main_y_range(ax)
            return
        if not getattr(self, "y_autoscale_to_x_range", True):
            return
        try:
            y_min, y_max = layout["y_bounds"]
            span = float(y_max) - float(y_min)
            if not np.isfinite(span) or span <= 0:
                self._apply_main_y_range(ax)
                return
            padding = float(getattr(self, "y_autoscale_padding_percent", 8.0))
            pad = span * max(0.0, padding) / 100.0
            ax.set_ylim(float(y_min) - pad, float(y_max) + pad)
        except Exception:
            self._apply_main_y_range(ax)

    def _apply_main_y_range(self, ax):
        custom_ylim = getattr(self, "custom_ylim", None)
        if not custom_ylim:
            if getattr(self, "y_autoscale_to_x_range", True):
                self._autoscale_main_y_to_current_x(ax)
            return
        try:
            y0, y1 = float(custom_ylim[0]), float(custom_ylim[1])
            if y0 != y1:
                ax.set_ylim(y0, y1)
        except Exception:
            pass

    def _autoscale_main_y_to_current_x(self, ax):
        try:
            x0, x1 = ax.get_xlim()
            lo_x, hi_x = sorted((float(x0), float(x1)))
        except Exception:
            return

        y_chunks = []
        for line in list(getattr(ax, "lines", [])):
            try:
                x_data = np.asarray(line.get_xdata(), dtype=float)
                y_data = np.asarray(line.get_ydata(), dtype=float)
                if x_data.size == 0 or y_data.size == 0 or x_data.size != y_data.size:
                    continue
                mask = np.isfinite(x_data) & np.isfinite(y_data) & (x_data >= lo_x) & (x_data <= hi_x)
                if np.any(mask):
                    y_chunks.append(y_data[mask])
            except Exception:
                continue

        for collection in list(getattr(ax, "collections", [])):
            try:
                offsets = collection.get_offsets()
                if offsets is None or len(offsets) == 0:
                    continue
                offsets = np.asarray(offsets, dtype=float)
                if offsets.ndim != 2 or offsets.shape[1] < 2:
                    continue
                x_data = offsets[:, 0]
                y_data = offsets[:, 1]
                mask = np.isfinite(x_data) & np.isfinite(y_data) & (x_data >= lo_x) & (x_data <= hi_x)
                if np.any(mask):
                    y_chunks.append(y_data[mask])
            except Exception:
                continue

        if not y_chunks:
            return

        y_all = np.concatenate(y_chunks)
        if y_all.size == 0:
            return
        y_min = float(np.nanmin(y_all))
        y_max = float(np.nanmax(y_all))
        if not np.isfinite(y_min) or not np.isfinite(y_max):
            return

        span = y_max - y_min
        if span <= 0:
            span = max(abs(y_max), 1.0) * 0.1
            y_min -= span
            y_max += span
        pad_percent = getattr(self, "y_autoscale_padding_percent", 8.0)
        try:
            pad_percent = float(pad_percent)
        except Exception:
            pad_percent = 8.0
        pad = span * max(0.0, pad_percent) / 100.0
        ax.set_ylim(y_min - pad, y_max + pad)

    def _sample_labels_enabled(self):
        if not getattr(self, "show_sample_labels", True):
            return False
        if getattr(self, "plot_layout_mode", "combined") != "combined":
            return False
        return True

    def _main_phase_labels_enabled(self):
        # If the user explicitly enables phase labels, draw them wherever phase
        # traces are visible. File-count based gating made the control appear
        # broken when multiple files were loaded but only one was inspected.
        return bool(getattr(self, "show_phase_display_labels", False))

    def _label_position(self, value):
        value = str(value or "right").strip().lower()
        aliases = {
            "right end": "right",
            "right-end": "right",
            "left rail": "left",
            "inside-left": "left",
            "outside-left": "left",
            "peak": "right",
        }
        return aliases.get(value, value if value in {"right", "left", "below", "above"} else "right")

    def _draw_row_attached_label(
        self, ax, label, x_vals, y_vals, row_y, color, position, size, bold,
        vertical_shift=0.0,
    ):
        if x_vals is None or y_vals is None or len(x_vals) == 0 or len(y_vals) == 0:
            return
        xs = np.asarray(x_vals, dtype=float)
        ys = np.asarray(y_vals, dtype=float)
        finite = np.isfinite(xs) & np.isfinite(ys)
        if not np.any(finite):
            return
        xs = xs[finite]
        ys = ys[finite]

        x_min, x_max = getattr(self, "_current_sample_label_xlim", ax.get_xlim())
        span = max(float(x_max) - float(x_min), 1e-12)
        y0, y1 = ax.get_ylim()
        y_span = max(abs(float(y1) - float(y0)), 1e-12)
        user_shift = float(vertical_shift)
        line_gap = y_span * 0.018
        position = self._label_position(position)

        if position == "left":
            x_text = float(x_min) + span * 0.012
            idx = int(np.argmin(np.abs(xs - x_text)))
            y_text = ys[idx] + user_shift
            ha = "left"
            va = "center"
            clip = False
        elif position == "below":
            x_text = float(x_max) - span * 0.012
            idx = int(np.argmin(np.abs(xs - x_text)))
            y_text = ys[idx] - line_gap + user_shift
            ha = "right"
            va = "top"
            clip = False
        elif position == "above":
            x_text = float(x_max) - span * 0.012
            idx = int(np.argmin(np.abs(xs - x_text)))
            y_text = ys[idx] + line_gap + user_shift
            ha = "right"
            va = "bottom"
            clip = False
        else:
            x_text = float(x_min) + span * 0.985
            idx = int(np.argmin(np.abs(xs - x_text)))
            y_text = ys[idx] + user_shift
            ha = "right"
            va = "center"
            clip = False

        txt = ax.text(
            x_text,
            y_text,
            self._format_tex(self._truncate_label(label, max_chars=38)),
            color=color,
            fontproperties=self._font_prop(size=self._scale_font_size(size, min_size=6, max_size=30), bold=bold),
            ha=ha,
            va=va,
            clip_on=clip,
            zorder=20,
        )
        txt._labx_no_text_art = True
        txt.set_in_layout(False)
        txt.set_bbox(None)
        txt.set_path_effects([])
        return txt

    def _draw_sample_label(self, ax, loader, x_vals, y_vals, color, row_y=0.0):
        color = self._element_color("sample_label", color)
        if not self._sample_labels_enabled():
            return
        raw_label = self._get_sample_display_name(loader)
        return self._draw_row_attached_label(
            ax,
            raw_label,
            x_vals,
            y_vals,
            row_y,
            color,
            getattr(self, "sample_label_position", "right"),
            getattr(self, "sample_label_size", 10),
            getattr(self, "sample_label_bold", True),
            getattr(self, "sample_label_vertical_shift", 0.0),
        )

    def _get_ordered_visible_phases(self, loaders):
        return self._get_global_phase_order(loaders, visible_only=True)

    def _phase_display_label(self, phase_name, loaders):
        for loader in loaders:
            if phase_name in getattr(loader, "phase_names", []):
                return loader.display_names.get(phase_name, self.phase_name_overrides.get(phase_name, phase_name))
        return self.phase_name_overrides.get(phase_name, phase_name)

    def _draw_phase_stack_label(self, ax, idx, phase_name, color, loaders, x_min, x_max):
        color = self._element_color("phase_label", color)
        if not getattr(self, "show_phase_display_labels", True):
            return
        span = max(float(x_max) - float(x_min), 1e-12)
        position = self._label_position(getattr(self, "phase_display_label_position", "right"))
        user_shift = float(getattr(self, "phase_label_vertical_shift", 0.0))
        y_center = idx + 0.5 + user_shift
        label = format_chemical_formula_mathtext(
            self._phase_display_label(phase_name, loaders)
        )
        label = self._format_tex(label)
        size = self._scale_font_size(getattr(self, "phase_display_label_size", 10), min_size=6, max_size=30)
        weight = "bold" if getattr(self, "phase_display_label_bold", True) else "normal"

        kwargs = dict(
            color=color,
            fontproperties=self._font_prop(size=size, weight=weight, bold=getattr(self, "phase_display_label_bold", True)),
            zorder=20,
        )
        if position == "left":
            x_text = float(x_min) + span * 0.012
            txt = ax.text(x_text, y_center, label, ha="left", va="center", clip_on=False, **kwargs)
        elif position == "below":
            x_text = float(x_max) - span * 0.012
            y_text = idx + 0.08 + user_shift
            txt = ax.text(x_text, y_text, label, ha="right", va="bottom", clip_on=False, **kwargs)
        elif position == "above":
            x_text = float(x_max) - span * 0.012
            y_text = idx + 0.92 + user_shift
            txt = ax.text(x_text, y_text, label, ha="right", va="top", clip_on=False, **kwargs)
        else:
            x_text = float(x_max) - span * 0.012
            txt = ax.text(x_text, y_center, label, ha="right", va="center", clip_on=False, **kwargs)
        txt._labx_no_text_art = True
        # Labels outside an axes must not enlarge the figure's layout/bounding box.
        # Otherwise an extreme shift can make the actual plot look compressed or absent.
        txt.set_in_layout(False)
        txt.set_bbox(None)
        txt.set_path_effects([])

    def _draw_phase_trace_label(self, ax, loader, phase_name, x_vals, y_vals, color):
        color = self._element_color("phase_label", color)
        if not self._main_phase_labels_enabled():
            return
        if x_vals is None or y_vals is None or len(x_vals) == 0 or len(y_vals) == 0:
            return

        xs = np.asarray(x_vals, dtype=float)
        ys = np.asarray(y_vals, dtype=float)
        finite = np.isfinite(xs) & np.isfinite(ys)
        if not np.any(finite):
            return
        xs = xs[finite]
        ys = ys[finite]

        label = format_chemical_formula_mathtext(
            loader.display_names.get(
                phase_name,
                self.phase_name_overrides.get(phase_name, phase_name),
            )
        )
        label = self._format_tex(label)
        return self._draw_row_attached_label(
            ax,
            label,
            xs,
            ys,
            getattr(self, "_current_phase_label_row_y", 0.0),
            color,
            getattr(self, "phase_display_label_position", "right"),
            getattr(self, "phase_display_label_size", 10),
            getattr(self, "phase_display_label_bold", True),
            getattr(self, "phase_label_vertical_shift", 0.0),
        )

    def _register_layer_offset_artist(self, loader, key, kind, artist):
        registry = getattr(self, "_layer_offset_artists", None)
        if registry is None or artist is None:
            return
        entry = {
            "kind": kind,
            "artist": artist,
            "manual_offset": float(loader.offsets.get(key, 0.0)),
        }
        if kind == "line":
            entry["base"] = np.asarray(artist.get_ydata(), dtype=float).copy()
        elif kind == "scatter":
            entry["base"] = np.asarray(artist.get_offsets(), dtype=float).copy()
        elif kind == "fill":
            entry["base"] = [path.vertices.copy() for path in artist.get_paths()]
        elif kind == "text":
            entry["base"] = tuple(artist.get_position())
        else:
            return
        registry.setdefault((id(loader), key), []).append(entry)

    def _preview_layer_offset(self, loader, key, value):
        """Move existing artists without rebuilding the complete Matplotlib figure."""
        entries = getattr(self, "_layer_offset_artists", {}).get((id(loader), key), [])
        if not entries or self.canvas is None:
            return False
        new_offset = float(value)
        updated = False
        for entry in entries:
            try:
                delta = new_offset - entry["manual_offset"]
                artist = entry["artist"]
                kind = entry["kind"]
                if kind == "line":
                    artist.set_ydata(entry["base"] + delta)
                elif kind == "scatter":
                    offsets = entry["base"].copy()
                    if offsets.ndim != 2 or offsets.shape[1] < 2:
                        continue
                    offsets[:, 1] += delta
                    artist.set_offsets(offsets)
                elif kind == "fill":
                    for path, base_vertices in zip(artist.get_paths(), entry["base"]):
                        path.vertices[:, :] = base_vertices
                        path.vertices[:, 1] += delta
                    artist.stale = True
                elif kind == "text":
                    x_pos, y_pos = entry["base"]
                    artist.set_position((x_pos, y_pos + delta))
                updated = True
            except Exception:
                continue
        if updated:
            self.canvas.draw_idle()
        return updated

    def _plot_loader_curves(self, ax_main, loader, legend_handles, draw_labels=True):
        range_norm = self._range_norm_factor_for_loader(loader)
        split_layout = self._split_panel_stack_layout(loader, range_norm)
        layer_order = self._get_loader_layer_order(loader)
        layer_count = max(1, len(layer_order))

        def plot_curve(key, y_raw, label_default, fill=False, order_index=0):
            if not loader.visibility.get(key, True):
                return
            if key == "Background" and self.bg_sub_enabled:
                return

            x_vals = self._loader_x(loader)
            y = self._curve_y_base(loader, key, y_raw) * range_norm
            if y.size != x_vals.size or not y.size:
                return

            if split_layout and key in split_layout["offsets"]:
                offset = split_layout["offsets"][key]
            else:
                offset = loader.offsets.get(key, 0.0)
            y_final = y + offset

            st = loader.styles.get(key, {})
            c = st.get("color", "black")
            if self.plot_layout_mode == "split" and key == "Observed":
                if not st.get("observed_custom_color", False):
                    c = "black"
            lw = self._scaled_line_width(st.get("linewidth", 1.0))
            ls = st.get("linestyle", "-")
            mk = st.get("marker", "o")
            md = st.get("mode", "line")
            sz = self._scaled_marker_size(st.get("size", 3))
            z_order = 100 + (layer_count - order_index)
            if key == "Calculated":
                z_order = 10000

            if key == "Observed":
                if self.plot_layout_mode == "split":
                    base_lbl = "Observed"
                else:
                    base_lbl = self._get_sample_display_name(loader)
            else:
                base_lbl = loader.display_names.get(key, label_default)
            if key in loader.phase_names:
                base_lbl = format_chemical_formula_mathtext(base_lbl)
            final_lbl = self._format_tex(base_lbl)

            if self.var_merge_legend.get():
                legend_key = final_lbl
            else:
                if self.plot_layout_mode == "split" and key == "Observed":
                    legend_key = "Observed"
                elif self.plot_layout_mode == "split":
                    project_name = self._format_tex(self._get_split_main_title(loader))
                    legend_key = f"{project_name}: {final_lbl}"
                else:
                    project_name = self._format_tex(self._get_sample_display_name(loader))
                    legend_key = f"{project_name}: {final_lbl}"

            line = None
            line_artist = None
            scatter_artist = None
            if md in ["line", "both"]:
                line, = ax_main.plot(x_vals, y_final, color=c, linewidth=lw, linestyle=ls, label=legend_key, zorder=z_order)
                line_artist = line
                self.art_engine.apply_line_art(line, color=c)
            if md in ["symbol", "both"]:
                s = ax_main.scatter(x_vals, y_final, facecolors=st.get("markerfacecolor", c), edgecolors=st.get("markeredgecolor", c), marker=mk, s=sz, label=legend_key if md == "symbol" else "", zorder=z_order)
                scatter_artist = s
                self.art_engine.apply_marker_art(s)
                if line is None:
                    line = s
            if line is not None:
                setattr(line, "_xrd_legend_role", key)
                setattr(line, "_xrd_legend_label", legend_key)
            fill_artist = None
            if fill:
                fill_artist = ax_main.fill_between(x_vals, offset, y_final, color=st.get("fill_color", c), alpha=0.1, zorder=z_order - 0.5)
            if line_artist is not None:
                self._register_layer_offset_artist(loader, key, "line", line_artist)
            if scatter_artist is not None:
                self._register_layer_offset_artist(loader, key, "scatter", scatter_artist)
            if fill_artist is not None:
                self._register_layer_offset_artist(loader, key, "fill", fill_artist)
            if line and legend_key not in legend_handles:
                legend_handles[legend_key] = line
            if draw_labels and key == "Observed":
                label_artist = self._draw_sample_label(ax_main, loader, x_vals, y_final, c, row_y=offset)
                if label_artist is not None:
                    self._register_layer_offset_artist(loader, key, "text", label_artist)
            elif draw_labels and key in loader.phase_names:
                self._current_phase_label_row_y = offset
                label_artist = self._draw_phase_trace_label(ax_main, loader, key, x_vals, y_final, c)
                if label_artist is not None:
                    self._register_layer_offset_artist(loader, key, "text", label_artist)

        curve_sources = {
            "Observed": (loader.obs, loader.filename, False),
            "Calculated": (loader.calc, "Calculated", False),
            "Background": (loader.back, "Background", False),
        }
        for order_index, layer_key in enumerate(layer_order):
            if layer_key == "Difference":
                continue
            if layer_key in curve_sources:
                y_raw, label_default, fill = curve_sources[layer_key]
                plot_curve(layer_key, y_raw, label_default, fill=fill, order_index=order_index)
            elif layer_key in loader.phase_names and layer_key in loader.phases:
                plot_curve(layer_key, loader.phases[layer_key], layer_key, fill=True, order_index=order_index)
        return split_layout

    def _parsed_zoom_panel_ranges(self):
        """Return validated zoom ranges from the compact UI text field."""
        text = str(getattr(self, "zoom_panel_ranges", "") or "")
        ranges = []
        number_pattern = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
        for raw_part in re.split(r"[;\n]+", text):
            part = re.sub(r"(?<=\d)\s*[\-\u2013\u2014:]\s*(?=\d)", ",", raw_part.strip())
            values = re.findall(number_pattern, part)
            if len(values) < 2:
                continue
            try:
                lo, hi = sorted((float(values[0]), float(values[1])))
            except (TypeError, ValueError):
                continue
            if np.isfinite(lo) and np.isfinite(hi) and hi > lo:
                ranges.append((lo, hi))
            if len(ranges) >= 4:
                break
        return ranges

    def _zoom_panels_requested(self):
        return bool(
            getattr(self, "zoom_panels_enabled", False)
            and getattr(self, "plot_layout_mode", "combined") == "combined"
            and not getattr(self, "is_3d_mode", False)
            and self._parsed_zoom_panel_ranges()
        )

    def _draw_xrd_zoom_panels(
        self, gs, main_row, ax_main, loaders, ranges, tick_dir_2d,
        grid_x, grid_y, reference_row=None,
        show_x_ticks=True, show_x_tick_labels=True,
    ):
        """Draw compact XRD panels and any matching reference-peak rows."""
        colors = ("#f59e73", "#4aa3d2", "#8b74c8", "#56a77b")
        main_ylim = ax_main.get_ylim()
        self.zoom_panel_axes = []

        def apply_zoom_ticks(ax, lo, hi, visible=True, labels_visible=True):
            self._apply_2d_tick_style(
                ax, tick_dir_2d, visible, False, labels_visible, False
            )
            if not visible:
                return
            # Keep each zoom axis tied explicitly to the user-entered range.
            zoom_ticks = [lo, (lo + hi) * 0.5, hi]
            zoom_tick_labels = [
                np.format_float_positional(
                    float(value), precision=6, unique=False,
                    fractional=True, trim='-'
                )
                for value in zoom_ticks
            ]
            ax.set_xticks(zoom_ticks)
            ax.set_xticklabels(zoom_tick_labels if labels_visible else [])

        if getattr(self, "zoom_highlight_ranges", True):
            for index, (lo, hi) in enumerate(ranges):
                ax_main.axvspan(
                    lo,
                    hi,
                    color=colors[index % len(colors)],
                    alpha=0.10,
                    linewidth=0,
                    zorder=0.2,
                )

        for column, (lo, hi) in enumerate(ranges, start=1):
            color = colors[(column - 1) % len(colors)]
            ax_zoom = self.fig.add_subplot(gs[main_row, column], sharey=ax_main)
            for loader in loaders:
                self._plot_loader_curves(ax_zoom, loader, {}, draw_labels=False)
            ax_zoom.set_xlim(lo, hi)
            ax_zoom.set_ylim(main_ylim)
            ax_zoom.set_title("")
            ax_zoom.set_xlabel("")
            ax_zoom.set_ylabel("")
            zoom_has_bottom_reference = reference_row is not None
            apply_zoom_ticks(
                ax_zoom, lo, hi,
                visible=show_x_ticks and not zoom_has_bottom_reference,
                labels_visible=show_x_tick_labels and not zoom_has_bottom_reference,
            )
            ax_zoom.tick_params(axis='y', which='both', left=False, right=False, labelleft=False, labelright=False)
            self._apply_plot_background(ax_zoom)
            self._apply_axis_grid(ax_zoom, grid_x, grid_y, alpha=0.35)
            self._apply_axis_font(ax_zoom)
            for spine in ax_zoom.spines.values():
                spine.set_color(color)
                spine.set_linewidth(max(1.0, float(getattr(self, "plot_box_linewidth", 1.0))))
                spine.set_linestyle((0, (5, 4)))
            self.zoom_panel_axes.append(ax_zoom)

            if zoom_has_bottom_reference:
                ax_zoom_ref = self.fig.add_subplot(gs[reference_row, column])
                self._draw_reference_peak_panel(
                    ax_zoom_ref, lo, hi, draw_labels=False
                )
                apply_zoom_ticks(
                    ax_zoom_ref, lo, hi,
                    visible=show_x_ticks,
                    labels_visible=show_x_tick_labels,
                )
                ax_zoom_ref.tick_params(
                    axis='y', which='both', left=False, right=False,
                    labelleft=False, labelright=False
                )
                ax_zoom_ref.set_xlabel("")
                self._apply_axis_font(ax_zoom_ref)
                for spine in ax_zoom_ref.spines.values():
                    spine.set_color(color)
                    spine.set_linewidth(max(1.0, float(getattr(self, "plot_box_linewidth", 1.0))))
                    spine.set_linestyle((0, (5, 4)))
                self.zoom_panel_axes.append(ax_zoom_ref)

    def draw_plot(self):
        if not getattr(self, "_canvas_ready", True) or self.fig is None or self.canvas is None:
            self._pending_canvas_draw = True
            return
        if self._is_redrawing:
            return
        self._is_redrawing = True
        self._gui_draw_plot_active = True
        try:
        # Sync variables before drawing
            self.is_3d_mode = self.var_3d.get()
            self.intensity_scale = self.var_int_scale.get()
            self.depth_scale = self.var_depth_scale.get()
            if hasattr(self, "var_resid_ratio"):
                self.residual_ratio = self.var_resid_ratio.get()
            if hasattr(self, "var_resid_scale"):
                self.residual_scale = self.var_resid_scale.get()
            if hasattr(self, "var_resid_size"):
                try:
                    value = max(6, min(30, int(float(self.var_resid_size.get()))))
                    self.residual_label_size = value
                    if self.var_resid_size.get() != value:
                        self.var_resid_size.set(value)
                except Exception:
                    pass
            if hasattr(self, "var_tick_label_size"):
                self.tick_label_size = self.var_tick_label_size.get()
            if hasattr(self, "var_tick_label_bold"):
                self.tick_label_bold = self.var_tick_label_bold.get()
            if hasattr(self, "var_tick_label_font"):
                self.tick_label_font = self.var_tick_label_font.get()
            if hasattr(self, "var_tick_label_color"):
                self.tick_label_color = self.var_tick_label_color.get()
            if hasattr(self, "var_tick_length_2d"):
                try:
                    self.tick_length_2d = max(0.0, min(40.0, float(self.var_tick_length_2d.get())))
                except Exception:
                    pass
            if hasattr(self, "var_minor_tick_length_2d"):
                try:
                    self.minor_tick_length_2d = max(0.0, min(40.0, float(self.var_minor_tick_length_2d.get())))
                except Exception:
                    pass
            if hasattr(self, "var_minor_tick_x_2d"):
                self.show_minor_tick_x_2d = bool(self.var_minor_tick_x_2d.get())
            if hasattr(self, "var_minor_tick_y_2d"):
                self.show_minor_tick_y_2d = bool(self.var_minor_tick_y_2d.get())
            if hasattr(self, "var_tick_width_2d"):
                try:
                    self.tick_width_2d = max(0.1, min(12.0, float(self.var_tick_width_2d.get())))
                except Exception:
                    pass
            if hasattr(self, "var_tick_label_x_rotation"):
                try:
                    self.tick_label_x_rotation = max(-90.0, min(90.0, float(self.var_tick_label_x_rotation.get())))
                except Exception:
                    pass
            if hasattr(self, "var_tick_label_y_rotation"):
                try:
                    self.tick_label_y_rotation = max(-90.0, min(90.0, float(self.var_tick_label_y_rotation.get())))
                except Exception:
                    pass
            if hasattr(self, "var_max_x_tick_labels"):
                try:
                    self.max_x_tick_labels = max(2, min(30, int(float(self.var_max_x_tick_labels.get()))))
                except Exception:
                    pass
            if hasattr(self, "var_max_y_tick_labels"):
                try:
                    self.max_y_tick_labels = max(2, min(30, int(float(self.var_max_y_tick_labels.get()))))
                except Exception:
                    pass
            if hasattr(self, "var_plot_box_linewidth"):
                self.plot_box_linewidth = self.var_plot_box_linewidth.get()
            if hasattr(self, "var_fixed_plot_box_enabled"):
                self.fixed_plot_box_enabled = bool(self.var_fixed_plot_box_enabled.get())
            if hasattr(self, "var_plot_box_width_cm"):
                try:
                    self.plot_box_width_cm = max(0.5, min(100.0, float(self.var_plot_box_width_cm.get())))
                except Exception:
                    pass
            if hasattr(self, "var_plot_box_height_cm"):
                try:
                    self.plot_box_height_cm = max(0.5, min(100.0, float(self.var_plot_box_height_cm.get())))
                except Exception:
                    pass
            if hasattr(self, "var_y_autoscale_to_x_range"):
                self.y_autoscale_to_x_range = bool(self.var_y_autoscale_to_x_range.get())
            if hasattr(self, "var_normalize_y_in_x_range"):
                self.normalize_y_in_x_range = bool(self.var_normalize_y_in_x_range.get())
            if hasattr(self, "var_y_autoscale_padding"):
                try:
                    self.y_autoscale_padding_percent = float(self.var_y_autoscale_padding.get())
                except Exception:
                    pass
            if hasattr(self, "var_axis_label_bold"):
                self.axis_label_bold = self.var_axis_label_bold.get()
            if hasattr(self, "var_axis_label_font"):
                self.axis_label_font = self.var_axis_label_font.get()
            if hasattr(self, "var_axis_label_color"):
                self.axis_label_color = self.var_axis_label_color.get()
            if hasattr(self, "var_axis_title_x_2d"):
                self.show_axis_title_x_2d = bool(self.var_axis_title_x_2d.get())
            if hasattr(self, "var_axis_title_y_2d"):
                self.show_axis_title_y_2d = bool(self.var_axis_title_y_2d.get())
            if hasattr(self, "var_axis_label_x_pad"):
                try:
                    self.axis_label_x_pad = max(0.0, min(80.0, float(self.var_axis_label_x_pad.get())))
                except Exception:
                    pass
            if hasattr(self, "var_axis_label_y_pad"):
                try:
                    self.axis_label_y_pad = max(0.0, min(80.0, float(self.var_axis_label_y_pad.get())))
                except Exception:
                    pass
            if hasattr(self, "var_axis_label_y_coord"):
                try:
                    self.axis_label_y_coord = max(-0.50, min(0.20, float(self.var_axis_label_y_coord.get())))
                except Exception:
                    pass
            if hasattr(self, "var_plot_layout"):
                self.plot_layout_mode = self.var_plot_layout.get()
            if hasattr(self, "var_panel_canvas_mode"):
                self.panel_canvas_mode = self._panel_canvas_mode_value()
                self._sync_panel_canvas_mode_transition()
            if hasattr(self, "_sync_reference_controls"):
                self._sync_reference_controls()
            if hasattr(self, "var_plot_title"):
                self.plot_title_text = self.var_plot_title.get()
            if hasattr(self, "var_plot_title_bold"):
                self.plot_title_bold = self.var_plot_title_bold.get()
            if hasattr(self, "var_plot_title_drag"):
                self.plot_title_drag_enabled = self.var_plot_title_drag.get()
            if hasattr(self, "var_zoom_panels_enabled"):
                self.zoom_panels_enabled = bool(self.var_zoom_panels_enabled.get())
            if hasattr(self, "var_zoom_panel_ranges"):
                self.zoom_panel_ranges = str(self.var_zoom_panel_ranges.get())
            if hasattr(self, "var_zoom_panel_width"):
                try:
                    self.zoom_panel_width = max(0.4, min(2.0, float(self.var_zoom_panel_width.get())))
                except Exception:
                    pass
            if hasattr(self, "var_zoom_panel_gap"):
                try:
                    self.zoom_panel_gap = max(0.02, min(0.50, float(self.var_zoom_panel_gap.get())))
                except Exception:
                    pass
            if hasattr(self, "var_zoom_highlight_ranges"):
                self.zoom_highlight_ranges = bool(self.var_zoom_highlight_ranges.get())
            if hasattr(self, "var_plot_memos_enabled"):
                self.plot_memos_enabled = bool(self.var_plot_memos_enabled.get())
            if hasattr(self, "var_plot_top_space"):
                try:
                    self.plot_top_space = max(0.0, min(0.35, float(self.var_plot_top_space.get())))
                except Exception:
                    pass
            if hasattr(self, "var_show_split_panel_titles"):
                self.show_split_panel_titles = self.var_show_split_panel_titles.get()
            if hasattr(self, "var_split_panel_title_source"):
                self.split_panel_title_source = self.var_split_panel_title_source.get()
            if hasattr(self, "var_split_arrangement"):
                self.split_arrangement = self.var_split_arrangement.get()
            if hasattr(self, "var_split_panel_title_size"):
                self.split_panel_title_size = self.var_split_panel_title_size.get()
            if hasattr(self, "var_plot_aspect_ratio"):
                self.plot_aspect_ratio = self.var_plot_aspect_ratio.get()
            if hasattr(self, "var_custom_plot_aspect_ratio"):
                self.custom_plot_aspect_ratio = self.var_custom_plot_aspect_ratio.get()
            if hasattr(self, "var_legend_font_size"):
                try:
                    value = max(6, min(30, int(float(self.var_legend_font_size.get()))))
                    self.legend_font_size = value
                    if self.var_legend_font_size.get() != value:
                        self.var_legend_font_size.set(value)
                except Exception:
                    pass
            if hasattr(self, "var_legend_orientation"):
                self.legend_orientation = self.var_legend_orientation.get()
            if hasattr(self, "var_legend_bold"):
                self.legend_bold = bool(self.var_legend_bold.get())
            if hasattr(self, "var_legend_column_mode"):
                mode = self.var_legend_column_mode.get()
                self.legend_column_mode = "custom" if mode == "manual" else mode
            if hasattr(self, "var_legend_ncol"):
                try:
                    self.legend_ncol = max(1, int(self.var_legend_ncol.get()))
                except Exception:
                    self.legend_ncol = 1
            if hasattr(self, "var_legend_max_width"):
                try:
                    self.legend_max_width_ratio = max(0.40, min(1.00, int(self.var_legend_max_width.get()) / 100.0))
                except Exception:
                    pass
            if hasattr(self, "var_legend_location"):
                self.legend_location = self.var_legend_location.get()
            if hasattr(self, "var_art_effects_enabled"):
                self.art_effects_enabled = self.var_art_effects_enabled.get()
            if hasattr(self, "var_art_line_effect"):
                self.art_line_effect = self.var_art_line_effect.get()
            if hasattr(self, "var_art_text_halo"):
                self.art_text_halo = self.var_art_text_halo.get()
            if hasattr(self, "var_art_marker_depth"):
                self.art_marker_depth = self.var_art_marker_depth.get()
            if hasattr(self, "var_art_label_adjust"):
                self.art_label_adjust = self.var_art_label_adjust.get()
            if hasattr(self, "var_art_palette"):
                self.art_palette_name = self.var_art_palette.get()
            if hasattr(self, "var_show_phase_display_labels"):
                self.show_phase_display_labels = self.var_show_phase_display_labels.get()
            if hasattr(self, "var_phase_display_label_position"):
                self.phase_display_label_position = self.var_phase_display_label_position.get()
            if hasattr(self, "var_phase_display_label_size"):
                try:
                    value = max(6, min(30, int(float(self.var_phase_display_label_size.get()))))
                    self.phase_display_label_size = value
                    if self.var_phase_display_label_size.get() != value:
                        self.var_phase_display_label_size.set(value)
                except Exception:
                    pass
            if hasattr(self, "var_phase_display_label_bold"):
                self.phase_display_label_bold = self.var_phase_display_label_bold.get()
            if hasattr(self, "var_phase_label_vertical_shift"):
                try:
                    self.phase_label_vertical_shift = max(-0.5, min(0.5, float(self.var_phase_label_vertical_shift.get())))
                except Exception:
                    pass
            if hasattr(self, "var_show_sample_labels"):
                self.show_sample_labels = self.var_show_sample_labels.get()
            if hasattr(self, "var_sample_label_position"):
                self.sample_label_position = self.var_sample_label_position.get()
            if hasattr(self, "var_sample_label_size"):
                try:
                    value = max(6, min(30, int(float(self.var_sample_label_size.get()))))
                    self.sample_label_size = value
                    if self.var_sample_label_size.get() != value:
                        self.var_sample_label_size.set(value)
                except Exception:
                    pass
            if hasattr(self, "var_sample_label_bold"):
                self.sample_label_bold = self.var_sample_label_bold.get()
            if hasattr(self, "var_sample_label_vertical_shift"):
                try:
                    self.sample_label_vertical_shift = max(-0.5, min(0.5, float(self.var_sample_label_vertical_shift.get())))
                except Exception:
                    pass

            # Avoid accumulating stale crosshair helper artists
            self.vlines = []
            self.hlines = []
            self.plot_axes = []
            self.zoom_panel_axes = []
            self.fixed_plot_box_axes = []
            self.title_artist = None
            self.title_axis = None
            self.is_dragging_title = False
            self.plot_memo_artists = []
            self.is_dragging_memo = False
            self.plot_memo_drag_index = None
            self._grid_target_ratio_compensation = 1.0
            self._layer_offset_artists = {}

            self._apply_plot_aspect_ratio()
            self.fig.clf()
            self.fig.patch.set_facecolor('white')
            if self.is_3d_mode:
                self._draw_3d()
            else:
                if self.plot_layout_mode == "split":
                    self._draw_2d_split_by_file()
                else:
                    self._draw_2d()
            for ax in list(getattr(self, "plot_axes", [])):
                try:
                    self._apply_axis_font(ax)
                except Exception:
                    pass
            if hasattr(self, "_apply_fixed_plot_box_size"):
                self._apply_fixed_plot_box_size()
            if hasattr(self, "_draw_plot_memos"):
                self._draw_plot_memos()
            self._apply_element_colors()
            self.canvas.draw()
            if hasattr(self, "_sync_plot_canvas_viewport"):
                self._sync_plot_canvas_viewport()
        finally:
            self._gui_draw_plot_active = False
            self._is_redrawing = False

    def _format_tex(self, text):
        if '$' in text: return text
        text = re.sub(r'_\{(.*?)\}', r'$_{\1}$', text)
        text = re.sub(r'\^\{(.*?)\}', r'$^{\1}$', text)
        return text

    def _draw_3d(self):
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - registers the 3D projection lazily.

        ax = self.fig.add_subplot(111, projection='3d')
        
        loaders = [l for _path, l in self._ordered_loaders(visible_only=True) if self._loader_has_data(l)]

        total_files = len(loaders)
        for i, l in enumerate(loaders):
            if l.visibility.get("Observed", True):
                base_depth = l.depth_3d_main if l.depth_3d_main is not None else float(total_files - i)
                depth = base_depth * self.depth_scale
                
                x_vals = self._loader_x(l)
                y_vals = self._loader_y(l, "Observed", l.obs) * self.intensity_scale
                back_vals = self._loader_y(l, "Background", l.back)
                if self.bg_sub_enabled and back_vals.size:
                    y_vals -= (back_vals * self.intensity_scale)
                
                line, = ax.plot(x_vals, [depth]*len(x_vals), y_vals, color=l.project_color, linewidth=1.0)
                self.art_engine.apply_line_art(line, color=l.project_color)
            
            for p in self._get_loader_phase_order(l):
                if l.visibility.get(p, True):
                    base_depth = l.depth_3d_phases[p] if l.depth_3d_phases[p] is not None else float(total_files - i)
                    depth = base_depth * self.depth_scale
                    x_vals = self._loader_x(l)
                    y_vals = self._loader_y(l, p, l.phases[p]) * self.intensity_scale
                    style = l.styles.get(p, {})
                    line, = ax.plot(x_vals, [depth]*len(x_vals), y_vals, color=style.get("color", "black"), alpha=0.8)
                    self.art_engine.apply_line_art(line, color=style.get("color", "black"))

        self._set_x_axis_title(ax)
        self._set_y_axis_title(ax, self.var_ylabel.get())
        
        tdir = self.cmb_tick_dir.get()
        if tdir == "none":
             ax.tick_params(axis='both', which='both', bottom=False, top=False, left=False, right=False)
        else:
             try:
                 ax.tick_params(direction=tdir)
             except ValueError:
                 ax.tick_params(direction="in")

        if not self.var_tick_x.get(): ax.xaxis.set_ticklabels([])
        if not self.var_tick_y.get(): ax.yaxis.set_ticklabels([])
        if not self.var_tick_z.get(): ax.zaxis.set_ticklabels([])

        ax.view_init(elev=self.var_elev.get(), azim=self.var_azim.get())
        try:
            ax.dist = self.var_dist.get()
        except AttributeError:
            pass
        ax.grid(False)
        self._apply_axis_font(ax)
        
        ax.xaxis.pane.fill = False; ax.yaxis.pane.fill = False; ax.zaxis.pane.fill = False

    def _draw_2d(self):
        loaders = [l for _path, l in self._ordered_loaders(visible_only=True) if self._loader_has_data(l)]

        if not loaders: return

        unique_phases = self._get_ordered_visible_phases(loaders)
        diff_loaders = [l for l in loaders if l.visibility.get("Difference", True)]
        
        if not self.var_show_residual.get():
            diff_loaders = [] 

        show_phase_subplot = (
            self.var_show_phase_peaks_top.get()
            and len(unique_phases) > 0
        )
        n_diff = len(diff_loaders)
        show_reference_subplot = self._reference_panel_requested() if hasattr(self, "_reference_panel_requested") else False
        diff_ratio = self._get_residual_height_weight()
        tick_dir_2d = self.cmb_tick_dir_2d.get() if hasattr(self, "cmb_tick_dir_2d") else "in"
        grid_x = self.var_grid_x.get() if hasattr(self, "var_grid_x") else False
        grid_y = self.var_grid_y.get() if hasattr(self, "var_grid_y") else False
        show_x_ticks_2d = self.var_tick_x_2d.get() if hasattr(self, "var_tick_x_2d") else True
        show_y_ticks_2d = self.var_tick_y_2d.get() if hasattr(self, "var_tick_y_2d") else True
        show_x_tick_labels_2d = self.var_tick_label_x_2d.get() if hasattr(self, "var_tick_label_x_2d") else True
        show_y_tick_labels_2d = self.var_tick_label_y_2d.get() if hasattr(self, "var_tick_label_y_2d") else True
        
        # Keep the optional phase-stick panel compact.  The previous 3.0 cap
        # allowed it to become as tall as the diffraction plot; with residual
        # rows present, the main curve could then appear to disappear.
        phase_plot_ratio = 0.16 * len(unique_phases) if show_phase_subplot else 0
        if phase_plot_ratio > 1.4:
            phase_plot_ratio = 1.4
        
        ratios = []
        if show_phase_subplot:
            ratios.append(max(0.45, phase_plot_ratio))
        ratios.append(4.0)
        ratios.extend([diff_ratio] * n_diff) 
        reference_ratio = 0.0
        if show_reference_subplot:
            reference_ratio = self._reference_panel_height_ratio() if hasattr(self, '_reference_panel_height_ratio') else max(0.75, float(getattr(self, 'reference_panel_height', 0.75)))
            ratios.append(reference_ratio)

        # The selected plot aspect ratio should describe the diffraction plot area,
        # not the plot plus appended reference-stick rows.  Compensating the whole
        # GridSpec target ratio prevents the main pattern from looking vertically
        # compressed when reference peaks are shown.
        ratio_without_reference = max(1e-9, sum(ratios) - float(reference_ratio))
        ratio_with_reference = max(1e-9, sum(ratios))
        self._grid_target_ratio_compensation = ratio_without_reference / ratio_with_reference

        hspace = 0.0 if (n_diff > 0 or show_reference_subplot) else self._get_adaptive_hspace(base_hspace=0.08, n_rows=len(ratios))
        zoom_ranges = self._parsed_zoom_panel_ranges() if self._zoom_panels_requested() else []
        panel_width = max(0.4, min(2.0, float(getattr(self, "zoom_panel_width", 1.0))))
        panel_gap = max(0.02, min(0.50, float(getattr(self, "zoom_panel_gap", 0.12))))
        row_scale = max(1.0, sum(ratios) / 4.0)
        column_scale = max(1.0, (5.0 + panel_width * len(zoom_ranges)) / 5.0)
        self._record_panel_canvas_scales(row_scale, column_scale, n_cols=1 + len(zoom_ranges))
        self._apply_preserved_panel_canvas_size(
            row_scale=row_scale,
            column_scale=column_scale,
        )
        gs = GridSpec(
            len(ratios),
            1 + len(zoom_ranges),
            figure=self.fig,
            height_ratios=ratios,
            width_ratios=[5.0] + ([panel_width] * len(zoom_ranges)),
            hspace=hspace,
            wspace=panel_gap if zoom_ranges else 0.0,
        )
        
        x_min = self.custom_xlim[0] if self.custom_xlim else min(l.x_min for l in loaders)
        x_max = self.custom_xlim[1] if self.custom_xlim else max(l.x_max for l in loaders)
        self._current_2d_loader_count = len(loaders)
        self._current_sample_label_xlim = (x_min, x_max)
        
        share_ax = None
        row = 0
        self.plot_axes = []
        
        # 1. Phase Subplot (Separate Tracks)
        if show_phase_subplot:
            if hasattr(self, "_recalculate_reference_patterns_if_needed"):
                self._recalculate_reference_patterns_if_needed()
            ax_p = self.fig.add_subplot(gs[row, 0], sharex=share_ax)
            if share_ax is None: share_ax = ax_p
            self.plot_axes.append(ax_p)
            ax_p.set_yticks([])
            
            ax_p.axis('on')
            ax_p.tick_params(left=False, labelleft=False, bottom=False, labelbottom=False)
            ax_p.grid(False, which='both', axis='both')
            
            for idx, phase_name in enumerate(unique_phases):
                has_plotted = False
                color_ref = "black"

                reference = self._reference_for_phase(phase_name, loaders)
                peak_x_vals = self._main_reference_peak_positions(
                    reference, x_min, x_max
                )
                for l in loaders:
                    if phase_name in l.phases and l.visibility.get(phase_name, True):
                        c = l.styles.get(phase_name, {}).get(
                            "color",
                            generate_formula_color(
                                l.display_names.get(phase_name, phase_name)
                            ),
                        )
                        color_ref = c
                        if peak_x_vals:
                            ax_p.vlines(peak_x_vals, float(idx), idx + 0.86, colors=c, linewidth=self._scaled_line_width(1.2))
                            has_plotted = True
                        break
                        
                if has_plotted and getattr(self, "show_phase_display_labels", False):
                    self._draw_phase_stack_label(ax_p, idx, phase_name, color_ref, loaders, x_min, x_max)
            
            ax_p.set_ylim(0, len(unique_phases))
            ax_p.set_xlim(x_min, x_max)
            self._apply_plot_background(ax_p)
            self._apply_axis_font(ax_p)
            row += 1
            
        # 2. Main Plot
        main_row = row
        ax_main = self.fig.add_subplot(gs[row, 0], sharex=share_ax)
        if share_ax is None: share_ax = ax_main
        self.plot_axes.append(ax_main)
        self.fixed_plot_box_axes = [ax_main]
        
        if n_diff <= 0 and not show_reference_subplot:
            self._set_x_axis_title(ax_main)
        
        legend_handles = {}
        for l in loaders:
            self._plot_loader_curves(ax_main, l, legend_handles)

        self._set_y_axis_title(ax_main)
        ax_main.set_title("")
        ax_main.set_xlim(x_min, x_max)
        self._apply_main_y_range(ax_main)
        self._reserve_top_headroom(ax_main, has_top_title=bool(self.plot_title_text.strip()))
        self._apply_plot_title(ax_main)
        self._draw_legend(ax_main, legend_handles)

        self._apply_2d_tick_style(
            ax_main,
            tick_dir_2d,
            show_x_ticks_2d if (n_diff <= 0 and not show_reference_subplot) else False,
            show_y_ticks_2d,
            show_x_tick_labels_2d if (n_diff <= 0 and not show_reference_subplot) else False,
            show_y_tick_labels_2d
        )

        self._apply_plot_background(ax_main)
        self._apply_axis_grid(ax_main, grid_x, grid_y, alpha=0.5)
        self._apply_axis_font(ax_main)

        if zoom_ranges:
            self._draw_xrd_zoom_panels(
                gs, main_row, ax_main, loaders, zoom_ranges,
                tick_dir_2d, grid_x, grid_y,
                reference_row=(len(ratios) - 1) if show_reference_subplot else None,
                show_x_ticks=show_x_ticks_2d,
                show_x_tick_labels=show_x_tick_labels_2d,
            )
        row += 1
        
        # 3. Difference Plot
        for i, l in enumerate(diff_loaders):
            ax_d = self.fig.add_subplot(gs[row, 0], sharex=share_ax)
            self.plot_axes.append(ax_d)
            
            y = self._loader_y(l, "Difference", l.diff) * self.intensity_scale * self.residual_scale
            c = l.styles.get("Difference", {}).get("color", "gray")
            line, = ax_d.plot(self._loader_x(l), y, color=c, linewidth=self._scaled_line_width(0.8))
            self.art_engine.apply_line_art(line, color=c)
            ax_d._xrd_color_role = "residual"
            ax_d.axhline(0, color=self._element_color("zero", "black"), linewidth=self._scaled_line_width(0.5))
            ax_d.set_yticks([])
            
            resid_font_size = self._get_residual_label_size()
            resid_name = self._format_tex(l.display_names.get("Observed", l.filename))
            txt = ax_d.text(0.01, 0.8, resid_name, transform=ax_d.transAxes, fontsize=resid_font_size, color=self.residual_label_color, fontweight='bold', fontname=self.plot_font_family)
            self.art_engine.apply_text_art(txt)

            is_bottom_x_axis = (i == n_diff - 1) and not show_reference_subplot
            self._apply_2d_tick_style(
                ax_d,
                tick_dir_2d,
                show_x_ticks_2d if is_bottom_x_axis else False,
                False,
                show_x_tick_labels_2d if is_bottom_x_axis else False,
                False
            )

            ax_d.set_xlim(x_min, x_max)
            self._apply_residual_panel_aspect(ax_d)
            self._apply_plot_background(ax_d)
            self._apply_axis_grid(ax_d, grid_x, grid_y, alpha=0.35)
            self._apply_axis_font(ax_d)
            
            if is_bottom_x_axis:
                self._set_x_axis_title(ax_d)
            row += 1
            
        if show_reference_subplot:
            ax_ref = self.fig.add_subplot(gs[row, 0], sharex=share_ax)
            self.plot_axes.append(ax_ref)
            self._draw_reference_peak_panel(ax_ref, x_min, x_max)
            self._apply_2d_tick_style(
                ax_ref,
                tick_dir_2d,
                show_x_ticks_2d,
                False,
                show_x_tick_labels_2d,
                False
            )
            self._set_x_axis_title(ax_ref)
            # Keep reference patterns in a clean boxed panel; do not apply global plot background here.
            ax_ref.set_facecolor("white")
            self._apply_axis_font(ax_ref)
            row += 1

        self.fig.align_ylabels(self.plot_axes)
        self._apply_adaptive_margins(n_cols=1 + len(zoom_ranges))

        # Crosshair helpers
        for ax in self.plot_axes:
            self.vlines.append(ax.axvline(0, color=self._element_color("crosshair", "gray"), linestyle="--", visible=False))
            self.hlines.append(ax.axhline(0, color=self._element_color("crosshair", "gray"), linestyle="--", visible=False))

    def _draw_2d_split_by_file(self):
        self._grid_target_ratio_compensation = 1.0
        loaders = [l for _path, l in self._ordered_loaders(visible_only=True) if self._loader_has_data(l)]
        if not loaders:
            return

        tick_dir_2d = self.cmb_tick_dir_2d.get() if hasattr(self, "cmb_tick_dir_2d") else "in"
        grid_x = self.var_grid_x.get() if hasattr(self, "var_grid_x") else False
        grid_y = self.var_grid_y.get() if hasattr(self, "var_grid_y") else False
        show_x_ticks_2d = self.var_tick_x_2d.get() if hasattr(self, "var_tick_x_2d") else True
        show_y_ticks_2d = self.var_tick_y_2d.get() if hasattr(self, "var_tick_y_2d") else True
        show_x_tick_labels_2d = self.var_tick_label_x_2d.get() if hasattr(self, "var_tick_label_x_2d") else True
        show_y_tick_labels_2d = self.var_tick_label_y_2d.get() if hasattr(self, "var_tick_label_y_2d") else True

        x_min = self.custom_xlim[0] if self.custom_xlim else min(l.x_min for l in loaders)
        x_max = self.custom_xlim[1] if self.custom_xlim else max(l.x_max for l in loaders)
        self._current_2d_loader_count = len(loaders)
        self._current_sample_label_xlim = (x_min, x_max)
        self.plot_axes = []
        title_set = False

        if self.split_arrangement == "horizontal":
            show_resid = self.var_show_residual.get()
            n_cols = len(loaders)
            n_rows = 2 if show_resid else 1
            resid_h = self._get_residual_height_weight()
            ratios = [3.0] + ([resid_h] if show_resid else [])
            row_scale = max(1.0, sum(ratios) / 3.0)
            column_scale = max(1.0, float(n_cols))
            self._record_panel_canvas_scales(row_scale, column_scale, n_cols=n_cols)
            self._apply_preserved_panel_canvas_size(
                row_scale=row_scale,
                column_scale=column_scale,
            )
            hspace = 0.0 if show_resid else self._get_adaptive_hspace(base_hspace=0.14, n_rows=n_rows)
            gs = GridSpec(n_rows, n_cols, figure=self.fig, height_ratios=ratios, hspace=hspace, wspace=0.08)
            share_ax = None
            self.fixed_plot_box_axes = []

            for col, loader in enumerate(loaders):
                ax_main = self.fig.add_subplot(gs[0, col], sharex=share_ax)
                if share_ax is None:
                    share_ax = ax_main
                self.plot_axes.append(ax_main)
                self.fixed_plot_box_axes.append(ax_main)

                legend_handles = {}
                split_layout = self._plot_loader_curves(ax_main, loader, legend_handles)
                if col == 0:
                    self._set_y_axis_title(ax_main)
                has_top_title = self.show_split_panel_titles or (not title_set and bool(self.plot_title_text.strip()))
                ax_main.set_xlim(x_min, x_max)
                self._apply_split_panel_y_range(ax_main, split_layout)
                self._reserve_top_headroom(ax_main, has_top_title=has_top_title)
                if self.show_split_panel_titles:
                    panel_title = self._format_tex(self._get_split_main_title(loader))
                    panel_y = 0.88 if (not title_set and self.plot_title_text.strip()) else 0.95
                    txt = ax_main.text(
                        0.01, panel_y, panel_title,
                        transform=ax_main.transAxes, ha='left', va='top',
                        fontsize=self._get_split_main_title_size(loader),
                        color=self._element_color("panel_title", "black"),
                        fontname=self.plot_font_family, fontweight='bold'
                    )
                    self.art_engine.apply_text_art(txt)
                if not title_set:
                    self._apply_plot_title(ax_main)
                    title_set = True
                self._draw_legend(ax_main, legend_handles)
                has_diff_axis = show_resid and loader.visibility.get("Difference", True)
                if self._should_apply_split_panel_ratio():
                    self._apply_split_panel_aspect(ax_main)
                is_bottom_for_main = not has_diff_axis
                self._apply_2d_tick_style(
                    ax_main, tick_dir_2d,
                    show_x_ticks_2d if is_bottom_for_main else False,
                    show_y_ticks_2d if col == 0 else False,
                    show_x_tick_labels_2d if is_bottom_for_main else False,
                    show_y_tick_labels_2d if col == 0 else False
                )
                self._apply_plot_background(ax_main)
                self._apply_axis_grid(ax_main, grid_x, grid_y, alpha=0.5)
                self._apply_axis_font(ax_main)

                if show_resid:
                    ax_diff = self.fig.add_subplot(gs[1, col], sharex=ax_main)
                    ax_diff._xrd_color_role = "residual"
                    if loader.visibility.get("Difference", True):
                        self.plot_axes.append(ax_diff)
                        y = self._loader_y(loader, "Difference", loader.diff) * self.intensity_scale * self.residual_scale
                        c = loader.styles.get("Difference", {}).get("color", "gray")
                        line, = ax_diff.plot(self._loader_x(loader), y, color=c, linewidth=self._scaled_line_width(0.8))
                        self.art_engine.apply_line_art(line, color=c)
                        ax_diff.axhline(0, color=self._element_color("zero", "black"), linewidth=self._scaled_line_width(0.5))
                        ax_diff.set_yticks([])
                        diff_title = self._format_tex(self._get_split_diff_title(loader))
                        txt = ax_diff.text(
                            0.01, 0.95, diff_title,
                            transform=ax_diff.transAxes, ha='left', va='top',
                            fontsize=self._get_split_diff_title_size(loader),
                            color=self.residual_label_color, fontweight='bold',
                            fontname=self.plot_font_family
                        )
                        self.art_engine.apply_text_art(txt)
                        self._apply_2d_tick_style(
                            ax_diff, tick_dir_2d,
                            show_x_ticks_2d, False,
                            show_x_tick_labels_2d, False
                        )
                        ax_diff.set_xlim(x_min, x_max)
                        self._apply_residual_panel_aspect(ax_diff)
                        self._apply_plot_background(ax_diff)
                        self._apply_axis_grid(ax_diff, grid_x, grid_y, alpha=0.35)
                        self._apply_axis_font(ax_diff)
                        self._set_x_axis_title(ax_diff)
                    else:
                        ax_diff.axis("off")
                        self._set_x_axis_title(ax_main)
            self._apply_adaptive_margins(n_cols=n_cols)
        else:
            show_resid = self.var_show_residual.get()
            group_hspace = 0.18 if show_resid else 0.14
            resid_h = self._get_residual_height_weight()
            group_weights = [
                1.0 + (resid_h / 3.0 if show_resid and loader.visibility.get("Difference", True) else 0.0)
                for loader in loaders
            ]
            row_scale = max(1.0, sum(group_weights))
            self._record_panel_canvas_scales(row_scale, 1.0, n_cols=1)
            self._apply_preserved_panel_canvas_size(
                row_scale=row_scale,
                column_scale=1.0,
            )
            preserve_canvas = (
                self._preserved_canvas_layout_is_active()
                and self._preserved_canvas_has_expansion()
            )
            gs = GridSpec(
                len(loaders), 1, figure=self.fig, hspace=group_hspace,
                height_ratios=group_weights if preserve_canvas else None,
            )
            share_ax = None
            self.fixed_plot_box_axes = []

            for row_idx, loader in enumerate(loaders):
                has_diff_axis = show_resid and loader.visibility.get("Difference", True)
                if has_diff_axis:
                    sub = GridSpecFromSubplotSpec(
                        2, 1, subplot_spec=gs[row_idx],
                        height_ratios=[3.0, self._get_residual_height_weight()],
                        hspace=0.0
                    )
                    ax_main = self.fig.add_subplot(sub[0], sharex=share_ax)
                    if share_ax is None:
                        share_ax = ax_main
                    ax_diff = self.fig.add_subplot(sub[1], sharex=ax_main)
                    ax_diff._xrd_color_role = "residual"
                else:
                    ax_main = self.fig.add_subplot(gs[row_idx], sharex=share_ax)
                    if share_ax is None:
                        share_ax = ax_main
                    ax_diff = None

                self.plot_axes.append(ax_main)
                self.fixed_plot_box_axes.append(ax_main)

                legend_handles = {}
                split_layout = self._plot_loader_curves(ax_main, loader, legend_handles)
                self._set_y_axis_title(ax_main)
                has_top_title = self.show_split_panel_titles or (not title_set and bool(self.plot_title_text.strip()))
                ax_main.set_xlim(x_min, x_max)
                self._apply_split_panel_y_range(ax_main, split_layout)
                self._reserve_top_headroom(ax_main, has_top_title=has_top_title)
                if self.show_split_panel_titles:
                    panel_title = self._format_tex(self._get_split_main_title(loader))
                    panel_y = 0.88 if (not title_set and self.plot_title_text.strip()) else 0.95
                    txt = ax_main.text(
                        0.01, panel_y, panel_title,
                        transform=ax_main.transAxes, ha='left', va='top',
                        fontsize=self._get_split_main_title_size(loader),
                        color=self._element_color("panel_title", "black"),
                        fontname=self.plot_font_family, fontweight='bold'
                    )
                    self.art_engine.apply_text_art(txt)
                if not title_set:
                    self._apply_plot_title(ax_main)
                    title_set = True
                self._draw_legend(ax_main, legend_handles)
                if self._should_apply_split_panel_ratio():
                    self._apply_split_panel_aspect(ax_main)

                self._apply_2d_tick_style(
                    ax_main,
                    tick_dir_2d,
                    show_x_ticks_2d if not has_diff_axis else False,
                    show_y_ticks_2d,
                    show_x_tick_labels_2d if not has_diff_axis else False,
                    show_y_tick_labels_2d
                )
                self._apply_plot_background(ax_main)
                self._apply_axis_grid(ax_main, grid_x, grid_y, alpha=0.5)
                self._apply_axis_font(ax_main)

                if has_diff_axis and ax_diff is not None:
                    self.plot_axes.append(ax_diff)
                    y = self._loader_y(loader, "Difference", loader.diff) * self.intensity_scale * self.residual_scale
                    c = loader.styles.get("Difference", {}).get("color", "gray")
                    line, = ax_diff.plot(self._loader_x(loader), y, color=c, linewidth=self._scaled_line_width(0.8))
                    self.art_engine.apply_line_art(line, color=c)
                    ax_diff.axhline(0, color=self._element_color("zero", "black"), linewidth=self._scaled_line_width(0.5))
                    ax_diff.set_yticks([])
                    diff_title = self._format_tex(self._get_split_diff_title(loader))
                    txt = ax_diff.text(
                        0.01, 0.95, diff_title,
                        transform=ax_diff.transAxes, ha='left', va='top',
                        fontsize=self._get_split_diff_title_size(loader),
                        color=self.residual_label_color,
                        fontweight='bold',
                        fontname=self.plot_font_family
                    )
                    self.art_engine.apply_text_art(txt)
                    self._apply_2d_tick_style(
                        ax_diff,
                        tick_dir_2d,
                        show_x_ticks_2d,
                        False,
                        show_x_tick_labels_2d,
                        False
                    )
                    ax_diff.set_xlim(x_min, x_max)
                    self._apply_residual_panel_aspect(ax_diff)
                    self._apply_plot_background(ax_diff)
                    self._apply_axis_grid(ax_diff, grid_x, grid_y, alpha=0.35)
                    self._apply_axis_font(ax_diff)
                    self._set_x_axis_title(ax_diff, labelpad=6)
                else:
                    self._set_x_axis_title(ax_main, labelpad=6)

            self.fig.align_ylabels(self.plot_axes)
            self._apply_adaptive_margins(n_cols=1)

        for ax in self.plot_axes:
            self.vlines.append(ax.axvline(0, color=self._element_color("crosshair", "gray"), linestyle="--", visible=False))
            self.hlines.append(ax.axhline(0, color=self._element_color("crosshair", "gray"), linestyle="--", visible=False))


