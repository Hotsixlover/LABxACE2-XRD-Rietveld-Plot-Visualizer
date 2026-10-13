# SPDX-License-Identifier: GPL-2.0-or-later
import colorsys

from matplotlib.colors import to_hex, to_rgb

from xrd_rietveld_manager.common import *


COLOR_STRATEGIES = [
    "Hybrid Recommended",
    "Same Phase Same Color",
    "File Family Gradient",
    "Role Based Neutral",
    "Manual Protect",
]


class ColorDirectorMixin:
    def _mix_color(self, color_a, color_b, amount=0.5):
        amount = max(0.0, min(1.0, float(amount)))
        ra, ga, ba = to_rgb(color_a)
        rb, gb, bb = to_rgb(color_b)
        return to_hex((
            ra * (1.0 - amount) + rb * amount,
            ga * (1.0 - amount) + gb * amount,
            ba * (1.0 - amount) + bb * amount,
        ))

    def _adjust_color(self, color, lightness=1.0, saturation=1.0):
        r, g, b = to_rgb(color)
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        l = max(0.0, min(1.0, l * float(lightness)))
        s = max(0.0, min(1.0, s * float(saturation)))
        return to_hex(colorsys.hls_to_rgb(h, l, s))

    def _calculated_role_color(self, file_color):
        # Avoid a fixed red calculated trace; it collides with temperature/file gradients.
        return self._adjust_color(file_color, lightness=0.62, saturation=0.72)

    def _background_role_color(self, file_color):
        return self._mix_color(self._adjust_color(file_color, lightness=1.25, saturation=0.35), "#9AA3AD", 0.55)

    def _difference_role_color(self):
        return "#6B7280"

    def _file_family_phase_colors(self, file_color, count):
        count = max(1, int(count))
        start = self._mix_color(file_color, "#FFFFFF", 0.72)
        mid = self._adjust_color(file_color, lightness=0.95, saturation=0.75)
        end = self._adjust_color(file_color, lightness=0.48, saturation=0.95)
        return self._sample_local_gradient([start, mid, end], count)

    def _sample_local_gradient(self, stops, count):
        from matplotlib.colors import LinearSegmentedColormap

        count = max(1, int(count))
        cmap = LinearSegmentedColormap.from_list("file_family_gradient", stops)
        if count == 1:
            return [to_hex(cmap(0.55))]
        return [to_hex(cmap(i / max(count - 1, 1))) for i in range(count)]

    def _get_color_director_settings(self):
        strategy = getattr(self, "color_strategy", "Hybrid Recommended")
        file_palette = getattr(self, "file_color_palette", "LAB×ACE² Thermal Gradient")
        phase_palette = getattr(self, "phase_color_palette", "Editorial Ink")
        reverse_files = getattr(self, "reverse_file_palette", False)
        reverse_phases = getattr(self, "reverse_phase_palette", False)
        lock_phases = getattr(self, "lock_same_phase_colors", True)
        preserve_manual = getattr(self, "preserve_manual_colors", False)

        for attr, fallback in [
            ("var_color_strategy", strategy),
            ("var_file_color_palette", file_palette),
            ("var_phase_color_palette", phase_palette),
            ("var_reverse_file_palette", reverse_files),
            ("var_reverse_phase_palette", reverse_phases),
            ("var_lock_same_phase_colors", lock_phases),
            ("var_preserve_manual_colors", preserve_manual),
        ]:
            obj = getattr(self, attr, None)
            if obj is not None and hasattr(obj, "get"):
                value = obj.get()
                if attr == "var_color_strategy":
                    strategy = value
                elif attr == "var_file_color_palette":
                    file_palette = value
                elif attr == "var_phase_color_palette":
                    phase_palette = value
                elif attr == "var_reverse_file_palette":
                    reverse_files = bool(value)
                elif attr == "var_reverse_phase_palette":
                    reverse_phases = bool(value)
                elif attr == "var_lock_same_phase_colors":
                    lock_phases = bool(value)
                elif attr == "var_preserve_manual_colors":
                    preserve_manual = bool(value)

        self.color_strategy = strategy
        self.file_color_palette = file_palette
        self.phase_color_palette = phase_palette
        self.reverse_file_palette = reverse_files
        self.reverse_phase_palette = reverse_phases
        self.lock_same_phase_colors = lock_phases
        self.preserve_manual_colors = preserve_manual
        return strategy, file_palette, phase_palette, reverse_files, reverse_phases, lock_phases, preserve_manual

    def _build_phase_color_map(self, phase_palette, reverse=False):
        seen = []
        seen_set = set()
        loaders = [loader for _path, loader in self._ordered_loaders()] if hasattr(self, "_ordered_loaders") else list(self.loaded_files.values())
        for loader in loaders:
            for phase_name in loader.phase_names:
                key = self._phase_color_group_key(loader, phase_name)
                if key and key not in seen_set:
                    seen.append(key)
                    seen_set.add(key)
        colors = get_palette_colors(phase_palette, len(seen))
        if reverse:
            colors = list(reversed(colors))
        return dict(zip(seen, colors))

    def _set_style_color(self, loader, key, color, mark_manual=False):
        style = loader.styles.setdefault(key, loader._get_default_style(key))
        style["color"] = color
        if key == "Observed":
            style["observed_custom_color"] = bool(mark_manual)

    def apply_color_director(self, target_paths=None, reset_manual=False):
        if not self.loaded_files:
            messagebox.showinfo("Color Director", "Load at least one DIA file first.")
            return

        strategy, file_palette, phase_palette, reverse_files, reverse_phases, lock_phases, preserve_manual = self._get_color_director_settings()
        ordered = list(self._ordered_loaders()) if hasattr(self, "_ordered_loaders") else list(self.loaded_files.items())
        if target_paths is not None:
            target_paths = set(target_paths)
            ordered = [(path, loader) for path, loader in ordered if path in target_paths]
        if not ordered:
            return

        file_colors = get_palette_colors(file_palette, len(ordered))
        if reverse_files:
            file_colors = list(reversed(file_colors))

        phase_color_map = self._build_phase_color_map(phase_palette, reverse=reverse_phases)
        next_phase_overrides = dict(getattr(self, "phase_color_overrides", {}))

        for (path, loader), file_color in zip(ordered, file_colors):
            loader.project_color = file_color

            observed_style = loader.styles.setdefault("Observed", loader._get_default_style("Observed"))
            if reset_manual:
                observed_style["observed_custom_color"] = False
            can_update_observed = not preserve_manual or not observed_style.get("observed_custom_color", False)
            if can_update_observed:
                self._set_style_color(loader, "Observed", file_color, mark_manual=False)

            if strategy == "Role Based Neutral":
                calc_color = "#171717"
            else:
                calc_color = self._calculated_role_color(file_color)
            self._set_style_color(loader, "Calculated", calc_color)
            loader.styles.setdefault("Calculated", loader._get_default_style("Calculated"))["linewidth"] = max(
                1.0, loader.styles.get("Calculated", {}).get("linewidth", 1.0)
            )

            self._set_style_color(loader, "Background", self._background_role_color(file_color))
            self._set_style_color(loader, "Difference", self._difference_role_color())

            if strategy == "Manual Protect":
                continue

            if strategy == "File Family Gradient":
                phase_colors = self._file_family_phase_colors(file_color, len(loader.phase_names))
                for phase_name, phase_color in zip(loader.phase_names, phase_colors):
                    self._set_style_color(loader, phase_name, phase_color)
            else:
                for phase_name in loader.phase_names:
                    group_key = self._phase_color_group_key(loader, phase_name)
                    phase_color = phase_color_map.get(group_key, "#111827")
                    self._set_style_color(loader, phase_name, phase_color)
                    if lock_phases:
                        next_phase_overrides[group_key] = phase_color

        if lock_phases and strategy != "File Family Gradient":
            self.phase_color_overrides = next_phase_overrides
            self.sync_phase_colors_by_name(redraw=False, rebuild=False)

        self.rebuild_layer_controls()
        self._refresh_color_preview()
        self._request_draw_plot()

    def apply_color_director_all(self):
        self.apply_color_director()

    def apply_color_director_selected(self):
        selection = self.file_tree.selection() if hasattr(self, "file_tree") else []
        paths = [item for item in selection if item in self.loaded_files]
        if not paths:
            messagebox.showinfo("Color Director", "Select a project file first.")
            return
        self.apply_color_director(target_paths=paths)

    def reset_manual_colors_and_apply(self):
        for loader in self.loaded_files.values():
            if "Observed" in loader.styles:
                loader.styles["Observed"]["observed_custom_color"] = False
        self.apply_color_director(reset_manual=True)

    def _refresh_color_preview(self):
        frame = getattr(self, "color_preview_frame", None)
        if frame is None or not frame.winfo_exists():
            return
        for child in frame.winfo_children():
            child.destroy()
        strategy, file_palette, phase_palette, reverse_files, reverse_phases, _lock, _preserve = self._get_color_director_settings()
        file_colors = get_palette_colors(file_palette, 8)
        phase_colors = get_palette_colors(phase_palette, 8)
        if reverse_files:
            file_colors = list(reversed(file_colors))
        if reverse_phases:
            phase_colors = list(reversed(phase_colors))

        def draw_row(title, colors, row):
            tk.Label(frame, text=title, bg=self.ui_panel, fg=self.ui_text, width=10, anchor="w", font=self.ui_font).grid(row=row, column=0, sticky="w", padx=4, pady=3)
            for idx, color in enumerate(colors):
                sw = tk.Canvas(frame, width=22, height=18, bg=self.ui_panel, highlightthickness=0)
                sw.create_rectangle(2, 3, 20, 15, fill=color, outline=color)
                sw.grid(row=row, column=idx + 1, padx=1, pady=3)

        draw_row("Files", file_colors, 0)
        draw_row("Phases", phase_colors, 1)

    def _setup_color_tab(self):
        """Legacy hook retained; Color Setting now owns all visible color tools."""
        return None
