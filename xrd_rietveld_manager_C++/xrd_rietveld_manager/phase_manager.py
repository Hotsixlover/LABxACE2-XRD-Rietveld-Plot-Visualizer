# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *


class PhaseManagerMixin:
    def _apply_phase_name_overrides_to_loader(self, loader):
        for phase_name in loader.phase_names:
            if phase_name in self.phase_name_overrides:
                loader.display_names[phase_name] = self.phase_name_overrides[phase_name]

    def _phase_color_link_enabled(self):
        """Same-name phase colors are an always-on project invariant."""
        return True

    def _phase_color_group_key(self, loader, phase_name):
        display_name = loader.display_names.get(phase_name, phase_name)
        key = re.sub(r"\s+", " ", str(display_name or phase_name).strip())
        return key.casefold()

    def _apply_phase_group_color(self, group_key, color):
        if not group_key or not color:
            return
        self.phase_color_overrides[group_key] = color
        for loader in self.loaded_files.values():
            for phase_name in loader.phase_names:
                if self._phase_color_group_key(loader, phase_name) == group_key:
                    loader.styles.setdefault(phase_name, loader._get_default_style(phase_name))
                    loader.styles[phase_name]["color"] = color

    def _apply_phase_color_overrides_to_loader(self, loader):
        for phase_name in loader.phase_names:
            group_key = self._phase_color_group_key(loader, phase_name)
            color = self.phase_color_overrides.get(group_key)
            if color:
                loader.styles.setdefault(phase_name, loader._get_default_style(phase_name))
                loader.styles[phase_name]["color"] = color

    def sync_phase_colors_by_name(self, redraw=True, rebuild=True):
        if not self.loaded_files:
            return

        group_colors = dict(self.phase_color_overrides)
        if hasattr(self, "_ordered_loaders"):
            ordered_loaders = [loader for _path, loader in self._ordered_loaders()]
        else:
            ordered_loaders = list(self.loaded_files.values())

        for loader in ordered_loaders:
            for phase_name in loader.phase_names:
                group_key = self._phase_color_group_key(loader, phase_name)
                if not group_key:
                    continue
                style = loader.styles.setdefault(phase_name, loader._get_default_style(phase_name))
                if group_key not in group_colors:
                    group_colors[group_key] = style.get("color", "#000000")
                style["color"] = group_colors[group_key]

        self.phase_color_overrides = group_colors
        if rebuild:
            self.rebuild_layer_controls()
        if redraw:
            self._request_draw_plot()

    def apply_art_palette_to_phases(self):
        palette_name = self.var_art_palette.get() if hasattr(self, "var_art_palette") else self.art_palette_name
        phase_keys = []
        seen = set()
        ordered_loaders = [loader for _path, loader in self._ordered_loaders()] if hasattr(self, "_ordered_loaders") else list(self.loaded_files.values())
        for loader in ordered_loaders:
            for phase_name in loader.phase_names:
                group_key = self._phase_color_group_key(loader, phase_name)
                if group_key not in seen:
                    seen.add(group_key)
                    phase_keys.append(group_key)
        if not phase_keys:
            messagebox.showinfo("Palette", "Load at least one file with phases first.")
            return
        colors = get_palette_colors(palette_name, len(phase_keys))
        for group_key, color in zip(phase_keys, colors):
            self._apply_phase_group_color(group_key, color)
        self.art_palette_name = palette_name
        self.rebuild_layer_controls()
        self._request_draw_plot()

    def auto_plot_stack_deferred(self):
        current_base = 0.0
        
        loader_iter = self._ordered_loaders(visible_only=True) if hasattr(self, "_ordered_loaders") else self.loaded_files.items()
        for i, (_path, l) in enumerate(loader_iter):
            l.phase_auto_stack_order = []
            l.phase_auto_stack_offsets = {}
            
            y_data = getattr(l, "obs_np", np.asarray(l.obs, dtype=float)) * self.var_int_scale.get()
            back_data = getattr(l, "back_np", np.asarray(l.back, dtype=float))
            if self.bg_sub_enabled and back_data.size:
                y_data -= (back_data * self.var_int_scale.get())
            
            local_max = np.max(y_data) if len(y_data) > 0 else 0.0
            
            shift_keys = ["Observed", "Calculated", "Background", "Difference"] + l.phase_names
            for k in shift_keys:
                l.offsets[k] = current_base
            
            current_base += local_max + (local_max * 0.1)
        self.rebuild_layer_controls()
        self._request_draw_plot()

    def _get_offset_step(self):
        try:
            return float(self.var_offset_step.get())
        except (ValueError, TypeError, AttributeError):
            return 0.05

    def reset_offsets_deferred(self):
        for loader in self.loaded_files.values():
            for key in list(loader.offsets.keys()):
                loader.offsets[key] = 0.0
            loader.phase_auto_stack_order = []
            loader.phase_auto_stack_offsets = {}
        self.rebuild_layer_controls()
        self._request_draw_plot()

    def distribute_offsets_evenly_deferred(self):
        visible_loaders = [loader for _path, loader in self._ordered_loaders(visible_only=True)] if hasattr(self, "_ordered_loaders") else [loader for loader in self.loaded_files.values() if loader.global_visible]
        if not visible_loaders:
            return

        step = max(self._get_offset_step(), 0.01)
        current_top = None
        for loader_idx, loader in enumerate(visible_loaders):
            y_obs = getattr(loader, "obs_np", np.asarray(loader.obs, dtype=float)) * self.var_int_scale.get() if loader.obs else np.array([])
            y_calc = getattr(loader, "calc_np", np.asarray(loader.calc, dtype=float)) * self.var_int_scale.get() if loader.calc else np.array([])
            y_back_raw = getattr(loader, "back_np", np.asarray(loader.back, dtype=float))
            if self.bg_sub_enabled and y_back_raw.size:
                y_back = y_back_raw * self.var_int_scale.get()
                if y_obs.size:
                    y_obs = y_obs - y_back
                if y_calc.size:
                    y_calc = y_calc - y_back

            peaks = []
            if y_obs.size:
                peaks.append(float(np.max(y_obs)))
            if y_calc.size:
                peaks.append(float(np.max(y_calc)))
            file_peak = max(peaks) if peaks else 1.0
            file_peak = max(file_peak, 0.05)

            # Keep the draggable Layer Order & Style phase order.
            phase_strength = []
            for phase in self._get_loader_phase_order(loader):
                y_phase = getattr(loader, "phases_np", {}).get(phase, np.asarray(loader.phases.get(phase, []), dtype=float)) * self.var_int_scale.get()
                pmax = float(np.max(y_phase)) if y_phase.size else 0.0
                phase_strength.append((phase, pmax))
            loader.phase_auto_stack_order = [phase for phase, _pmax in phase_strength]

            phase_step = max(file_peak * 0.22, step * 2.0)
            n_phase = len(phase_strength)
            inter_file_gap = max(file_peak * 0.20, step * 4.0)

            # Place each file block so phases go downward while files do not overlap.
            if loader_idx == 0 or current_top is None:
                current_base = 0.0
            else:
                current_base = current_top + inter_file_gap + n_phase * phase_step

            # Keep core curves attached for each file.
            for key in ["Observed", "Calculated", "Background", "Difference"]:
                if key in loader.offsets:
                    loader.offsets[key] = current_base

            # Stack only phase curves downward from the core curves.
            for idx, (phase, _pmax) in enumerate(phase_strength):
                loader.offsets[phase] = current_base - (idx + 1) * phase_step

            # Remember the generated positions.  In Split layout these are
            # the zero point for later manual Layer Order & Style movement.
            loader.phase_auto_stack_offsets = {
                key: float(loader.offsets.get(key, 0.0))
                for key in ["Observed", "Calculated", "Background"] + list(loader.phase_names)
            }

            current_top = current_base + file_peak
        self.rebuild_layer_controls()
        self._request_draw_plot()

