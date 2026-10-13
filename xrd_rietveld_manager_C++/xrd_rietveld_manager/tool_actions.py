# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *


class ToolActionsMixin:
    def toggle_crosshair_state(self):
        self.crosshair_enabled = not self.crosshair_enabled
        self.btn_cross.config(bg="#a0a0a0" if self.crosshair_enabled else "#e0e0e0")

    def toggle_bg_sub_state(self):
        self.bg_sub_enabled = not self.bg_sub_enabled
        self.btn_bg.config(bg="#a0a0a0" if self.bg_sub_enabled else "#e0e0e0")
        self._request_draw_plot(delay_ms=1)

    def open_xscale_dialog(self):
        cur_x = self._format_axis_range(self.custom_xlim)
        prompt = (
            "Enter X range as: Xmin,Xmax\n\n"
            "Y axis will be auto-scaled from the visible data inside this X range "
            "when 'Auto Y to X Range' is enabled.\n"
            "If 'Normalize in X Range' is enabled, displayed intensities are also "
            "re-normalized from this X window.\n\n"
            f"Current X: {cur_x}\n\n"
            "Example: 18,32"
        )
        res = simpledialog.askstring("X Range", prompt, initialvalue=cur_x)
        if res:
            try:
                self.custom_xlim = self._parse_axis_range_part(res, "X")
                # The requested workflow is auto-Y-from-X, so discard old manual Y limits.
                self.custom_ylim = None
                self._request_draw_plot(delay_ms=1)
            except ValueError:
                messagebox.showerror("Error", "Invalid X range format. Use: Xmin,Xmax")

    def _format_axis_range(self, value):
        if not value:
            return "auto"
        return f"{value[0]:g},{value[1]:g}"

    def _parse_axis_range_part(self, text, axis_name):
        text = str(text or "").strip()
        if not text or text.lower() in {"auto", "none", "reset", "-"}:
            return None
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 2:
            raise ValueError(f"{axis_name} range must be min,max.")
        mn, mx = float(parts[0]), float(parts[1])
        if mn == mx:
            raise ValueError(f"{axis_name} min and max must be different.")
        if mn > mx:
            mn, mx = mx, mn
        return (mn, mx)

    def open_axis_range_dialog(self):
        self.open_xscale_dialog()

    def reset_axis_ranges(self):
        self.custom_xlim = None
        self.custom_ylim = None
        self._request_draw_plot(delay_ms=1)

