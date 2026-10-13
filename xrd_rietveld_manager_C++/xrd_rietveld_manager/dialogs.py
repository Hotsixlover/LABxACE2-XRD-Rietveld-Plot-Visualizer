# SPDX-License-Identifier: GPL-2.0-or-later
import tkinter as tk
from tkinter import ttk, messagebox

from xrd_rietveld_manager.popup_utils import (
    POPUP_PRIMARY_ACTIVE_BG,
    POPUP_PRIMARY_BG,
    POPUP_SECONDARY_ACTIVE_BG,
    POPUP_SECONDARY_BG,
    POPUP_SURFACE_BG,
    place_window_on_parent_monitor,
)
from xrd_rietveld_manager.ui2_widgets import RoundedScrollbar


class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        bg = kwargs.pop("bg", "#ffffff")
        super().__init__(container, *args, bg=bg, **kwargs)
        self.canvas = tk.Canvas(self, width=1, bg=bg, highlightthickness=0)
        self.scrollbar = RoundedScrollbar(self, orient="vertical", command=self.canvas.yview, bg=bg)
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg)
        self.scrollable_frame.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)


def _primary_button(master, text, command, **kwargs):
    return tk.Button(
        master, text=text, command=command, bg=POPUP_PRIMARY_BG, fg="#ffffff",
        activebackground=POPUP_PRIMARY_ACTIVE_BG, activeforeground="#ffffff",
        relief="flat", bd=0, highlightthickness=0, pady=5, cursor="hand2", **kwargs
    )


def _secondary_button(master, text, command, **kwargs):
    return tk.Button(
        master, text=text, command=command, bg=POPUP_SECONDARY_BG, fg="#3c4043",
        activebackground=POPUP_SECONDARY_ACTIVE_BG, activeforeground="#202124",
        relief="flat", bd=0, highlightthickness=0, pady=5, cursor="hand2", **kwargs
    )


class RichLabelEditDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_value, callback):
        super().__init__(parent)
        self.withdraw()
        host = parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent
        popup_attr = "_xrd_active_value_popup"
        existing = getattr(host, popup_attr, None)
        try:
            existing_open = existing is not None and existing.winfo_exists()
        except Exception:
            existing_open = False
        if existing_open:
            self.destroy()
            try:
                existing.deiconify()
                existing.lift()
                existing.focus_force()
            except Exception:
                pass
            return

        setattr(host, popup_attr, self)

        def clear_popup_slot(event=None):
            if event is not None and event.widget is not self:
                return
            if getattr(host, popup_attr, None) is self:
                setattr(host, popup_attr, None)

        self.bind("<Destroy>", clear_popup_slot, add="+")
        self.callback = callback
        self.title(title)
        self.configure(bg=POPUP_SURFACE_BG)
        self.after_idle(lambda: place_window_on_parent_monitor(self, parent, 350, 150))

        tk.Label(
            self, text="New Label (Ctrl+=: Sub, Ctrl+-: Sup):",
            bg=POPUP_SURFACE_BG, fg="#202124"
        ).pack(pady=5)
        self.entry = tk.Entry(self, width=40)
        self.entry.insert(0, initial_value)
        self.entry.pack(pady=5)
        self.after(340, lambda: self.entry.focus_set() if self.entry.winfo_exists() else None)
        self.entry.bind("<Control-equal>", self._insert_sub)
        self.entry.bind("<Control-minus>", self._insert_sup)
        self.bind("<Return>", self._on_ok)

        buttons = tk.Frame(self, bg=POPUP_SURFACE_BG)
        buttons.pack(pady=10)
        _primary_button(buttons, "OK", self._on_ok, width=10).pack(side="left", padx=5)
        _secondary_button(buttons, "Cancel", self.destroy, width=10).pack(side="left")

    def _insert_sub(self, _event):
        self.entry.insert(tk.INSERT, "_{}")
        self.entry.icursor(self.entry.index(tk.INSERT) - 1)
        return "break"

    def _insert_sup(self, _event):
        self.entry.insert(tk.INSERT, "^{}")
        self.entry.icursor(self.entry.index(tk.INSERT) - 1)
        return "break"

    def _on_ok(self, _event=None):
        if self.callback:
            self.callback(self.entry.get())
        self.destroy()


class StyleDialog(tk.Toplevel):
    def __init__(self, parent, target_name, current_settings, callback):
        super().__init__(parent)
        self.withdraw()
        self.settings = current_settings.copy()
        self.callback = callback
        self.title(f"Style: {target_name}")
        self.configure(bg=POPUP_SURFACE_BG)
        self.after_idle(lambda: place_window_on_parent_monitor(self, parent, 300, 300))

        frame = tk.Frame(self, bg=POPUP_SURFACE_BG, padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(1, weight=1)
        tk.Label(frame, text="View Mode:", bg=POPUP_SURFACE_BG, fg="#202124").grid(row=0, column=0, sticky="w", pady=5)
        self.mode = tk.StringVar(value=self.settings.get("mode", "line"))
        ttk.Combobox(frame, textvariable=self.mode, values=["line", "symbol", "both"], state="readonly").grid(row=0, column=1, sticky="ew")

        tk.Label(frame, text="Line Width:", bg=POPUP_SURFACE_BG, fg="#202124").grid(row=1, column=0, sticky="w", pady=5)
        self.width = tk.Scale(frame, from_=0.1, to=5.0, resolution=0.1, orient="horizontal", bg=POPUP_SURFACE_BG, highlightthickness=0)
        self.width.set(self.settings.get("linewidth", 1.0))
        self.width.grid(row=1, column=1, sticky="ew")

        tk.Label(frame, text="Symbol Size:", bg=POPUP_SURFACE_BG, fg="#202124").grid(row=2, column=0, sticky="w", pady=5)
        self.size = tk.Scale(frame, from_=1, to=15, orient="horizontal", bg=POPUP_SURFACE_BG, highlightthickness=0)
        self.size.set(self.settings.get("size", 3))
        self.size.grid(row=2, column=1, sticky="ew")
        _primary_button(self, "Apply", self._apply, padx=18).pack(pady=10)

    def _apply(self):
        self.settings["mode"] = self.mode.get()
        self.settings["linewidth"] = self.width.get()
        self.settings["size"] = self.size.get()
        self.callback(self.settings)
        self.destroy()


class SplitTitlesDialog(tk.Toplevel):
    def __init__(self, parent, rows, main_overrides, diff_overrides, main_size_overrides,
                 diff_size_overrides, default_main_size, default_diff_size, callback):
        super().__init__(parent)
        self.withdraw()
        self.callback = callback
        self.rows = rows
        self.main_vars, self.diff_vars = {}, {}
        self.main_size_vars, self.diff_size_vars = {}, {}
        self.default_main_size = int(default_main_size)
        self.default_diff_size = int(default_diff_size)
        self.title("Edit Split Titles")
        self.configure(bg=POPUP_SURFACE_BG)
        self.after_idle(lambda: place_window_on_parent_monitor(self, parent, 940, 520))

        tk.Label(
            self, text="Leave title blank to use auto title. Leave size blank to use defaults.",
            anchor="w", bg=POPUP_SURFACE_BG, fg="#202124"
        ).pack(fill="x", padx=10, pady=(8, 4))
        header = tk.Frame(self, bg=POPUP_SURFACE_BG)
        header.pack(fill="x", padx=10)
        for text, width, padding in (
            ("File", 26, (0, 0)), ("Main Title", 24, (6, 4)),
            ("Main Size", 9, (2, 8)), ("Difference Title", 24, (6, 4)),
            ("Diff Size", 9, (0, 0)),
        ):
            tk.Label(
                header, text=text, width=width, anchor="w", font=("Arial", 9, "bold"),
                bg=POPUP_SURFACE_BG, fg="#202124"
            ).pack(side="left", padx=padding)

        sc = ScrollableFrame(self, bg=POPUP_SURFACE_BG)
        sc.pack(fill="both", expand=True, padx=10, pady=6)
        for filepath, display in rows:
            row = tk.Frame(sc.scrollable_frame, bg=POPUP_SURFACE_BG, pady=2)
            row.pack(fill="x")
            tk.Label(row, text=display, anchor="w", width=26, bg=POPUP_SURFACE_BG, fg="#3c4043").pack(side="left")
            main_var = tk.StringVar(value=main_overrides.get(filepath, ""))
            self.main_vars[filepath] = main_var
            tk.Entry(row, textvariable=main_var, width=28).pack(side="left", padx=(6, 4))
            main_size_var = tk.StringVar(value=str(main_size_overrides.get(filepath, "")))
            self.main_size_vars[filepath] = main_size_var
            tk.Entry(row, textvariable=main_size_var, width=8).pack(side="left", padx=(2, 8))
            diff_var = tk.StringVar(value=diff_overrides.get(filepath, ""))
            self.diff_vars[filepath] = diff_var
            tk.Entry(row, textvariable=diff_var, width=28).pack(side="left", padx=(6, 4))
            diff_size_var = tk.StringVar(value=str(diff_size_overrides.get(filepath, "")))
            self.diff_size_vars[filepath] = diff_size_var
            tk.Entry(row, textvariable=diff_size_var, width=8).pack(side="left")

        buttons = tk.Frame(self, bg=POPUP_SURFACE_BG)
        buttons.pack(fill="x", padx=10, pady=8)
        _primary_button(buttons, "Apply", self._on_apply, width=12).pack(side="right")
        _secondary_button(buttons, "Cancel", self.destroy, width=12).pack(side="right", padx=6)

    def _on_apply(self):
        main_map = {k: v.get().strip() for k, v in self.main_vars.items() if v.get().strip()}
        diff_map = {k: v.get().strip() for k, v in self.diff_vars.items() if v.get().strip()}
        main_size_map, diff_size_map = {}, {}
        for key, var in self.main_size_vars.items():
            text = var.get().strip()
            if not text:
                continue
            try:
                value = int(text)
                if value <= 0:
                    raise ValueError
                main_size_map[key] = value
            except ValueError:
                messagebox.showerror("Error", f"Invalid Main Size for: {key}\nUse a positive integer.", parent=self)
                return
        for key, var in self.diff_size_vars.items():
            text = var.get().strip()
            if not text:
                continue
            try:
                value = int(text)
                if value <= 0:
                    raise ValueError
                diff_size_map[key] = value
            except ValueError:
                messagebox.showerror("Error", f"Invalid Diff Size for: {key}\nUse a positive integer.", parent=self)
                return
        if self.callback:
            self.callback(main_map, diff_map, main_size_map, diff_size_map)
        self.destroy()
