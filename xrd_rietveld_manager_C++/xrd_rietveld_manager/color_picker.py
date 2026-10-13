# SPDX-License-Identifier: GPL-2.0-or-later
import colorsys
import ctypes
import json
import os
import platform
import re
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from xrd_rietveld_manager.branding import APP_NAME

from matplotlib.colors import is_color_like, to_hex, to_rgb

from xrd_rietveld_manager.palettes import available_palette_names, get_palette_colors
from xrd_rietveld_manager.popup_utils import (
    POPUP_PRIMARY_ACTIVE_BG,
    POPUP_PRIMARY_BG,
    POPUP_SECONDARY_ACTIVE_BG,
    POPUP_SECONDARY_BG,
    POPUP_SURFACE_BG,
    monitor_workarea_for_point,
    native_toplevel_hwnd,
    place_window_on_parent_monitor,
)
from xrd_rietveld_manager.ui2_widgets import ModernScale, RoundedScrollbar

try:
    from PIL import Image, ImageGrab, ImageTk
except ImportError:
    Image = ImageGrab = ImageTk = None


HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")
MAX_SAVED_COLORS = 18
PICKER_WIDTH = 380
PICKER_HEIGHT = 150


def _normalize_color(value, fallback="#1f77b4"):
    if value and is_color_like(value):
        return to_hex(value)
    return fallback


def _rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(r))),
        max(0, min(255, int(g))),
        max(0, min(255, int(b))),
    )


def _saved_colors_path(legacy=False):
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if base:
        directory = "XRD Rietveld Manager" if legacy else APP_NAME
        return Path(base) / directory / "saved_colors.json"
    directory = ".xrd_rietveld_manager" if legacy else ".labxace2_xrd_rietveld_plot_visualizer"
    return Path.home() / directory / "saved_colors.json"


def _load_saved_colors(path=None):
    if path is None and not _saved_colors_path().exists():
        # Read old preferences without moving/deleting the user's existing file.
        path = _saved_colors_path(legacy=True)
    path = Path(path) if path is not None else _saved_colors_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    if not isinstance(payload, list):
        return []
    colors = []
    for value in payload:
        if not isinstance(value, str) or not is_color_like(value):
            continue
        color = to_hex(value)
        if color not in colors:
            colors.append(color)
        if len(colors) >= MAX_SAVED_COLORS:
            break
    return colors


def _store_saved_colors(colors, path=None):
    path = Path(path) if path is not None else _saved_colors_path()
    normalized = []
    for value in colors:
        if is_color_like(value):
            color = to_hex(value)
            if color not in normalized:
                normalized.append(color)
        if len(normalized) >= MAX_SAVED_COLORS:
            break
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def _virtual_screen_bounds(widget=None):
    if platform.system() == "Windows":
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            return tuple(int(user32.GetSystemMetrics(index)) for index in (76, 77, 78, 79))
        except Exception:
            pass
    width = int(widget.winfo_screenwidth()) if widget is not None else 1920
    height = int(widget.winfo_screenheight()) if widget is not None else 1080
    return 0, 0, width, height


class _NativeRect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long), ("top", ctypes.c_long),
        ("right", ctypes.c_long), ("bottom", ctypes.c_long),
    ]


def _monitor_bounds(widget=None):
    """Return one physical-pixel rectangle per monitor."""
    if platform.system() == "Windows":
        try:
            monitors = []
            callback_type = ctypes.WINFUNCTYPE(
                ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                ctypes.POINTER(_NativeRect), ctypes.c_void_p,
            )

            def collect(_monitor, _dc, rect_pointer, _data):
                rect = rect_pointer.contents
                monitors.append((
                    int(rect.left), int(rect.top),
                    int(rect.right), int(rect.bottom),
                ))
                return 1

            callback = callback_type(collect)
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.EnumDisplayMonitors(None, None, callback, None)
            if monitors:
                return monitors
        except Exception:
            pass
    left, top, width, height = _virtual_screen_bounds(widget)
    return [(left, top, left + width, top + height)]


def _window_center_in_physical_pixels(widget):
    if platform.system() == "Windows":
        try:
            hwnd = native_toplevel_hwnd(widget)
            rect = _NativeRect()
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            if hwnd and user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return (
                    int((rect.left + rect.right) / 2),
                    int((rect.top + rect.bottom) / 2),
                )
        except Exception:
            pass
    widget.update_idletasks()
    return (
        widget.winfo_rootx() + max(1, widget.winfo_width()) // 2,
        widget.winfo_rooty() + max(1, widget.winfo_height()) // 2,
    )


def _notice_screen_position(workarea, notice_width, margin=24):
    left, top, right, _bottom = workarea
    return int((left + right - notice_width) / 2), int(top + margin)


def _screen_to_capture_point(screen_x, screen_y, virtual_bounds, capture_size):
    virtual_left, virtual_top, virtual_width, virtual_height = virtual_bounds
    capture_width, capture_height = capture_size
    x_ratio = capture_width / max(1, virtual_width)
    y_ratio = capture_height / max(1, virtual_height)
    return (
        int(round((screen_x - virtual_left) * x_ratio)),
        int(round((screen_y - virtual_top) * y_ratio)),
    )


def _focus_existing_popup(popup):
    try:
        if popup is None or not popup.winfo_exists():
            return False
        popup.deiconify()
        popup.lift()
        popup.focus_force()
        return True
    except Exception:
        return False


class ColorPickerDialog(tk.Toplevel):
    """Two-mode color picker with reusable color lists and saved colors."""

    def __init__(
        self,
        parent,
        title="Choose Color",
        initial_color="#1f77b4",
        palette_name="LAB×ACE² Thermal Gradient",
    ):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.result = None
        self.selected_color = _normalize_color(initial_color)
        self._syncing = False
        self._picker_hue = 0.0
        self._picker_saturation = 1.0
        self._picker_value = 1.0
        self._rendered_hue = None
        self._eyedropper_overlays = []
        self._eyedropper_notice = None
        self._eyedropper_workarea = None
        self.saved_colors = _load_saved_colors()

        self.title(title)
        self.configure(bg=POPUP_SURFACE_BG)
        self.resizable(False, False)
        self.transient(parent)

        palette_name = str(palette_name).replace("LABXACE2 Thermal", "LAB\u00d7ACE\u00b2 Thermal")
        self.palette_var = tk.StringVar(value=palette_name if palette_name in available_palette_names() else "LAB×ACE² Thermal Gradient")
        self.mode_var = tk.StringVar(value="Color Palette")
        self.status_var = tk.StringVar(value="")
        self.hex_var = tk.StringVar(value=self.selected_color.upper())
        self.r_var = tk.IntVar(value=0)
        self.g_var = tk.IntVar(value=0)
        self.b_var = tk.IntVar(value=0)

        self._build_ui(title)
        self._set_color(self.selected_color)
        self._render_palette()
        self._render_saved_colors()
        self._show_mode("Color Palette")

        self.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<Return>", lambda _e: self._ok())

        self.update_idletasks()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        self.after_idle(lambda: place_window_on_parent_monitor(self, parent, width, height))
        self.after(340, self._activate_dialog)

    def _activate_dialog(self):
        if not self.winfo_exists():
            return
        self.grab_set()
        self.focus_set()

    def _build_ui(self, title):
        card_bg = "#FFFFFF"
        text_color = "#202124"
        muted_color = "#5F6368"
        border_color = "#DADCE0"
        ui_font = ("Calibri", 10)
        ui_font_bold = ("Calibri", 10, "bold")
        self._card_bg = card_bg
        self._text_color = text_color
        self._muted_color = muted_color
        self._border_color = border_color
        self._ui_font = ui_font
        self._ui_font_bold = ui_font_bold

        scroll_host = tk.Frame(self, bg=POPUP_SURFACE_BG)
        scroll_host.pack(fill="both", expand=True)
        canvas = tk.Canvas(scroll_host, bg=POPUP_SURFACE_BG, highlightthickness=0, bd=0)
        scrollbar = RoundedScrollbar(
            scroll_host,
            orient="vertical",
            command=canvas.yview,
            bg=POPUP_SURFACE_BG,
        )
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        outer = tk.Frame(canvas, bg=POPUP_SURFACE_BG, padx=14, pady=14)
        canvas_window = canvas.create_window((0, 0), window=outer, anchor="nw")
        self._content_canvas = canvas
        self._content_outer = outer
        outer.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        self.bind(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
            add="+",
        )

        header = tk.Frame(outer, bg=POPUP_PRIMARY_BG)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(
            header,
            text=title,
            bg=POPUP_PRIMARY_BG,
            fg="#FFFFFF",
            font=("Calibri", 12, "bold"),
            anchor="w",
            padx=12,
            pady=9,
        ).pack(fill="x")

        top = tk.Frame(
            outer,
            bg=card_bg,
            highlightbackground=border_color,
            highlightthickness=1,
            bd=0,
            padx=11,
            pady=10,
        )
        top.pack(fill="x", pady=(0, 10))
        preview_box = tk.Frame(top, bg=card_bg)
        preview_box.pack(side="left", padx=(0, 14))
        tk.Label(
            preview_box,
            text="Selected",
            bg=card_bg,
            fg=muted_color,
            font=ui_font_bold,
            anchor="w",
        ).pack(fill="x", pady=(0, 5))
        self.preview = tk.Frame(
            preview_box,
            width=80,
            height=58,
            bg=self.selected_color,
            highlightbackground=border_color,
            highlightthickness=1,
            bd=0,
        )
        self.preview.pack(fill="x")
        self.preview.pack_propagate(False)

        edit_box = tk.Frame(top, bg=card_bg)
        edit_box.pack(side="left", fill="x", expand=True)
        edit_box.columnconfigure(1, weight=1)
        tk.Label(edit_box, text="HEX", bg=card_bg, fg=muted_color, font=ui_font).grid(row=0, column=0, sticky="w")
        ent_hex = tk.Entry(
            edit_box,
            textvariable=self.hex_var,
            width=12,
            font=ui_font,
            relief=tk.SOLID,
            bd=1,
            highlightthickness=0,
        )
        ent_hex.grid(row=0, column=1, sticky="w", padx=(6, 0))
        ent_hex.bind("<Return>", lambda _e: self._apply_hex())
        ent_hex.bind("<FocusOut>", lambda _e: self._apply_hex())

        self.rgb_labels = {}
        for row, (name, var) in enumerate((("R", self.r_var), ("G", self.g_var), ("B", self.b_var)), start=1):
            tk.Label(edit_box, text=name, bg=card_bg, fg=muted_color, font=ui_font).grid(row=row, column=0, sticky="w", pady=(4, 0))
            scale = ModernScale(
                edit_box,
                from_=0,
                to=255,
                resolution=1,
                orient="horizontal",
                variable=var,
                command=lambda _v: self._apply_rgb(),
                length=180,
                bg=card_bg,
                accent=POPUP_PRIMARY_BG,
                troughcolor=border_color,
            )
            scale.grid(row=row, column=1, sticky="ew", padx=(6, 6), pady=(4, 0))
            lbl = tk.Label(edit_box, text="000", width=3, bg=card_bg, fg=text_color, font=ui_font, anchor="e")
            lbl.grid(row=row, column=2, sticky="e", pady=(4, 0))
            self.rgb_labels[name] = lbl

        mode_bar = tk.Frame(outer, bg=POPUP_SURFACE_BG)
        mode_bar.pack(fill="x", pady=(0, 7))
        mode_bar.columnconfigure(0, weight=1, uniform="picker_modes")
        mode_bar.columnconfigure(1, weight=1, uniform="picker_modes")
        self.mode_buttons = {}
        for column, mode in enumerate(("Color Palette", "Color List")):
            button = tk.Button(
                mode_bar, text=mode, command=lambda name=mode: self._show_mode(name),
                font=ui_font_bold, relief="flat", bd=0, highlightthickness=0,
                pady=7, cursor="hand2",
            )
            button.grid(row=0, column=column, sticky="ew", padx=(0, 3 if column == 0 else 8))
            self.mode_buttons[mode] = button
        tk.Button(
            mode_bar, text="Color Picker", command=self._start_eyedropper,
            bg=POPUP_SECONDARY_BG, fg=text_color,
            activebackground=POPUP_SECONDARY_ACTIVE_BG, activeforeground=text_color,
            font=ui_font_bold, relief="flat", bd=0, highlightthickness=0,
            padx=9, pady=7, cursor="crosshair",
        ).grid(row=0, column=2, sticky="e", padx=(0, 4))
        tk.Button(
            mode_bar, text="Save Color", command=self._save_current_color,
            bg=POPUP_SECONDARY_BG, fg=text_color,
            activebackground=POPUP_SECONDARY_ACTIVE_BG, activeforeground=text_color,
            font=ui_font_bold, relief="flat", bd=0, highlightthickness=0,
            padx=9, pady=7, cursor="hand2",
        ).grid(row=0, column=3, sticky="e")

        mode_card = tk.Frame(
            outer, bg=card_bg, highlightbackground=border_color,
            highlightthickness=1, bd=0, padx=10, pady=9,
        )
        mode_card.pack(fill="x", pady=(0, 10))
        self.mode_pages = {
            "Color Palette": tk.Frame(mode_card, bg=card_bg),
            "Color List": tk.Frame(mode_card, bg=card_bg),
        }

        picker_page = self.mode_pages["Color Palette"]
        tk.Label(
            picker_page, text="Saturation / brightness", bg=card_bg,
            fg=muted_color, font=ui_font, anchor="w",
        ).pack(fill="x", pady=(0, 4))
        self.sv_canvas = tk.Canvas(
            picker_page, width=PICKER_WIDTH, height=PICKER_HEIGHT,
            bg="#FFFFFF", highlightbackground=border_color,
            highlightthickness=1, bd=0, cursor="crosshair",
        )
        self.sv_canvas.pack(fill="x")
        self.sv_canvas.bind("<Button-1>", self._pick_saturation_value)
        self.sv_canvas.bind("<B1-Motion>", self._pick_saturation_value)
        tk.Label(
            picker_page, text="Hue", bg=card_bg, fg=muted_color,
            font=ui_font, anchor="w",
        ).pack(fill="x", pady=(7, 3))
        self.hue_canvas = tk.Canvas(
            picker_page, width=PICKER_WIDTH, height=18,
            bg="#FFFFFF", highlightbackground=border_color,
            highlightthickness=1, bd=0, cursor="hand2",
        )
        self.hue_canvas.pack(fill="x")
        self.hue_canvas.bind("<Button-1>", self._pick_hue)
        self.hue_canvas.bind("<B1-Motion>", self._pick_hue)

        list_page = self.mode_pages["Color List"]
        pal_row = tk.Frame(list_page, bg=card_bg)
        pal_row.pack(fill="x", pady=(0, 7))
        tk.Label(pal_row, text="Color List", bg=card_bg, fg=text_color, font=ui_font_bold).pack(side="left")
        cmb = ttk.Combobox(
            pal_row, textvariable=self.palette_var,
            values=available_palette_names(), state="readonly", width=27,
        )
        cmb.pack(side="left", fill="x", expand=True, padx=(10, 0))
        cmb.bind("<<ComboboxSelected>>", lambda _e: self._render_palette())
        self.palette_frame = tk.Frame(list_page, bg=card_bg)
        self.palette_frame.pack(fill="x")

        saved_card = tk.Frame(
            outer, bg=card_bg, highlightbackground=border_color,
            highlightthickness=1, bd=0, padx=10, pady=8,
        )
        saved_card.pack(fill="x")
        saved_header = tk.Frame(saved_card, bg=card_bg)
        saved_header.pack(fill="x", pady=(0, 5))
        tk.Label(
            saved_header, text="Saved Colors", bg=card_bg, fg=text_color,
            font=ui_font_bold, anchor="w",
        ).pack(side="left")
        tk.Label(
            saved_header, text="Right-click to remove", bg=card_bg,
            fg=muted_color, font=("Calibri", 8), anchor="e",
        ).pack(side="right")
        self.saved_colors_frame = tk.Frame(saved_card, bg=card_bg)
        self.saved_colors_frame.pack(fill="x")

        tk.Label(
            outer, textvariable=self.status_var, bg=POPUP_SURFACE_BG,
            fg=muted_color, font=("Calibri", 9), anchor="w",
        ).pack(fill="x", pady=(7, 0))

        btn_row = tk.Frame(outer, bg=POPUP_SURFACE_BG)
        btn_row.pack(fill="x", pady=(12, 0))
        tk.Button(
            btn_row,
            text="Cancel",
            command=self._cancel,
            width=10,
            bg=POPUP_SECONDARY_BG,
            fg=text_color,
            activebackground=POPUP_SECONDARY_ACTIVE_BG,
            activeforeground=text_color,
            font=ui_font_bold,
            relief="flat",
            bd=0,
            highlightthickness=0,
            pady=6,
            cursor="hand2",
        ).pack(side="right", padx=(4, 0))
        tk.Button(
            btn_row,
            text="Apply",
            command=self._ok,
            width=10,
            bg=POPUP_PRIMARY_BG,
            fg="#FFFFFF",
            activebackground=POPUP_PRIMARY_ACTIVE_BG,
            activeforeground="#FFFFFF",
            font=ui_font_bold,
            relief="flat",
            bd=0,
            highlightthickness=0,
            pady=6,
            cursor="hand2",
        ).pack(side="right")

        self._fit_content_height()

    @staticmethod
    def _hsv_color(hue, saturation, value):
        red, green, blue = colorsys.hsv_to_rgb(
            max(0.0, min(1.0, float(hue))),
            max(0.0, min(1.0, float(saturation))),
            max(0.0, min(1.0, float(value))),
        )
        return _rgb_to_hex(round(red * 255), round(green * 255), round(blue * 255))

    def _show_mode(self, mode):
        if mode not in self.mode_pages:
            return
        self.mode_var.set(mode)
        for page in self.mode_pages.values():
            page.pack_forget()
        self.mode_pages[mode].pack(fill="x")
        for name, button in self.mode_buttons.items():
            selected = name == mode
            button.configure(
                bg=POPUP_PRIMARY_BG if selected else POPUP_SECONDARY_BG,
                fg="#FFFFFF" if selected else self._text_color,
                activebackground=POPUP_PRIMARY_ACTIVE_BG if selected else POPUP_SECONDARY_ACTIVE_BG,
                activeforeground="#FFFFFF" if selected else self._text_color,
            )
        if mode == "Color Palette":
            self._render_picker()
        self._fit_content_height()

    @staticmethod
    def _photo_from_rows(master, rows):
        height = len(rows)
        width = len(rows[0]) if rows else 1
        if Image is not None and ImageTk is not None:
            image = Image.new("RGB", (width, height))
            image.putdata([
                tuple(int(color[offset:offset + 2], 16) for offset in (1, 3, 5))
                for row in rows for color in row
            ])
            return ImageTk.PhotoImage(image, master=master)
        photo = tk.PhotoImage(master=master, width=width, height=height)
        for y, row in enumerate(rows):
            photo.put("{" + " ".join(row) + "}", to=(0, y))
        return photo

    def _render_picker(self):
        if not hasattr(self, "sv_canvas"):
            return
        hue_key = round(self._picker_hue, 4)
        if self._rendered_hue != hue_key:
            rows = []
            for y in range(PICKER_HEIGHT):
                value = 1.0 - (y / max(1, PICKER_HEIGHT - 1))
                rows.append([
                    self._hsv_color(
                        self._picker_hue,
                        x / max(1, PICKER_WIDTH - 1),
                        value,
                    )
                    for x in range(PICKER_WIDTH)
                ])
            self._sv_photo = self._photo_from_rows(self.sv_canvas, rows)
            self.sv_canvas.delete("gradient")
            self.sv_canvas.create_image(0, 0, image=self._sv_photo, anchor="nw", tags="gradient")
            self.sv_canvas.tag_lower("gradient")
            self._rendered_hue = hue_key

        if not hasattr(self, "_hue_photo"):
            hue_row = [
                self._hsv_color(x / max(1, PICKER_WIDTH - 1), 1.0, 1.0)
                for x in range(PICKER_WIDTH)
            ]
            self._hue_photo = self._photo_from_rows(
                self.hue_canvas, [hue_row for _ in range(18)]
            )
            self.hue_canvas.create_image(0, 0, image=self._hue_photo, anchor="nw", tags="gradient")

        self.sv_canvas.delete("marker")
        x = self._picker_saturation * (PICKER_WIDTH - 1)
        y = (1.0 - self._picker_value) * (PICKER_HEIGHT - 1)
        self.sv_canvas.create_oval(
            x - 6, y - 6, x + 6, y + 6,
            outline="#000000", width=3, tags="marker",
        )
        self.sv_canvas.create_oval(
            x - 5, y - 5, x + 5, y + 5,
            outline="#FFFFFF", width=2, tags="marker",
        )
        self.hue_canvas.delete("marker")
        hue_x = self._picker_hue * (PICKER_WIDTH - 1)
        self.hue_canvas.create_line(
            hue_x, 0, hue_x, 18, fill="#FFFFFF", width=3, tags="marker",
        )
        self.hue_canvas.create_line(
            hue_x - 1, 0, hue_x - 1, 18, fill="#202124", width=1, tags="marker",
        )
        self.hue_canvas.create_line(
            hue_x + 1, 0, hue_x + 1, 18, fill="#202124", width=1, tags="marker",
        )

    def _pick_saturation_value(self, event):
        self._picker_saturation = max(0.0, min(1.0, event.x / max(1, PICKER_WIDTH - 1)))
        self._picker_value = 1.0 - max(0.0, min(1.0, event.y / max(1, PICKER_HEIGHT - 1)))
        self._set_color(self._hsv_color(
            self._picker_hue, self._picker_saturation, self._picker_value,
        ))

    def _pick_hue(self, event):
        self._picker_hue = max(0.0, min(1.0, event.x / max(1, PICKER_WIDTH - 1)))
        self._rendered_hue = None
        self._set_color(self._hsv_color(
            self._picker_hue, self._picker_saturation, self._picker_value,
        ))

    def _render_saved_colors(self):
        frame = getattr(self, "saved_colors_frame", None)
        if frame is None:
            return
        for child in frame.winfo_children():
            child.destroy()
        if not self.saved_colors:
            tk.Label(
                frame, text="No saved colors yet.", bg=self._card_bg,
                fg=self._muted_color, font=self._ui_font, anchor="w",
            ).pack(fill="x", pady=3)
            return
        for index, color in enumerate(self.saved_colors):
            button = tk.Button(
                frame, bg=color, activebackground=color, relief="flat", bd=0,
                highlightbackground="#FFFFFF", highlightthickness=1,
                width=3, height=1, cursor="hand2",
                command=lambda value=color: self._set_color(value),
            )
            button.grid(row=index // 9, column=index % 9, padx=2, pady=2, sticky="ew")
            button.bind(
                "<Button-3>",
                lambda _event, value=color: self._remove_saved_color(value),
            )
        for column in range(9):
            frame.columnconfigure(column, weight=1)

    def _save_current_color(self):
        color = _normalize_color(self.selected_color)
        self.saved_colors = [
            color,
            *[saved for saved in self.saved_colors if saved != color],
        ][:MAX_SAVED_COLORS]
        if _store_saved_colors(self.saved_colors):
            self.status_var.set(f"Saved {color.upper()}.")
        else:
            self.status_var.set("The color could not be saved to disk.")
        self._render_saved_colors()
        self._fit_content_height()

    def _remove_saved_color(self, color):
        self.saved_colors = [saved for saved in self.saved_colors if saved != color]
        _store_saved_colors(self.saved_colors)
        self._render_saved_colors()
        self.status_var.set(f"Removed {color.upper()} from Saved Colors.")
        self._fit_content_height()

    def _start_eyedropper(self):
        if ImageGrab is None:
            self.status_var.set("Color Picker requires Pillow screen capture support.")
            return
        self.status_var.set("Click anywhere on the screen to sample a color. Press Esc to cancel.")
        center_x, center_y = _window_center_in_physical_pixels(self)
        self._eyedropper_workarea = monitor_workarea_for_point(
            center_x, center_y, self,
        )
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.withdraw()
        self.after(140, self._open_eyedropper_overlay)

    def _open_eyedropper_overlay(self):
        if not self.winfo_exists():
            return
        try:
            try:
                screenshot = ImageGrab.grab(all_screens=True)
            except TypeError:
                screenshot = ImageGrab.grab()
        except Exception:
            self._restore_after_eyedropper("The screen color could not be captured.")
            return

        virtual_bounds = _virtual_screen_bounds(self)
        self._eyedropper_overlays = []
        active_overlay = None
        workarea = self._eyedropper_workarea or monitor_workarea_for_point(
            self.winfo_pointerx(), self.winfo_pointery(), self,
        )
        work_center_x = int((workarea[0] + workarea[2]) / 2)
        work_center_y = int((workarea[1] + workarea[3]) / 2)

        for monitor_left, monitor_top, monitor_right, monitor_bottom in _monitor_bounds(self):
            monitor_width = max(1, monitor_right - monitor_left)
            monitor_height = max(1, monitor_bottom - monitor_top)
            overlay = tk.Toplevel(self.parent)
            overlay.overrideredirect(True)
            overlay.configure(bg="#000000", cursor="crosshair")
            overlay.geometry(
                f"{monitor_width}x{monitor_height}{monitor_left:+d}{monitor_top:+d}"
            )
            overlay.attributes("-topmost", True)
            # A nearly invisible, non-color-keyed window still receives mouse
            # events. Color-key transparency can become click-through on a
            # secondary Windows monitor.
            overlay.attributes("-alpha", 0.01)
            overlay.bind(
                "<Button-1>",
                lambda event, origin_x=monitor_left, origin_y=monitor_top: self._finish_eyedropper(
                    screenshot,
                    origin_x + event.x,
                    origin_y + event.y,
                    virtual_bounds,
                ),
            )
            overlay.bind(
                "<Escape>",
                lambda _event: self._restore_after_eyedropper("Color Picker cancelled."),
            )
            self._eyedropper_overlays.append(overlay)
            if monitor_left <= work_center_x < monitor_right and monitor_top <= work_center_y < monitor_bottom:
                active_overlay = overlay

        notice = tk.Toplevel(self.parent)
        self._eyedropper_notice = notice
        notice.withdraw()
        notice.overrideredirect(True)
        notice.configure(bg="#202124")
        notice.attributes("-topmost", True)
        tk.Label(
            notice,
            text="COLOR PICKER  •  Click anywhere on the screen to pick a color  •  Esc to cancel",
            bg="#202124", fg="#FFFFFF", font=("Calibri", 11, "bold"),
            padx=16, pady=9, bd=0,
        ).pack()
        notice.update_idletasks()
        notice_x, notice_y = _notice_screen_position(
            workarea, notice.winfo_reqwidth(),
        )
        notice.geometry(
            f"{notice.winfo_reqwidth()}x{notice.winfo_reqheight()}{notice_x:+d}{notice_y:+d}"
        )
        notice.deiconify()
        notice.lift()

        focus_overlay = active_overlay or (self._eyedropper_overlays[0] if self._eyedropper_overlays else None)
        if focus_overlay is not None:
            focus_overlay.lift()
            notice.lift()
            focus_overlay.focus_force()

    def _finish_eyedropper(self, screenshot, screen_x, screen_y, virtual_bounds):
        pixel_x, pixel_y = _screen_to_capture_point(
            screen_x, screen_y, virtual_bounds, screenshot.size,
        )
        try:
            pixel = screenshot.getpixel((pixel_x, pixel_y))
            if isinstance(pixel, int):
                red = green = blue = pixel
            else:
                red, green, blue = pixel[:3]
            color = _rgb_to_hex(red, green, blue)
        except Exception:
            self._restore_after_eyedropper("The selected pixel is outside the captured screen.")
            return
        self._restore_after_eyedropper(f"Sampled {color.upper()}.")
        self._set_color(color)

    def _restore_after_eyedropper(self, message=""):
        overlays = self._eyedropper_overlays
        self._eyedropper_overlays = []
        for overlay in overlays:
            try:
                overlay.destroy()
            except tk.TclError:
                pass
        notice = self._eyedropper_notice
        self._eyedropper_notice = None
        if notice is not None:
            try:
                notice.destroy()
            except tk.TclError:
                pass
        if self.winfo_exists():
            self.deiconify()
            self.lift()
            self.focus_force()
            self.grab_set()
            self.status_var.set(message)

    def _fit_content_height(self):
        """Resize the viewport after dynamic palette buttons are populated."""
        outer = getattr(self, "_content_outer", None)
        canvas = getattr(self, "_content_canvas", None)
        if outer is None or canvas is None:
            return
        outer.update_idletasks()
        canvas.configure(
            width=outer.winfo_reqwidth(),
            height=outer.winfo_reqheight() + 48,
        )

    def _render_palette(self):
        for child in self.palette_frame.winfo_children():
            child.destroy()
        colors = get_palette_colors(self.palette_var.get(), 40)
        for idx, color in enumerate(colors):
            color = _normalize_color(color, "#1f77b4")
            btn = tk.Button(
                self.palette_frame,
                bg=color,
                activebackground=color,
                relief="flat",
                bd=0,
                highlightbackground="#FFFFFF",
                highlightthickness=1,
                width=3,
                height=1,
                cursor="hand2",
                command=lambda c=color: self._set_color(c),
            )
            btn.grid(row=idx // 10, column=idx % 10, padx=2, pady=2, sticky="ew")
        for col in range(10):
            self.palette_frame.columnconfigure(col, weight=1)
        self._fit_content_height()

    def _set_color(self, color):
        color = _normalize_color(color, self.selected_color)
        self.selected_color = color
        r, g, b = [int(round(v * 255)) for v in to_rgb(color)]
        self._syncing = True
        try:
            self.r_var.set(r)
            self.g_var.set(g)
            self.b_var.set(b)
            self.hex_var.set(color.upper())
            self.preview.configure(bg=color)
            self.rgb_labels["R"].configure(text=f"{r:03d}")
            self.rgb_labels["G"].configure(text=f"{g:03d}")
            self.rgb_labels["B"].configure(text=f"{b:03d}")
            hue, saturation, value = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if saturation > 0.001:
                if abs(hue - self._picker_hue) > 0.0005:
                    self._rendered_hue = None
                self._picker_hue = hue
            self._picker_saturation = saturation
            self._picker_value = value
            self._render_picker()
        finally:
            self._syncing = False

    def _apply_rgb(self):
        if self._syncing:
            return
        color = _rgb_to_hex(self.r_var.get(), self.g_var.get(), self.b_var.get())
        self._set_color(color)

    def _apply_hex(self):
        value = self.hex_var.get().strip()
        if not HEX_RE.match(value):
            self.hex_var.set(self.selected_color.upper())
            return
        if not value.startswith("#"):
            value = "#" + value
        self._set_color(value)

    def _ok(self):
        self.result = self.selected_color
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


def choose_color(parent, title="Choose Color", initial_color="#1f77b4", palette_name="LAB×ACE² Thermal Gradient"):
    host = parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent
    popup_attr = "_xrd_active_value_popup"
    existing = getattr(host, popup_attr, None)
    if _focus_existing_popup(existing):
        return None

    dialog = ColorPickerDialog(parent, title=title, initial_color=initial_color, palette_name=palette_name)
    setattr(host, popup_attr, dialog)
    try:
        parent.wait_window(dialog)
        return dialog.result
    finally:
        if getattr(host, popup_attr, None) is dialog:
            setattr(host, popup_attr, None)
