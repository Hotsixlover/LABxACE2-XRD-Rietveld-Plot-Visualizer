# SPDX-License-Identifier: GPL-2.0-or-later
"""Reusable UI2 widgets with no knowledge of application state."""

import tkinter as tk

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:  # Keep a Tk-only fallback for minimal installations.
    Image = ImageDraw = ImageTk = None


def build_antialiased_color_dot(master, color, size=12):
    """Return a transparent, antialiased circular swatch for compact UI rows."""
    if Image is None:
        return None
    try:
        red, green, blue = master.winfo_rgb(color)
        rgb = tuple(int(round(channel / 257.0)) for channel in (red, green, blue))
        scale = 4
        high_size = max(4, int(size)) * scale
        margin = max(1, scale // 2)
        source = Image.new("RGBA", (high_size, high_size), (0, 0, 0, 0))
        ImageDraw.Draw(source).ellipse(
            (margin, margin, high_size - margin - 1, high_size - margin - 1),
            fill=rgb + (255,),
        )
        reduced = source.resize((int(size), int(size)), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(reduced, master=master)
    except Exception:
        return None


def build_ui2_indicator_images(master, accent="#4C7FF0", border="#9AA0A6"):
    """Create compact checkbox/radio images matching the UI2 control language."""

    if Image is not None:
        scale = 4
        size = 16
        high_size = size * scale

        def finish(source):
            reduced = source.resize((size, size), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(reduced, master=master)

        check_off_source = Image.new("RGBA", (high_size, high_size), (0, 0, 0, 0))
        check_on_source = Image.new("RGBA", (high_size, high_size), (0, 0, 0, 0))
        off_draw = ImageDraw.Draw(check_off_source)
        on_draw = ImageDraw.Draw(check_on_source)
        box = (1 * scale, 1 * scale, 15 * scale - 1, 15 * scale - 1)
        off_draw.rectangle(box, fill="#FFFFFF", outline=border, width=scale)
        on_draw.rectangle(box, fill=accent, outline=accent, width=scale)
        on_draw.line(
            ((4 * scale, 8 * scale), (7 * scale, 11 * scale), (12 * scale, 4 * scale)),
            fill="#FFFFFF",
            width=2 * scale,
            joint="curve",
        )

        radio_off_source = Image.new("RGBA", (high_size, high_size), (0, 0, 0, 0))
        radio_on_source = Image.new("RGBA", (high_size, high_size), (0, 0, 0, 0))
        radio_box = (1 * scale, 1 * scale, 15 * scale - 1, 15 * scale - 1)
        ImageDraw.Draw(radio_off_source).ellipse(
            radio_box,
            fill="#FFFFFF",
            outline=border,
            width=scale,
        )
        radio_on_draw = ImageDraw.Draw(radio_on_source)
        radio_on_draw.ellipse(
            radio_box,
            fill="#FFFFFF",
            outline=accent,
            width=2 * scale,
        )
        radio_on_draw.ellipse(
            (5 * scale, 5 * scale, 11 * scale - 1, 11 * scale - 1),
            fill=accent,
        )

        return {
            "check_off": finish(check_off_source),
            "check_on": finish(check_on_source),
            "radio_off": finish(radio_off_source),
            "radio_on": finish(radio_on_source),
        }

    def line(image, x0, y0, x1, y1, color, thickness=1):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        error = dx + dy
        while True:
            for ox in range(-(thickness // 2), thickness - thickness // 2):
                for oy in range(-(thickness // 2), thickness - thickness // 2):
                    px, py = x0 + ox, y0 + oy
                    if 0 <= px < image.width() and 0 <= py < image.height():
                        image.put(color, (px, py))
            if x0 == x1 and y0 == y1:
                break
            twice = 2 * error
            if twice >= dy:
                error += dy
                x0 += sx
            if twice <= dx:
                error += dx
                y0 += sy

    check_off = tk.PhotoImage(master=master, width=16, height=16)
    check_on = tk.PhotoImage(master=master, width=16, height=16)
    for image, fill, edge in (
        (check_off, "#FFFFFF", border),
        (check_on, accent, accent),
    ):
        image.put(fill, to=(1, 1, 15, 15))
        image.put(edge, to=(1, 1, 15, 2))
        image.put(edge, to=(1, 14, 15, 15))
        image.put(edge, to=(1, 1, 2, 15))
        image.put(edge, to=(14, 1, 15, 15))
    line(check_on, 4, 8, 7, 11, "#FFFFFF", thickness=2)
    line(check_on, 7, 11, 12, 4, "#FFFFFF", thickness=2)

    radio_off = tk.PhotoImage(master=master, width=16, height=16)
    radio_on = tk.PhotoImage(master=master, width=16, height=16)
    center = 7.5
    for y in range(16):
        for x in range(16):
            distance_sq = (x - center) ** 2 + (y - center) ** 2
            if distance_sq <= 49:
                radio_off.put(border if distance_sq >= 34 else "#FFFFFF", (x, y))
                radio_on.put(accent if distance_sq >= 34 or distance_sq <= 8 else "#FFFFFF", (x, y))

    return {
        "check_off": check_off,
        "check_on": check_on,
        "radio_off": radio_off,
        "radio_on": radio_on,
    }


class ModernScale(tk.Canvas):
    """Canvas slider with a blue progress track and a white circular thumb."""

    def __init__(
        self,
        master,
        from_=0,
        to=100,
        resolution=1,
        orient="horizontal",
        variable=None,
        command=None,
        releasecommand=None,
        length=110,
        bg="#FFFFFF",
        accent="#4C7FF0",
        troughcolor="#D4D7DB",
        **kwargs,
    ):
        self.from_value = float(from_)
        self.to_value = float(to)
        self.resolution = float(resolution) if resolution not in (None, "") else 0.0
        self.orient = orient
        self.variable = variable or tk.DoubleVar(master=master, value=self.from_value)
        self.command = command
        self.releasecommand = releasecommand
        self.accent = accent
        self.troughcolor = troughcolor
        self._enabled = True
        self._dragging = False
        self._trace_id = None

        for option in (
            "showvalue", "sliderlength", "sliderrelief", "activebackground",
            "bigincrement", "digits", "label", "repeatdelay", "repeatinterval",
            "tickinterval", "takefocus", "bd", "highlightthickness", "relief",
        ):
            kwargs.pop(option, None)
        kwargs.pop("width", None)
        requested_width = int(length) if orient == "horizontal" else 20
        requested_height = 20 if orient == "horizontal" else int(length)
        super().__init__(
            master,
            width=requested_width,
            height=requested_height,
            bg=bg,
            highlightthickness=0,
            bd=0,
            relief="flat",
            cursor="hand2",
            **kwargs,
        )
        self.bind("<Configure>", self._draw)
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Left>", lambda _event: self._step(-1))
        self.bind("<Right>", lambda _event: self._step(1))
        try:
            self._trace_id = self.variable.trace_add("write", lambda *_args: self._draw())
        except Exception:
            self._trace_id = None
        self.after_idle(self._draw)

    def get(self):
        return self.variable.get()

    def set(self, value):
        self._set_value(float(value), notify=False)

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)
        self._dragging = False
        self.configure(cursor="hand2" if self._enabled else "arrow")
        self._draw()

    def _range(self):
        return self.to_value - self.from_value

    def _fraction(self):
        try:
            value = float(self.variable.get())
        except Exception:
            value = self.from_value
        span = self._range()
        return 0.0 if span == 0 else max(0.0, min(1.0, (value - self.from_value) / span))

    def _draw(self, _event=None):
        self.delete("ui2_scale")
        accent = self.accent if self._enabled else "#BFC5CD"
        troughcolor = self.troughcolor if self._enabled else "#E3E6EA"
        knob_fill = "#FFFFFF" if self._enabled else "#F2F3F5"
        knob_outline = "#B8BDC4" if self._enabled else "#D2D6DC"
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        start, end = 7.0, float((width if self.orient == "horizontal" else height) - 7)
        position = start + (end - start) * self._fraction()
        # PIL supersampling looks polished while idle, but allocating and
        # resizing a 4x bitmap for every mouse-motion event makes dragging
        # visibly sticky. Tk canvas primitives are much cheaper during drag.
        if Image is not None and width > 2 and height > 2 and not self._dragging:
            scale = 4
            source = Image.new(
                "RGB",
                (width * scale, height * scale),
                self.cget("bg"),
            )
            draw = ImageDraw.Draw(source)
            track_width = 5 * scale
            knob_radius = 6 * scale
            if self.orient == "horizontal":
                center = height * scale / 2.0
                track_start = start * scale
                track_end = end * scale
                track_position = position * scale
                draw.line(
                    (track_start, center, track_end, center),
                    fill=troughcolor,
                    width=track_width,
                )
                cap_radius = track_width / 2.0
                draw.ellipse(
                    (track_start - cap_radius, center - cap_radius, track_start + cap_radius, center + cap_radius),
                    fill=troughcolor,
                )
                draw.ellipse(
                    (track_end - cap_radius, center - cap_radius, track_end + cap_radius, center + cap_radius),
                    fill=troughcolor,
                )
                draw.line(
                    (track_start, center, track_position, center),
                    fill=accent,
                    width=track_width,
                )
                draw.ellipse(
                    (track_start - cap_radius, center - cap_radius, track_start + cap_radius, center + cap_radius),
                    fill=accent,
                )
                draw.ellipse(
                    (track_position - cap_radius, center - cap_radius, track_position + cap_radius, center + cap_radius),
                    fill=accent,
                )
                knob_box = (
                    track_position - knob_radius,
                    center - knob_radius,
                    track_position + knob_radius,
                    center + knob_radius,
                )
            else:
                center = width * scale / 2.0
                track_start = start * scale
                track_end = end * scale
                track_position = position * scale
                draw.line(
                    (center, track_start, center, track_end),
                    fill=troughcolor,
                    width=track_width,
                )
                cap_radius = track_width / 2.0
                draw.ellipse(
                    (center - cap_radius, track_start - cap_radius, center + cap_radius, track_start + cap_radius),
                    fill=troughcolor,
                )
                draw.ellipse(
                    (center - cap_radius, track_end - cap_radius, center + cap_radius, track_end + cap_radius),
                    fill=troughcolor,
                )
                draw.line(
                    (center, track_start, center, track_position),
                    fill=accent,
                    width=track_width,
                )
                draw.ellipse(
                    (center - cap_radius, track_start - cap_radius, center + cap_radius, track_start + cap_radius),
                    fill=accent,
                )
                draw.ellipse(
                    (center - cap_radius, track_position - cap_radius, center + cap_radius, track_position + cap_radius),
                    fill=accent,
                )
                knob_box = (
                    center - knob_radius,
                    track_position - knob_radius,
                    center + knob_radius,
                    track_position + knob_radius,
                )
            draw.ellipse(
                knob_box,
                fill=knob_fill,
                outline=knob_outline,
                width=scale,
            )
            reduced = source.resize((width, height), Image.Resampling.LANCZOS)
            self._render_image = ImageTk.PhotoImage(reduced, master=self)
            self.create_image(0, 0, anchor=tk.NW, image=self._render_image, tags="ui2_scale")
            return
        if self.orient == "horizontal":
            center = height / 2.0
            self.create_line(start, center, end, center, fill=troughcolor, width=5, capstyle=tk.ROUND, tags="ui2_scale")
            self.create_line(start, center, position, center, fill=accent, width=5, capstyle=tk.ROUND, tags="ui2_scale")
            self.create_oval(position - 6, center - 6, position + 6, center + 6, fill=knob_fill, outline=knob_outline, width=1, tags="ui2_scale")
        else:
            center = width / 2.0
            self.create_line(center, start, center, end, fill=troughcolor, width=5, capstyle=tk.ROUND, tags="ui2_scale")
            self.create_line(center, start, center, position, fill=accent, width=5, capstyle=tk.ROUND, tags="ui2_scale")
            self.create_oval(center - 6, position - 6, center + 6, position + 6, fill=knob_fill, outline=knob_outline, width=1, tags="ui2_scale")

    def _event_fraction(self, event):
        total = self.winfo_width() if self.orient == "horizontal" else self.winfo_height()
        coordinate = event.x if self.orient == "horizontal" else event.y
        return max(0.0, min(1.0, (float(coordinate) - 7.0) / max(1.0, float(total) - 14.0)))

    def _value_from_event(self, event):
        return self.from_value + self._range() * self._event_fraction(event)

    def _set_value(self, value, notify=True):
        low, high = sorted((self.from_value, self.to_value))
        value = max(low, min(high, float(value)))
        if self.resolution > 0:
            value = self.from_value + round((value - self.from_value) / self.resolution) * self.resolution
        try:
            current = self.variable.get()
            if isinstance(current, int) and not isinstance(current, bool):
                value = int(round(value))
        except Exception:
            pass
        self.variable.set(value)
        self._draw()
        if notify and callable(self.command):
            self.command(str(value))

    def _press(self, event):
        if not self._enabled:
            return
        self.focus_set()
        self._dragging = True
        self._set_value(self._value_from_event(event))

    def _drag(self, event):
        if self._enabled and self._dragging:
            self._set_value(self._value_from_event(event))

    def _release(self, _event=None):
        if not self._dragging:
            return
        self._dragging = False
        self._draw()
        if callable(self.releasecommand):
            self.releasecommand(str(self.variable.get()))

    def _step(self, direction):
        if not self._enabled:
            return
        step = self.resolution if self.resolution > 0 else abs(self._range()) / 100.0
        self._set_value(float(self.variable.get()) + direction * step)


class RoundedScrollbar(tk.Canvas):
    """Compact rounded scrollbar compatible with the standard Tk protocol."""

    def __init__(self, master, orient="vertical", command=None, bg="#FFFFFF", **kwargs):
        self.orient = orient
        self.command = command
        self.first, self.last = 0.0, 1.0
        self.dragging = False
        self.hovered = False
        self.visible = True
        self.hide_after_id = None
        self.drag_pointer_origin = 0.0
        self.drag_first_origin = 0.0
        self.drag_thumb_length = 20.0
        self.thumb_bounds = (0.0, 0.0)
        kwargs.setdefault("width" if orient == "vertical" else "height", 10)
        super().__init__(master, bg=bg, highlightthickness=0, bd=0, relief="flat", cursor="hand2", **kwargs)
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self._schedule_hide()

    def set(self, first, last):
        self.first = max(0.0, min(1.0, float(first)))
        self.last = max(self.first, min(1.0, float(last)))
        self._show_temporarily()

    def _cancel_hide(self):
        if self.hide_after_id is None:
            return
        try:
            self.after_cancel(self.hide_after_id)
        except Exception:
            pass
        self.hide_after_id = None

    def _schedule_hide(self, delay=900):
        self._cancel_hide()
        if self.hovered or self.dragging:
            return
        try:
            self.hide_after_id = self.after(delay, self._hide)
        except Exception:
            self.hide_after_id = None

    def _hide(self):
        self.hide_after_id = None
        if self.hovered or self.dragging:
            return
        self.visible = False
        self._draw()

    def _show_temporarily(self):
        self.visible = True
        self._draw()
        self._schedule_hide()

    def _enter(self, _event=None):
        self.hovered = True
        self.visible = True
        self._cancel_hide()
        self._draw()

    def _leave(self, _event=None):
        self.hovered = False
        if not self.dragging:
            self._schedule_hide(delay=250)

    def _metrics(self):
        total = self.winfo_height() if self.orient == "vertical" else self.winfo_width()
        start, end = 4.0, max(5.0, float(total) - 4.0)
        a = start + (end - start) * self.first
        b = start + (end - start) * self.last
        if b - a < 20.0:
            mid = (a + b) / 2.0
            a, b = max(start, mid - 10.0), min(end, mid + 10.0)
        return start, end, a, b

    def _draw(self, _event=None):
        self.delete("all")
        if not self.visible or self.last - self.first >= 0.999:
            return
        start, end, a, b = self._metrics()
        self.thumb_bounds = (a, b)
        center = self.winfo_width() / 2 if self.orient == "vertical" else self.winfo_height() / 2
        thumb = "#AEB2B7" if self.dragging else "#C7C9CC"
        if Image is not None and self.winfo_width() > 2 and self.winfo_height() > 2:
            scale = 4
            width, height = self.winfo_width(), self.winfo_height()
            source = Image.new("RGB", (width * scale, height * scale), self.cget("bg"))
            draw = ImageDraw.Draw(source)
            line_width = 4 * scale
            cap_radius = line_width / 2.0

            def rounded_line(x0, y0, x1, y1, color):
                draw.line((x0, y0, x1, y1), fill=color, width=line_width)
                draw.ellipse((x0 - cap_radius, y0 - cap_radius, x0 + cap_radius, y0 + cap_radius), fill=color)
                draw.ellipse((x1 - cap_radius, y1 - cap_radius, x1 + cap_radius, y1 + cap_radius), fill=color)

            if self.orient == "vertical":
                x = center * scale
                rounded_line(x, start * scale, x, end * scale, "#F1F3F4")
                rounded_line(x, a * scale, x, b * scale, thumb)
            else:
                y = center * scale
                rounded_line(start * scale, y, end * scale, y, "#F1F3F4")
                rounded_line(a * scale, y, b * scale, y, thumb)
            reduced = source.resize((width, height), Image.Resampling.LANCZOS)
            self._render_image = ImageTk.PhotoImage(reduced, master=self)
            self.create_image(0, 0, anchor=tk.NW, image=self._render_image)
            return
        if self.orient == "vertical":
            self.create_line(center, start, center, end, fill="#F1F3F4", width=4, capstyle=tk.ROUND)
            self.create_line(center, a, center, b, fill=thumb, width=4, capstyle=tk.ROUND)
        else:
            self.create_line(start, center, end, center, fill="#F1F3F4", width=4, capstyle=tk.ROUND)
            self.create_line(a, center, b, center, fill=thumb, width=4, capstyle=tk.ROUND)

    def _coord(self, event):
        return float(event.y if self.orient == "vertical" else event.x)

    def _press(self, event):
        self.hovered = True
        self.visible = True
        self._cancel_hide()
        pointer = self._coord(event)
        start, end, a, b = self._metrics()
        thumb_length = max(1.0, b - a)
        movable = max(1.0, (end - start) - thumb_length)
        if not a <= pointer <= b and self.command is not None:
            target = (pointer - start - thumb_length / 2.0) / movable
            self.command("moveto", max(0.0, min(1.0, target)))
            start, end, a, b = self._metrics()
            thumb_length = max(1.0, b - a)
        self.dragging = True
        self.drag_pointer_origin = pointer
        self.drag_first_origin = self.first
        self.drag_thumb_length = thumb_length
        self._draw()

    def _drag(self, event):
        if self.dragging:
            self._move(self._coord(event))

    def _release(self, _event):
        self.dragging = False
        self._draw()
        if not self.hovered:
            self._schedule_hide(delay=250)

    def _move(self, pointer):
        if self.command is None:
            return
        start, end, _a, _b = self._metrics()
        movable = max(1.0, (end - start) - self.drag_thumb_length)
        delta = pointer - self.drag_pointer_origin
        fraction = self.drag_first_origin + delta / movable
        self.command("moveto", max(0.0, min(1.0, fraction)))


class CollapsibleSection(tk.Frame):
    """UI2 white card with a compact clickable header."""

    def __init__(self, master, title, expanded=True, bg="#FFFFFF", accent="#4285F4", **kwargs):
        super().__init__(master, bg=bg, highlightbackground="#DADCE0", highlightthickness=1, bd=0, **kwargs)
        self.title_text = str(title)
        self.expanded = bool(expanded)
        self.toggle_button = tk.Button(
            self, command=self.toggle, anchor="w", relief="flat", bd=0,
            bg=bg, activebackground="#EEF3FB", fg="#202124",
            activeforeground=accent, font=("Calibri", 9, "bold"),
            cursor="hand2", padx=9, pady=6,
        )
        self.toggle_button.pack(fill="x")
        self.body = tk.Frame(self, bg=bg)
        self._refresh()

    def _refresh(self):
        self.toggle_button.configure(text=("▼  " if self.expanded else "▶  ") + self.title_text)
        if self.expanded:
            if not self.body.winfo_manager():
                self.body.pack(fill="x", padx=8, pady=(0, 8))
        else:
            self.body.pack_forget()

    def toggle(self):
        self.expanded = not self.expanded
        self._refresh()
