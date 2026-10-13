# SPDX-License-Identifier: GPL-2.0-or-later
import base64
import io
import json
import os
import tempfile
from types import SimpleNamespace

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import matplotlib.image as mpimg

from xrd_rietveld_manager.figure_set_manager import FigureSetManagerMixin
from xrd_rietveld_manager.figure_set_model import FigureSetItem


class _FigureSetHarness(FigureSetManagerMixin):
    def __init__(self):
        self.plot_font_family = "Calibri"
        self._init_figure_set_state()

    def _push_figure_set_page_to_ui(self):
        pass

    def refresh_figure_set_canvas(self):
        pass

    def clear_figure_set_render_cache(self, show_message=True):
        self.figure_set_render_cache = {}
        self.figure_set_render_cache_order = []


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _make_thumbnail_data():
    fig = Figure(figsize=(2.0, 1.2), dpi=120, facecolor="white")
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0.12, 0.18, 0.82, 0.72])
    ax.plot([0, 1, 2, 3], [0.2, 0.7, 0.45, 0.9], color="#2563eb", lw=1.8)
    ax.set_xlabel("2 theta")
    ax.set_ylabel("Intensity")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def run_selftest():
    thumbnail = _make_thumbnail_data()
    app = _FigureSetHarness()
    app.figure_set_page.width_cm = 10.0
    app.figure_set_page.height_cm = 8.0
    app.figure_set_page.zoom_percent = 123
    app.figure_set_page.export_dpi = 150
    app.figure_set_page.panel_render_scale = 1.0
    app.figure_set_page.export_metadata_enabled = True
    app.figure_set_page.export_set_copy_enabled = True

    app.fig = Figure(figsize=(8.0, 4.0), dpi=100, facecolor="white")
    FigureCanvasAgg(app.fig)
    source_ax = app.fig.add_subplot(111)
    source_ax.plot([0, 1, 2], [0.2, 0.9, 0.4])
    panel_width, panel_height = app._current_plot_figure_set_dimensions()
    _assert(abs(panel_width / panel_height - 2.0) < 1e-9, "current plot aspect ratio was not preserved")
    app.figure_set_page.export_dpi = 600
    captured = app._capture_current_plot_thumbnail()
    captured_image = mpimg.imread(io.BytesIO(base64.b64decode(captured)), format="png")
    _assert(captured_image.shape[1] == 2400, "fallback thumbnail width is not 300 dpi")
    _assert(captured_image.shape[0] == 1200, "fallback thumbnail height is not 300 dpi")
    preview_item = FigureSetItem(item_id="preview", label="Preview", width_cm=6.0, height_cm=3.0)
    preview_dpi = app._figure_set_preview_dpi(preview_item, width_px=1800, height_px=900)
    _assert(preview_dpi > 360, "high-zoom preview DPI did not scale with display pixels")

    # A saved panel must retain the visibility state from Add Current Plot,
    # regardless of later Project Files changes or newly loaded files.
    visible_path = os.path.join("project", "visible.dia")
    hidden_path = os.path.join("project", "hidden.dia")
    new_path = os.path.join("project", "new-after-capture.dia")
    app.loaded_files = {
        visible_path: SimpleNamespace(global_visible=False),
        hidden_path: SimpleNamespace(global_visible=True),
        new_path: SimpleNamespace(global_visible=True),
    }
    visibility_recipe = {
        "figure_set_file_visibility": {
            visible_path: True,
            hidden_path: False,
        }
    }
    app._apply_figure_set_recipe_file_visibility(visibility_recipe)
    _assert(app.loaded_files[visible_path].global_visible, "captured visible file was hidden")
    _assert(not app.loaded_files[hidden_path].global_visible, "captured hidden file became visible")
    _assert(not app.loaded_files[new_path].global_visible, "file loaded after capture leaked into panel")

    legacy_recipe = {
        "files": {
            visible_path: {"global_visible": True},
            hidden_path: {"global_visible": False},
        }
    }
    app.loaded_files[hidden_path].global_visible = True
    app._apply_figure_set_recipe_file_visibility(legacy_recipe)
    _assert(not app.loaded_files[hidden_path].global_visible, "legacy panel visibility was not restored")

    capture_app = _FigureSetHarness()
    capture_app.loaded_files = {
        visible_path: SimpleNamespace(global_visible=True),
        hidden_path: SimpleNamespace(global_visible=False),
    }
    capture_app._collect_template_data = lambda: {"settings": {}, "files": {}}
    capture_app._get_ui_value = lambda _name, fallback=None: fallback
    capture_app._make_figure_set_item_label = lambda: "visibility snapshot"
    capture_app._figure_set_source_file_info = lambda paths: [{"path": path} for path in paths]
    captured_recipe = capture_app._capture_plot_recipe()
    _assert(captured_recipe["source_files"] == [visible_path], "hidden file became a panel source dependency")
    _assert(
        captured_recipe["figure_set_file_visibility"][hidden_path] is False,
        "Add Current Plot did not capture the hidden-file state",
    )
    app.figure_set_page.export_dpi = 150
    app.figure_set_page.items = [
        FigureSetItem(
            item_id="item-1",
            label="Panel A",
            x_cm=1.0,
            y_cm=1.2,
            width_cm=4.0,
            height_cm=3.0,
            recipe={"source_label": "demo", "source_files": ["demo.dia"]},
            thumbnail_data=thumbnail,
            crop_left_pct=2.0,
            crop_right_pct=3.0,
            subplot_label="(a)",
        )
    ]

    data = app._figure_set_to_dict()
    _assert(data["items"][0]["label"] == "Panel A", "item serialization failed")
    _assert(data["page"]["zoom_percent"] == 123, "page zoom serialization failed")

    clone = app._clone_figure_set_item(app.figure_set_page.items[0], dx_cm=0.5, dy_cm=0.5, label_suffix=" copy")
    _assert(clone.item_id != "item-1", "clone did not create a new id")
    _assert(clone.label == "Panel A copy", "clone label suffix failed")
    _assert(abs(clone.x_cm - 1.5) < 1e-9, "clone x offset failed")
    _assert(clone.recipe["source_label"] == "demo", "clone recipe copy failed")

    loaded = _FigureSetHarness()
    loaded._load_figure_set_data(data)
    _assert(len(loaded.figure_set_page.items) == 1, "load roundtrip item count failed")
    _assert(loaded.figure_set_page.items[0].subplot_label == "(a)", "load roundtrip subplot label failed")

    too_zoomed = _FigureSetHarness()
    changed = dict(data)
    changed["page"] = dict(data["page"])
    changed["page"]["zoom_percent"] = 9999
    too_zoomed._load_figure_set_data(changed)
    _assert(too_zoomed.figure_set_page.zoom_percent == 800, "zoom upper clamp failed")

    with tempfile.TemporaryDirectory() as tmp:
        first = os.path.join(tmp, "figure.manifest.json")
        with open(first, "w", encoding="utf-8") as f:
            f.write("{}")
        candidate = app._figure_set_unique_companion_path(first)
        _assert(candidate.endswith("_2.json"), "unique companion path failed")

    with tempfile.TemporaryDirectory() as tmp:
        output_path = os.path.join(tmp, "figure_set_export_smoke.png")
        app._export_figure_set_to_path(output_path)
        companions = app._figure_set_export_companion_paths(output_path)
        manifest_path = app._write_figure_set_export_manifest(
            output_path,
            scope="selftest",
            items=app.figure_set_page.items,
            manifest_path=companions.get("manifest"),
            set_copy_path=companions.get("set_copy"),
        )
        set_copy_path = app._write_figure_set_export_copy(output_path, set_path=companions.get("set_copy"))
        _assert(os.path.exists(output_path) and os.path.getsize(output_path) > 0, "export image was not written")
        _assert(manifest_path and os.path.exists(manifest_path), "manifest was not written")
        _assert(set_copy_path and os.path.exists(set_copy_path), "editable set copy was not written")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        _assert(manifest["companions"]["editable_set_copy"] == os.path.abspath(set_copy_path), "manifest set-copy path mismatch")
        with open(set_copy_path, "r", encoding="utf-8") as f:
            exported_set = json.load(f)
        _assert(exported_set["items"][0]["label"] == "Panel A", "editable set copy content mismatch")

        for ext in ("pdf", "svg"):
            format_path = os.path.join(tmp, f"figure_set_export_smoke.{ext}")
            app._export_figure_set_to_path(format_path)
            _assert(os.path.exists(format_path) and os.path.getsize(format_path) > 0, f"{ext.upper()} export was not written")

    return True


if __name__ == "__main__":
    run_selftest()
    print("figure_set_selftest_ok")
