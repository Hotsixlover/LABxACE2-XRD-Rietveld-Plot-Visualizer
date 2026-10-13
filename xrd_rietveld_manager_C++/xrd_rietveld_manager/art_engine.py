# SPDX-License-Identifier: GPL-2.0-or-later
from matplotlib import patheffects as pe

try:
    from adjustText import adjust_text
except Exception:
    adjust_text = None

try:
    import mplcyberpunk
except Exception:
    mplcyberpunk = None


class PlotArtEngine:
    """Adds optional visual art effects on top of clean publication styling."""

    def __init__(self, app):
        self.app = app

    def enabled(self):
        return bool(getattr(self.app, "art_effects_enabled", False))

    def text_halo_enabled(self):
        return self.enabled() and bool(getattr(self.app, "art_text_halo", True))

    def marker_depth_enabled(self):
        return self.enabled() and bool(getattr(self.app, "art_marker_depth", False))

    def label_adjust_enabled(self):
        return self.enabled() and bool(getattr(self.app, "art_label_adjust", False))

    def line_effect(self):
        if not self.enabled():
            return "none"
        return str(getattr(self.app, "art_line_effect", "none"))

    def apply_line_art(self, artist, color=None):
        if artist is None:
            return
        effect = self.line_effect()
        if effect == "none":
            return
        try:
            if effect == "soft shadow":
                artist.set_path_effects([
                    pe.SimpleLineShadow(offset=(1.2, -1.2), alpha=0.25),
                    pe.Normal(),
                ])
            elif effect == "glow":
                foreground = color or artist.get_color()
                base_lw = float(getattr(artist, "get_linewidth", lambda: 1.0)())
                artist.set_path_effects([
                    pe.Stroke(linewidth=base_lw + 3.0, foreground=foreground, alpha=0.22),
                    pe.Stroke(linewidth=base_lw + 1.4, foreground=foreground, alpha=0.35),
                    pe.Normal(),
                ])
        except Exception:
            pass

    def apply_marker_art(self, artist):
        if artist is None or not self.marker_depth_enabled():
            return
        try:
            artist.set_path_effects([
                pe.withSimplePatchShadow(offset=(0.8, -0.8), alpha=0.25, rho=0.55),
                pe.withStroke(linewidth=0.7, foreground="white"),
                pe.Normal(),
            ])
        except Exception:
            pass

    def apply_text_art(self, text_artist):
        if text_artist is None or getattr(text_artist, "_labx_no_text_art", False) or not self.text_halo_enabled():
            return
        try:
            text_artist.set_path_effects([
                pe.withStroke(linewidth=2.4, foreground="white"),
                pe.Normal(),
            ])
        except Exception:
            pass

    def apply_axes_text_art(self, ax):
        if not self.text_halo_enabled():
            return
        try:
            for text in ax.texts:
                self.apply_text_art(text)
            for text in ax.get_xticklabels() + ax.get_yticklabels():
                self.apply_text_art(text)
            if hasattr(ax, "get_zticklabels"):
                for text in ax.get_zticklabels():
                    self.apply_text_art(text)
        except Exception:
            pass

    def adjust_axes_text(self, ax):
        if not self.label_adjust_enabled() or adjust_text is None:
            return
        try:
            movable = [t for t in ax.texts if t.get_visible()]
            if len(movable) < 2:
                return
            adjust_text(
                movable,
                ax=ax,
                expand=(1.05, 1.18),
                force_text=(0.08, 0.14),
                force_static=(0.05, 0.10),
                force_pull=(0.01, 0.02),
                time_lim=0.35,
                arrowprops=dict(arrowstyle="-", color="#666666", lw=0.35, alpha=0.55),
            )
        except Exception:
            pass

    def apply_cyberpunk_effects(self, ax=None):
        if not self.enabled() or self.line_effect() != "cyberpunk" or mplcyberpunk is None:
            return
        try:
            if ax is not None and hasattr(mplcyberpunk, "make_lines_glow"):
                mplcyberpunk.make_lines_glow(ax)
            elif hasattr(mplcyberpunk, "add_glow_effects"):
                mplcyberpunk.add_glow_effects()
        except Exception:
            pass
