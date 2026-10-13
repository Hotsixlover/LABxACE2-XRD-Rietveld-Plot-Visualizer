# SPDX-License-Identifier: GPL-2.0-or-later
import os
import platform

import matplotlib as mpl
from matplotlib import font_manager


PREFERRED_FONT_SPECS = [
    ("Calibri", ["calibri.ttf"], "Calibri", "normal"),
    ("Calibri Light", ["calibril.ttf"], "Calibri", "light"),
    ("Aptos", ["aptos.ttf"], "Aptos", "normal"),
    ("Aptos Display", ["aptosdisplay.ttf"], "Aptos Display", "normal"),
    ("Arial", ["arial.ttf"], "Arial", "normal"),
    ("Times New Roman", ["times.ttf"], "Times New Roman", "normal"),
    ("Cambria", ["cambria.ttc", "cambria.ttf"], "Cambria", "normal"),
    ("Georgia", ["georgia.ttf"], "Georgia", "normal"),
    ("Segoe UI", ["segoeui.ttf"], "Segoe UI", "normal"),
    ("Tahoma", ["tahoma.ttf"], "Tahoma", "normal"),
    ("Verdana", ["verdana.ttf"], "Verdana", "normal"),
    ("Malgun Gothic", ["malgun.ttf"], "Malgun Gothic", "normal"),
    ("DejaVu Sans", [], "DejaVu Sans", "normal"),
    ("DejaVu Serif", [], "DejaVu Serif", "normal"),
]


def _font_dirs():
    dirs = []
    if platform.system() == "Windows":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        dirs.append(os.path.join(windir, "Fonts"))
    dirs.extend(font_manager.get_fontconfig_fonts() if hasattr(font_manager, "get_fontconfig_fonts") else [])
    return dirs


def _find_font_file(filenames):
    wanted = {name.lower() for name in filenames}
    if not wanted:
        return None
    for font_dir in _font_dirs():
        if not isinstance(font_dir, str) or not os.path.isdir(font_dir):
            continue
        try:
            for name in os.listdir(font_dir):
                if name.lower() in wanted:
                    return os.path.join(font_dir, name)
        except Exception:
            continue
    for path in font_manager.findSystemFonts():
        if os.path.basename(path).lower() in wanted:
            return path
    return None


def _resolve_family(family_name, weight="normal"):
    try:
        prop = font_manager.FontProperties(family=family_name, weight=weight)
        return font_manager.findfont(prop, fallback_to_default=False)
    except Exception:
        return None


def build_font_registry():
    registry = {}
    for display, filenames, family, base_weight in PREFERRED_FONT_SPECS:
        path = _find_font_file(filenames)
        if path is None:
            path = _resolve_family(family, base_weight)
        if path:
            registry[display] = {
                "display": display,
                "family": family,
                "path": path,
                "base_weight": base_weight,
            }

    # DejaVu is bundled with Matplotlib, so keep a guaranteed fallback.
    if "DejaVu Sans" not in registry:
        registry["DejaVu Sans"] = {
            "display": "DejaVu Sans",
            "family": "DejaVu Sans",
            "path": font_manager.findfont("DejaVu Sans"),
            "base_weight": "normal",
        }
    return registry


FONT_REGISTRY = build_font_registry()


def available_plot_fonts():
    preferred = [name for name, *_rest in PREFERRED_FONT_SPECS if name in FONT_REGISTRY]
    extras = sorted(name for name in FONT_REGISTRY if name not in preferred)
    return preferred + extras


def get_font_spec(display_name=None):
    if display_name in FONT_REGISTRY:
        return FONT_REGISTRY[display_name]
    if "Calibri" in FONT_REGISTRY:
        return FONT_REGISTRY["Calibri"]
    if "Calibri Light" in FONT_REGISTRY:
        return FONT_REGISTRY["Calibri Light"]
    return FONT_REGISTRY["DejaVu Sans"]


def configure_style():
    spec = get_font_spec("Calibri")
    mpl.rcParams["font.family"] = spec["family"]
    mpl.rcParams["font.sans-serif"] = [spec["family"], "Calibri", "Arial", "DejaVu Sans"]
    mpl.rcParams["font.weight"] = spec["base_weight"]
    mpl.rcParams["axes.labelweight"] = spec["base_weight"]
    mpl.rcParams["axes.titleweight"] = spec["base_weight"]
    mpl.rcParams["mathtext.fontset"] = "custom"
    mpl.rcParams["mathtext.rm"] = spec["family"]
    mpl.rcParams["mathtext.it"] = f"{spec['family']}:italic"
    mpl.rcParams["mathtext.bf"] = f"{spec['family']}:bold"
    mpl.rcParams["pdf.fonttype"] = 42
    mpl.rcParams["ps.fonttype"] = 42
    mpl.rcParams["svg.fonttype"] = "none"
    mpl.rc("axes", unicode_minus=False)
    mpl.rcParams["mathtext.default"] = "regular"
    return spec["display"], spec["family"], spec["base_weight"], spec["path"]


ACTIVE_PLOT_FONT_DISPLAY, ACTIVE_PLOT_FONT_FAMILY, ACTIVE_PLOT_BASE_WEIGHT, ACTIVE_PLOT_FONT_PATH = configure_style()
