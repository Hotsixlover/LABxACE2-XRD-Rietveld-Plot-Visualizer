# SPDX-License-Identifier: GPL-2.0-or-later
import os
from matplotlib.ticker import AutoMinorLocator, MaxNLocator
from matplotlib.font_manager import FontProperties
from xrd_rietveld_manager.style_utils import get_font_spec


class PaperStyleEngine:
    """Applies publication-oriented Matplotlib styling for XRD plots."""

    def __init__(self, app):
        self.app = app

    def _legend_sort_key(self, indexed_entry):
        idx, (handle, label) = indexed_entry
        role = str(getattr(handle, "_xrd_legend_role", "") or "")
        plain_label = str(label or "").replace("$", "").strip().lower()
        if role == "Observed" or plain_label == "observed":
            return (0, idx)
        if role == "Calculated" or plain_label == "calculated":
            return (1, idx)
        if role == "Background" or plain_label == "background":
            return (2, idx)
        if role == "Difference" or plain_label == "difference":
            return (3, idx)
        return (10, idx)

    def _scale_legend_handles(self, leg, source_handles, legend_size):
        legend_artists = getattr(leg, "legend_handles", None)
        if legend_artists is None:
            legend_artists = getattr(leg, "legendHandles", [])
        if not legend_artists:
            return
        marker_size = max(4.0, float(legend_size) * 0.85)
        scatter_area = marker_size ** 2
        for src, artist in zip(source_handles, legend_artists):
            role = str(getattr(src, "_xrd_legend_role", "") or "")
            try:
                if hasattr(src, "get_linewidth") and hasattr(artist, "set_linewidth"):
                    artist.set_linewidth(src.get_linewidth())
            except Exception:
                pass
            if role != "Observed":
                continue
            try:
                if hasattr(artist, "set_sizes"):
                    artist.set_sizes([scatter_area])
                elif hasattr(artist, "set_markersize"):
                    artist.set_markersize(marker_size)
            except Exception:
                pass

    def apply_axis_grid(self, ax, show_x, show_y, alpha=0.5):
        ax.grid(False, which='both', axis='both')
        ax.xaxis.grid(False, which='both')
        ax.yaxis.grid(False, which='both')
        if show_x:
            ax.xaxis.grid(True, which='major', linestyle=':', alpha=alpha)
        if show_y:
            ax.yaxis.grid(True, which='major', linestyle=':', alpha=alpha)
        for line in ax.get_xgridlines():
            line.set_visible(bool(show_x))
            line.set_linestyle(':')
            line.set_alpha(alpha)
        for line in ax.get_ygridlines():
            line.set_visible(bool(show_y))
            line.set_linestyle(':')
            line.set_alpha(alpha)

    def apply_axis_font(self, ax):
        app = self.app
        base_size = int(app.var_tick_label_size.get()) if hasattr(app, "var_tick_label_size") else int(app.tick_label_size)
        size = app._scale_font_size(base_size, min_size=6, max_size=48)
        is_bold = app.var_tick_label_bold.get() if hasattr(app, "var_tick_label_bold") else app.tick_label_bold
        weight = "bold" if is_bold else app.plot_base_weight
        tick_font = getattr(app, "tick_label_font", "Use Plot Font")
        if hasattr(app, "var_tick_label_font"):
            try:
                tick_font = app.var_tick_label_font.get() or "Use Plot Font"
            except Exception:
                tick_font = getattr(app, "tick_label_font", "Use Plot Font")
        tick_labels = list(ax.get_xticklabels()) + list(ax.get_yticklabels())
        if hasattr(ax, "get_zticklabels"):
            try:
                tick_labels += list(ax.get_zticklabels())
            except Exception:
                pass
        tick_label_color = getattr(app, "tick_label_color", "#000000")
        if hasattr(app, "var_tick_label_color"):
            try:
                tick_label_color = app.var_tick_label_color.get() or tick_label_color
            except Exception:
                tick_label_color = getattr(app, "tick_label_color", "#000000")
        if tick_font and tick_font != "Use Plot Font":
            spec = get_font_spec(tick_font)
            kwargs = {"family": spec["family"], "weight": weight, "size": size}
            font_path = spec.get("path")
            if font_path and os.path.exists(font_path) and not is_bold:
                kwargs["fname"] = font_path
            prop = FontProperties(**kwargs)
            for tick in tick_labels:
                try:
                    tick.set_fontproperties(prop)
                except Exception:
                    app._apply_forced_font(tick, size=size, weight=weight, bold=is_bold)
        else:
            for tick in tick_labels:
                app._apply_forced_font(tick, size=size, weight=weight, bold=is_bold)
        for tick in tick_labels:
            try:
                tick.set_color(tick_label_color)
            except Exception:
                pass
        axis_title_font = getattr(app, "axis_label_font", "Use Plot Font")
        if hasattr(app, "var_axis_label_font"):
            try:
                axis_title_font = app.var_axis_label_font.get() or "Use Plot Font"
            except Exception:
                axis_title_font = getattr(app, "axis_label_font", "Use Plot Font")
        axis_label_color = getattr(app, "axis_label_color", "#000000")
        if hasattr(app, "var_axis_label_color"):
            try:
                axis_label_color = app.var_axis_label_color.get() or axis_label_color
            except Exception:
                axis_label_color = getattr(app, "axis_label_color", "#000000")
        axis_title_size = app._get_axis_label_size() if hasattr(app, "_get_axis_label_size") else None
        axis_title_weight = app._get_axis_label_weight() if hasattr(app, "_get_axis_label_weight") else app.plot_base_weight
        axis_title_bold = axis_title_weight == "bold"
        axis_label_artists = [ax.xaxis.label, ax.yaxis.label]
        if hasattr(ax, "zaxis"):
            try:
                axis_label_artists.append(ax.zaxis.label)
            except Exception:
                pass
        if axis_title_font and axis_title_font != "Use Plot Font":
            spec = get_font_spec(axis_title_font)
            kwargs = {"family": spec["family"], "weight": axis_title_weight}
            if axis_title_size is not None:
                kwargs["size"] = axis_title_size
            font_path = spec.get("path")
            if font_path and os.path.exists(font_path) and not axis_title_bold:
                kwargs["fname"] = font_path
            axis_prop = FontProperties(**kwargs)
            for text in axis_label_artists:
                try:
                    text.set_fontproperties(axis_prop)
                except Exception:
                    app._apply_forced_font(text, size=axis_title_size, weight=axis_title_weight, bold=axis_title_bold)
        else:
            for text in axis_label_artists:
                app._apply_forced_font(text, size=axis_title_size, weight=axis_title_weight, bold=axis_title_bold)
        for text in axis_label_artists:
            try:
                text.set_color(axis_label_color)
            except Exception:
                pass
        app._apply_forced_font(ax.title)
        for text in ax.texts:
            app._apply_forced_font(text)
        self.apply_axis_label_spacing(ax)
        self.apply_axis_box_style(ax)
        if hasattr(app, "art_engine"):
            app.art_engine.apply_axes_text_art(ax)
            app.art_engine.adjust_axes_text(ax)
            app.art_engine.apply_cyberpunk_effects(ax)

    def apply_axis_box_style(self, ax):
        app = self.app
        base = app.var_plot_box_linewidth.get() if hasattr(app, "var_plot_box_linewidth") else app.plot_box_linewidth
        lw = max(0.1, app._scaled_line_width(base))
        try:
            for spine in ax.spines.values():
                spine.set_linewidth(lw)
        except Exception:
            pass

    def apply_2d_tick_style(self, ax, tick_dir, show_x_ticks, show_y_ticks, show_x_labels=None, show_y_labels=None):
        app = self.app
        tick_dir = str(tick_dir or "in")
        show_x_ticks = bool(show_x_ticks) and tick_dir != "none"
        show_y_ticks = bool(show_y_ticks) and tick_dir != "none"
        # Y minor ticks stay limited to diffraction/main axes. X minor ticks,
        # however, must use the same baseline as the visible X major ticks so
        # they move below residual/reference panels together.
        minor_allowed = ax in getattr(app, "fixed_plot_box_axes", ())
        show_x_minor = show_x_ticks and (
            bool(app.var_minor_tick_x_2d.get())
            if hasattr(app, "var_minor_tick_x_2d")
            else bool(getattr(app, "show_minor_tick_x_2d", True))
        )
        show_y_minor = minor_allowed and (
            bool(app.var_minor_tick_y_2d.get())
            if hasattr(app, "var_minor_tick_y_2d")
            else bool(getattr(app, "show_minor_tick_y_2d", True))
        )
        show_x_minor = show_x_minor and tick_dir != "none"
        show_y_minor = show_y_minor and tick_dir != "none"

        try:
            max_x_labels = max(2, int(getattr(app, "max_x_tick_labels", 6)))
            max_y_labels = max(2, int(getattr(app, "max_y_tick_labels", 6)))
            ax.xaxis.set_major_locator(MaxNLocator(nbins=max_x_labels, prune=None))
            ax.yaxis.set_major_locator(MaxNLocator(nbins=max_y_labels, prune=None))
        except Exception:
            pass


        try:
            tick_length = max(0.0, min(40.0, float(getattr(app, "tick_length_2d", 10.0))))
        except Exception:
            tick_length = 10.0
        try:
            tick_width = max(0.1, min(12.0, app._scaled_line_width(float(getattr(app, "tick_width_2d", 1.0)))))
        except Exception:
            tick_width = app._scaled_line_width(1.0)
        try:
            minor_tick_length = max(0.0, min(40.0, float(getattr(app, "minor_tick_length_2d", 5.0))))
        except Exception:
            minor_tick_length = 5.0

        major_kwargs = {
            "which": "major",
            "direction": tick_dir if tick_dir != "none" else "in",
            "bottom": show_x_ticks,
            "top": False,
            "left": show_y_ticks,
            "right": False,
            "length": tick_length,
            "width": tick_width,
        }
        if show_x_labels is not None:
            major_kwargs["labelbottom"] = bool(show_x_labels)
        if show_y_labels is not None:
            major_kwargs["labelleft"] = bool(show_y_labels)
        try:
            ax.tick_params(**major_kwargs)
        except ValueError:
            major_kwargs["direction"] = "in"
            ax.tick_params(**major_kwargs)

        try:
            x_rot = float(getattr(app, "tick_label_x_rotation", 0.0))
            y_rot = float(getattr(app, "tick_label_y_rotation", 0.0))
            for label in ax.get_xticklabels():
                label.set_rotation(x_rot)
                label.set_ha("right" if abs(x_rot) >= 20 else "center")
            for label in ax.get_yticklabels():
                label.set_rotation(y_rot)
                label.set_va("center")
        except Exception:
            pass

        # Font/art passes query tick artists again later in the draw cycle.
        # Pin visibility on the artists themselves so the Y Labels checkbox
        # cannot be undone by a subsequent style refresh.
        x_labels_visible = show_x_ticks if show_x_labels is None else bool(show_x_labels)
        y_labels_visible = show_y_ticks if show_y_labels is None else bool(show_y_labels)
        try:
            for tick in ax.xaxis.get_major_ticks():
                tick.label1.set_visible(x_labels_visible)
            for tick in ax.yaxis.get_major_ticks():
                tick.label1.set_visible(y_labels_visible)
        except Exception:
            pass

        try:
            if show_x_minor:
                ax.xaxis.set_minor_locator(AutoMinorLocator())
            if show_y_minor:
                ax.yaxis.set_minor_locator(AutoMinorLocator())
            ax.tick_params(
                which="minor",
                direction=tick_dir if tick_dir != "none" else "in",
                bottom=show_x_minor,
                top=False,
                left=show_y_minor,
                right=False,
                labelbottom=False,
                labelleft=False,
                length=minor_tick_length,
                width=tick_width,
            )
        except ValueError:
            ax.tick_params(
                which="minor",
                direction="in",
                bottom=show_x_minor,
                top=False,
                left=show_y_minor,
                right=False,
                labelbottom=False,
                labelleft=False,
                length=minor_tick_length,
                width=tick_width,
            )

        self.apply_axis_label_spacing(ax)

    def apply_axis_label_spacing(self, ax):
        app = self.app
        try:
            x_pad = float(getattr(app, "axis_label_x_pad", 6.0))
            y_pad = float(getattr(app, "axis_label_y_pad", 10.0))
            y_coord = float(getattr(app, "axis_label_y_coord", -0.075))
            ax.xaxis.labelpad = x_pad
            ax.yaxis.labelpad = y_pad
            # -0.075 is the legacy/default control value. At that default,
            # leave placement to Matplotlib so the Y title moves toward the
            # plot when Y tick labels/ticks are hidden, just like the X title.
            # Any user-edited Y Pos remains an intentional fixed coordinate.
            if ax.get_ylabel() and abs(y_coord - (-0.075)) > 1e-9:
                ax.yaxis.set_label_coords(y_coord, 0.5)
        except Exception:
            pass

    def apply_plot_title(self, ax):
        app = self.app
        app.title_artist = None
        app.title_axis = None
        title_text = app.plot_title_text.strip()
        if not title_text:
            return
        weight = "bold" if app.plot_title_bold else app.plot_base_weight
        x_pos, y_pos = app.plot_title_pos
        x_pos = max(0.0, min(1.0, x_pos))
        y_pos = max(0.0, min(1.0, y_pos))
        app.plot_title_pos = [x_pos, y_pos]
        app.title_artist = ax.text(
            x_pos,
            y_pos,
            title_text,
            transform=ax.transAxes,
            ha='left',
            va='top',
            fontsize=app._get_title_font_size(),
            fontproperties=app._font_prop(size=app._get_title_font_size(), weight=weight, bold=app.plot_title_bold),
        )
        if hasattr(app, "art_engine"):
            app.art_engine.apply_text_art(app.title_artist)
        app.title_axis = ax

    def draw_legend(self, ax_main, legend_handles):
        app = self.app
        if not app.var_show_legend.get() or not legend_handles:
            return
        entries = list(zip(legend_handles.values(), legend_handles.keys()))
        entries = [entry for _, entry in sorted(enumerate(entries), key=self._legend_sort_key)]
        h_list = [entry[0] for entry in entries]
        l_list = [entry[1] for entry in entries]
        frame_alpha = 0.0 if app.var_legend_transparent.get() else 0.7
        legend_size = app._get_legend_font_size()
        legend_bold = bool(app.var_legend_bold.get()) if hasattr(app, "var_legend_bold") else bool(getattr(app, "legend_bold", False))
        legend_orient = app.var_legend_orientation.get() if hasattr(app, "var_legend_orientation") else app.legend_orientation
        legend_col_mode = app.var_legend_column_mode.get() if hasattr(app, "var_legend_column_mode") else app.legend_column_mode
        legend_loc_pref = app.var_legend_location.get() if hasattr(app, "var_legend_location") else app.legend_location
        try:
            manual_ncol = int(app.var_legend_ncol.get()) if hasattr(app, "var_legend_ncol") else int(app.legend_ncol)
        except Exception:
            manual_ncol = 1
        manual_ncol = max(1, manual_ncol)
        try:
            max_width_pct = int(app.var_legend_max_width.get()) if hasattr(app, "var_legend_max_width") else int(app.legend_max_width_ratio * 100)
        except Exception:
            max_width_pct = int(app.legend_max_width_ratio * 100)
        max_width_ratio = max(0.40, min(1.00, max_width_pct / 100.0))

        if legend_orient == "horizontal":
            if legend_col_mode in {"manual", "custom"}:
                legend_ncol = min(len(l_list), manual_ncol)
            else:
                legend_ncol = app._estimate_horizontal_legend_ncol(ax_main, l_list, legend_size, max_width_ratio)
            if legend_loc_pref == "auto":
                legend_loc = 'upper center'
                legend_bbox = (0.5, 1.0)
            else:
                legend_loc = legend_loc_pref
                legend_bbox = None
        else:
            legend_ncol = 1
            legend_loc = 'upper right' if legend_loc_pref == "auto" else legend_loc_pref
            legend_bbox = None
        leg = ax_main.legend(
            h_list,
            l_list,
            loc=legend_loc,
            bbox_to_anchor=legend_bbox,
            fontsize=legend_size,
            framealpha=frame_alpha,
            ncol=legend_ncol,
        )
        if leg:
            self._scale_legend_handles(leg, h_list, legend_size)
            if app.var_legend_transparent.get():
                leg.get_frame().set_facecolor('none')
            for text in leg.get_texts():
                app._apply_forced_font(
                    text,
                    size=legend_size,
                    weight="bold" if legend_bold else app.plot_base_weight,
                    bold=legend_bold,
                )
                if hasattr(app, "art_engine"):
                    app.art_engine.apply_text_art(text)
            leg.set_draggable(True)
