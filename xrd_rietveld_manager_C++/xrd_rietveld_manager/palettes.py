# SPDX-License-Identifier: GPL-2.0-or-later
from matplotlib import colormaps
from matplotlib.colors import LinearSegmentedColormap, to_hex

try:
    import colorcet as cc
except Exception:
    cc = None

try:
    import cmasher as cmr
except Exception:
    cmr = None


BUILTIN_ART_PALETTES = {
    "Journal Muted": [
        "#2F4858", "#F26419", "#33658A", "#86BBD8", "#758E4F",
        "#F6AE2D", "#7A5195", "#EF5675", "#00A6A6", "#58508D",
    ],
    "Mineral Earth": [
        "#344E41", "#A3B18A", "#DDA15E", "#BC6C25", "#606C38",
        "#283618", "#8D99AE", "#B56576", "#6D597A", "#355070",
    ],
    "Clean Contrast": [
        "#111827", "#2563EB", "#DC2626", "#059669", "#D97706",
        "#7C3AED", "#0891B2", "#DB2777", "#65A30D", "#4B5563",
    ],
    "Soft Origin": [
        "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
        "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
    ],
    "Editorial Ink": [
        "#17202A", "#0E7C7B", "#D95D39", "#2E5EAA", "#8A5A83",
        "#B38600", "#2D936C", "#A23E48", "#4A6670", "#111827",
    ],
    "Ceramic Pastel": [
        "#315C73", "#88A2AA", "#BFD7B5", "#F2CC8F", "#E07A5F",
        "#81717A", "#6D597A", "#99C1B9", "#F4A261", "#457B9D",
    ],
    "Anodized Spectrum": [
        "#073B4C", "#118AB2", "#06D6A0", "#FFD166", "#EF476F",
        "#7209B7", "#3A86FF", "#FB5607", "#8338EC", "#0B525B",
    ],
    "Museum Glass": [
        "#143642", "#0F8B8D", "#EC9A29", "#A8201A", "#5C415D",
        "#1B998B", "#2D3047", "#FFFD82", "#FF9B71", "#456990",
    ],
}


GRADIENT_ART_PALETTES = {
    "LAB×ACE² Thermal Gradient": ["#243B53", "#2F80ED", "#27AE60", "#F2C94C", "#EB5757"],
    "LAB×ACE² Thermal Vivid": ["#0033CC", "#0066FF", "#00B8FF", "#00C853", "#FFD600", "#FF8C00", "#E60012"],
    "Origin Temperature Gradient": ["#234B9A", "#00A6D6", "#6CC24A", "#F4C430", "#D7263D"],
    "Deep Ocean Gradient": ["#081C24", "#0B525B", "#1B998B", "#80ED99", "#F9F7F3"],
    "Sunset Alloy Gradient": ["#231942", "#5E548E", "#E56B6F", "#F4A261", "#FFD166"],
    "Graphite Ember Gradient": ["#111827", "#374151", "#B45309", "#F59E0B", "#FDE68A"],
    "Blue Steel Gradient": ["#0B132B", "#1C2541", "#3A506B", "#5BC0BE", "#CDEDF6"],
}


def available_palette_names():
    names = list(BUILTIN_ART_PALETTES)
    names.extend(GRADIENT_ART_PALETTES)
    if cc is not None:
        names.extend(["Colorcet Glasbey", "Colorcet Fire"])
    if cmr is not None:
        names.extend(["CMasher Gem", "CMasher Rainforest"])
    names.extend(["Matplotlib Viridis", "Matplotlib Plasma", "Matplotlib Tab20"])
    return names


def _sample_cmap(cmap_name, count):
    count = max(1, int(count))
    cmap = colormaps.get_cmap(cmap_name)
    if count == 1:
        return [to_hex(cmap(0.55))]
    return [to_hex(cmap(i / max(count - 1, 1))) for i in range(count)]


def _sample_gradient(stops, count):
    count = max(1, int(count))
    cmap = LinearSegmentedColormap.from_list("labxace2_custom_gradient", stops)
    if count == 1:
        return [to_hex(cmap(0.5))]
    return [to_hex(cmap(i / max(count - 1, 1))) for i in range(count)]


def get_palette_colors(name, count):
    # Accept palette names from templates saved before the product rename.
    name = str(name).replace("LABXACE2 Thermal", "LAB\u00d7ACE\u00b2 Thermal")
    count = max(1, int(count))
    if name in BUILTIN_ART_PALETTES:
        base = BUILTIN_ART_PALETTES[name]
        return [base[i % len(base)] for i in range(count)]

    if name in GRADIENT_ART_PALETTES:
        return _sample_gradient(GRADIENT_ART_PALETTES[name], count)

    if name == "Colorcet Glasbey" and cc is not None:
        base = list(getattr(cc, "glasbey", [])) or BUILTIN_ART_PALETTES["Clean Contrast"]
        return [base[i % len(base)] for i in range(count)]

    if name == "Colorcet Fire" and cc is not None:
        return [to_hex(cc.cm.fire(i / max(count - 1, 1))) for i in range(count)]

    if name == "CMasher Gem" and cmr is not None:
        return _sample_cmap("cmr.gem", count)

    if name == "CMasher Rainforest" and cmr is not None:
        return _sample_cmap("cmr.rainforest", count)

    if name == "Matplotlib Viridis":
        return _sample_cmap("viridis", count)
    if name == "Matplotlib Plasma":
        return _sample_cmap("plasma", count)
    if name == "Matplotlib Tab20":
        return _sample_cmap("tab20", count)

    return get_palette_colors("Journal Muted", count)
