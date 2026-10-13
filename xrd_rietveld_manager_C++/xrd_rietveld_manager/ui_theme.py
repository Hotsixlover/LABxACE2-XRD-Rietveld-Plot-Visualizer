# SPDX-License-Identifier: GPL-2.0-or-later
"""Visual system for LAB×ACE²-XRD Rietveld Plot Visualizer.

This module deliberately contains presentation only. Plotting, project state,
Figure Set rendering, and reference-pattern calculations remain owned by the
modular application.
"""


LABXACE2_UI_THEME = {
    "bg": "#F8F9FA",
    "panel": "#FFFFFF",
    "surface": "#FFFFFF",
    "canvas_bg": "#F2F4F7",
    "text": "#202124",
    "muted": "#5F6368",
    "border": "#DADCE0",
    "accent": "#4285F4",
    "accent_alt": "#3F73D8",
    "accent_deep": "#3367D6",
    "accent_soft": "#E8F0FE",
    "warning": "#E37400",
    "danger": "#C5221F",
    "button_dark": "#3C4043",
    "button_mid": "#6B7280",
    "button_light": "#F1F3F4",
    "tab_idle": "#EEF3FB",
    "tab_active": "#E8F0FE",
    "tab_selected": "#FFFFFF",
    "disabled_bg": "#F1F3F4",
    "disabled_text": "#9AA0A6",
    "focus_border": "#A8C7FA",
}


def _configure_ttk_styles(style, theme):
    style.configure("TFrame", background=theme["panel"])
    style.configure("TLabel", background=theme["panel"], foreground=theme["text"])
    style.configure("TLabelframe", background=theme["panel"], bordercolor=theme["border"], relief="flat")
    style.configure("TLabelframe.Label", background=theme["panel"], foreground=theme["text"], font=("Calibri", 10, "bold"))
    style.configure("TNotebook", background=theme["bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        font=("Calibri", 10, "bold"),
        padding=(10, 6),
        background=theme["tab_idle"],
        foreground=theme["muted"],
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", theme["tab_selected"]), ("active", theme["tab_active"])],
        foreground=[("selected", theme["accent"]), ("active", theme["muted"])],
    )
    style.configure(
        "Treeview",
        background=theme["surface"], fieldbackground=theme["surface"],
        foreground=theme["muted"], bordercolor=theme["border"],
        lightcolor=theme["border"], darkcolor=theme["border"],
        rowheight=25, relief="flat",
    )
    style.map("Treeview", background=[("selected", theme["accent_soft"])], foreground=[("selected", theme["text"])])
    style.configure("Treeview.Heading", background=theme["bg"], foreground=theme["muted"], font=("Calibri", 10, "bold"), relief="flat")
    style.map("Treeview.Heading", background=[("active", theme["tab_idle"])])
    style.configure(
        "TCombobox", fieldbackground=theme["surface"], background=theme["surface"],
        foreground=theme["text"], arrowcolor=theme["accent"],
        bordercolor="#C9CFD6", lightcolor=theme["surface"], darkcolor=theme["surface"],
        selectbackground=theme["accent_soft"], selectforeground=theme["text"],
        borderwidth=1, relief="flat", padding=(7, 4), arrowsize=9,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("disabled", theme["disabled_bg"]), ("readonly", theme["surface"])],
        foreground=[("disabled", theme["disabled_text"]), ("readonly", theme["text"])],
        arrowcolor=[("disabled", theme["disabled_text"]), ("readonly", theme["accent"])],
        bordercolor=[("focus", theme["accent"]), ("readonly", "#C9CFD6")],
    )
    style.configure("TScrollbar", background="#C7C9CC", troughcolor=theme["surface"], bordercolor=theme["surface"], arrowcolor=theme["muted"], relief="flat")
    style.configure("UI2.TButton", background=theme["button_light"], foreground=theme["text"], borderwidth=0, padding=(9, 5), font=("Calibri", 10))
    style.map("UI2.TButton", background=[("active", theme["tab_active"]), ("pressed", theme["accent_soft"])])
    style.configure("UI2.Accent.TButton", background=theme["accent"], foreground="#FFFFFF", borderwidth=0, padding=(10, 6), font=("Calibri", 10, "bold"))
    style.map("UI2.Accent.TButton", background=[("active", theme["accent_deep"]), ("pressed", theme["accent_deep"])])


def apply_labxace_theme(root, style, theme=None):
    """Apply the UI2 light material skin to existing and future widgets."""
    theme = theme or LABXACE2_UI_THEME
    root.configure(bg=theme["bg"])
    root.option_add("*Font", "Calibri 10")
    root.option_add("*Background", theme["panel"])
    root.option_add("*Foreground", theme["text"])
    root.option_add("*activeBackground", theme["tab_active"])
    root.option_add("*activeForeground", theme["text"])
    root.option_add("*highlightBackground", theme["border"])
    root.option_add("*highlightColor", theme["focus_border"])
    root.option_add("*selectBackground", theme["accent_soft"])
    root.option_add("*selectForeground", theme["text"])
    root.option_add("*TCombobox*Listbox.background", theme["surface"])
    root.option_add("*TCombobox*Listbox.foreground", theme["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", theme["accent_soft"])
    root.option_add("*TCombobox*Listbox.selectForeground", theme["text"])
    _configure_ttk_styles(style, theme)
