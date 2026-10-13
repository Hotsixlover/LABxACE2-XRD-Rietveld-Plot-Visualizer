# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *


class EventsMixin:
    def on_mouse_move(self, event):
        # Ctrl-drag in Preserve Plot Ratio mode pans the viewport itself. Avoid
        # crosshair redraws or artist movement while that gesture is active.
        if getattr(self, "_plot_canvas_pan_active", False):
            return

        if getattr(self, "is_dragging_memo", False) and event.x is not None and event.y is not None:
            idx = getattr(self, "plot_memo_drag_index", None)
            if idx is not None and 0 <= idx < len(getattr(self, "plot_memos", [])):
                try:
                    fig_w = max(float(self.fig.bbox.width), 1.0)
                    fig_h = max(float(self.fig.bbox.height), 1.0)
                    dx, dy = getattr(self, "plot_memo_drag_offset", (0.0, 0.0))
                    x_fig = max(0.0, min(1.0, float(event.x) / fig_w + dx))
                    y_fig = max(0.0, min(1.0, float(event.y) / fig_h + dy))
                    self.plot_memos[idx]["x"] = x_fig
                    self.plot_memos[idx]["y"] = y_fig
                    for artist in getattr(self, "plot_memo_artists", []):
                        if getattr(artist, "_labx_memo_index", None) == idx:
                            artist.set_position((x_fig, y_fig))
                            break
                    self.canvas.draw_idle()
                    return
                except Exception:
                    pass

        if self.is_dragging_title and self.title_axis is not None and event.inaxes == self.title_axis and event.x is not None and event.y is not None:
            x_ax, y_ax = self.title_axis.transAxes.inverted().transform((event.x, event.y))
            x_ax = max(0.0, min(1.0, float(x_ax)))
            y_ax = max(0.0, min(1.0, float(y_ax)))
            self.plot_title_pos = [x_ax, y_ax]
            if self.title_artist is not None:
                self.title_artist.set_position((x_ax, y_ax))
            self.canvas.draw_idle()
            return

        if self.is_3d_mode or not self.crosshair_enabled or not event.inaxes: 
            for l in self.vlines+self.hlines: l.set_visible(False)
            self.canvas.draw_idle()
            return
            
        for vl in self.vlines:
            vl.set_xdata([event.xdata, event.xdata])
            vl.set_visible(True)
        for i, ax in enumerate(self.plot_axes):
            if ax == event.inaxes:
                self.hlines[i].set_ydata([event.ydata, event.ydata])
                self.hlines[i].set_visible(True)
            else:
                self.hlines[i].set_visible(False)
                
        self.lbl_coords.config(text=f"X: {event.xdata:.2f} / Y: {event.ydata:.2f}")
        self.canvas.draw_idle()

    def on_leave_axes(self, event):
        for l in self.vlines+self.hlines: l.set_visible(False)
        self.canvas.draw_idle()

    def on_mpl_click(self, event):
        gui_event = getattr(event, "guiEvent", None)
        try:
            ctrl_pressed = bool(int(getattr(gui_event, "state", 0)) & 0x0004)
        except Exception:
            ctrl_pressed = False
        key = str(getattr(event, "key", "") or "").lower()
        ctrl_pressed = ctrl_pressed or "control" in key or "ctrl" in key
        if ctrl_pressed and hasattr(self, "_plot_canvas_pan_enabled"):
            if self._plot_canvas_pan_enabled():
                return

        button = getattr(getattr(event, "button", None), "value", getattr(event, "button", None))
        if button == 3 and not ctrl_pressed and hasattr(self, "_reset_plot_canvas_zoom"):
            if self._reset_plot_canvas_zoom():
                return

        if bool(getattr(self, "plot_memos_enabled", False)) and event.x is not None and event.y is not None:
            try:
                renderer = self.canvas.get_renderer()
                for artist in reversed(getattr(self, "plot_memo_artists", [])):
                    try:
                        bbox = artist.get_window_extent(renderer=renderer).expanded(1.08, 1.25)
                        hit = bbox.contains(float(event.x), float(event.y))
                    except Exception:
                        hit, _ = artist.contains(event)
                    if not hit:
                        continue
                    idx = getattr(artist, "_labx_memo_index", None)
                    if idx is None or not (0 <= idx < len(getattr(self, "plot_memos", []))):
                        continue
                    fig_w = max(float(self.fig.bbox.width), 1.0)
                    fig_h = max(float(self.fig.bbox.height), 1.0)
                    memo = self.plot_memos[idx]
                    self.plot_memo_drag_index = idx
                    self.plot_memo_drag_offset = (
                        float(memo.get("x", 0.0)) - float(event.x) / fig_w,
                        float(memo.get("y", 0.0)) - float(event.y) / fig_h,
                    )
                    self.is_dragging_memo = True
                    if hasattr(self, "lb_plot_memos"):
                        try:
                            self.lb_plot_memos.selection_clear(0, tk.END)
                            self.lb_plot_memos.selection_set(idx)
                            self.lb_plot_memos.see(idx)
                            self._on_plot_memo_select()
                        except Exception:
                            pass
                    return
            except Exception:
                pass

        if not self.plot_title_drag_enabled:
            return
        if self.title_artist is None or self.title_axis is None:
            return
        if event.inaxes != self.title_axis:
            return
        contains, _ = self.title_artist.contains(event)
        if contains:
            self.is_dragging_title = True

    def on_mpl_release(self, event):
        self.is_dragging_title = False
        self.is_dragging_memo = False
        self.plot_memo_drag_index = None

