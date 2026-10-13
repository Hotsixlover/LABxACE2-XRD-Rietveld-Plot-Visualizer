# SPDX-License-Identifier: GPL-2.0-or-later
import io

from xrd_rietveld_manager.common import *


class ExportToolsMixin:
    def _prepare_plot_export(self):
        """Reset view-only zoom before any persistent or clipboard output."""
        reset_zoom = getattr(self, "_reset_plot_canvas_zoom", None)
        if callable(reset_zoom):
            reset_zoom(immediate=True)

    def export_xy_data(self, target_path=None):
        if not target_path:
            sel = self.file_tree.selection()
            if not sel: 
                messagebox.showwarning("Warning", "Select a file in the tree to export.")
                return
            target_path = sel[0]
            
        if target_path not in self.loaded_files: return
        
        loader = self.loaded_files[target_path]
        
        save_path = filedialog.asksaveasfilename(
            initialfile=f"{loader.filename}_XY.csv",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Text", "*.txt")]
        )
        if not save_path: return
        
        try:
            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["2Theta", "Intensity_Raw_Minus_Bg" if loader.back else "Intensity_Normalized"])
                
                x_data = getattr(loader, "x_np", np.asarray(loader.x, dtype=float))
                y_data = getattr(loader, "obs_np", np.asarray(loader.obs, dtype=float))
                back_data = getattr(loader, "back_np", np.asarray(loader.back, dtype=float))
                if back_data.size:
                    y_data = y_data - back_data
                    
                for x, y in zip(x_data, y_data):
                    writer.writerow([x, y])
            messagebox.showinfo("Success", "Export Complete.")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def save_image(self):
        p = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG Image", "*.png"),
                ("JPEG Image", "*.jpg;*.jpeg"),
                ("TIFF Image", "*.tif;*.tiff"),
                ("All files", "*.*"),
            ],
        )
        if p:
            self._prepare_plot_export()
            self.fig.savefig(p, dpi=300, bbox_inches=None)

    def export_vector_artwork(self):
        p = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[
                ("SVG vector for Illustrator/Inkscape", "*.svg"),
                ("PDF vector", "*.pdf"),
                ("EPS vector", "*.eps"),
                ("All files", "*.*"),
            ],
        )
        if not p:
            return
        ext = os.path.splitext(p)[1].lower().lstrip(".")
        if ext not in {"svg", "pdf", "eps"}:
            ext = "svg"
            p = f"{p}.svg"
        transparent = messagebox.askyesno(
            "Vector Export",
            "Export with transparent background?\n\nYes: transparent for Illustrator/Inkscape compositing\nNo: keep current figure background",
        )
        try:
            self._prepare_plot_export()
            self.fig.savefig(
                p,
                format=ext,
                dpi=300,
                bbox_inches=None,
                transparent=transparent,
                facecolor='none' if transparent else self.fig.get_facecolor(),
                edgecolor='none',
            )
            messagebox.showinfo("Export Complete", f"Vector artwork exported:\n{p}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export vector artwork.\n{e}")

    def _canvas_to_dib_bytes(self, dpi=300):
        # Render a fresh, high-resolution copy. Reading the interactive Tk
        # canvas directly would make clipboard quality depend on view zoom.
        dpi = max(72, int(dpi))
        figure_width = max(1e-6, float(self.fig.get_figwidth()))
        figure_height = max(1e-6, float(self.fig.get_figheight()))
        requested_width = figure_width * dpi
        requested_height = figure_height * dpi
        render_scale = min(
            1.0,
            12000.0 / requested_width,
            12000.0 / requested_height,
            math.sqrt(48_000_000.0 / max(1.0, requested_width * requested_height)),
        )
        render_dpi = max(1, int(round(dpi * render_scale)))
        # FigureCanvasAgg truncates fractional output pixels. Match that exact
        # rule so Fit-to-Window figures with decimal inch sizes reshape safely.
        width = max(1, int(figure_width * render_dpi))
        height = max(1, int(figure_height * render_dpi))
        if width <= 0 or height <= 0:
            raise RuntimeError("Invalid canvas size.")

        raw = io.BytesIO()
        self.fig.savefig(
            raw,
            format="rgba",
            dpi=render_dpi,
            bbox_inches=None,
            facecolor=self.fig.get_facecolor(),
            edgecolor="none",
            transparent=False,
        )
        rgba = np.frombuffer(raw.getvalue(), dtype=np.uint8)
        if rgba.size != width * height * 4:
            raise RuntimeError("Failed to read plot pixels from canvas.")
        rgba = rgba.reshape((height, width, 4))

        rgb = rgba[:, :, :3]
        bgr = rgb[:, :, ::-1]
        row_stride = ((width * 3 + 3) // 4) * 4
        pixel_data = bytearray(row_stride * height)

        for dst_row in range(height):
            src_row = height - 1 - dst_row
            src_bytes = bgr[src_row].tobytes()
            dst_offset = dst_row * row_stride
            pixel_data[dst_offset:dst_offset + (width * 3)] = src_bytes

        pixels_per_meter = int(round(render_dpi / 0.0254))
        header = struct.pack(
            "<IIIHHIIIIII",
            40,                 # biSize
            width,              # biWidth
            height,             # biHeight (bottom-up)
            1,                  # biPlanes
            24,                 # biBitCount
            0,                  # biCompression (BI_RGB)
            len(pixel_data),    # biSizeImage
            pixels_per_meter,   # biXPelsPerMeter
            pixels_per_meter,   # biYPelsPerMeter
            0,                  # biClrUsed
            0                   # biClrImportant
        )
        return header + pixel_data

    def _copy_dib_to_windows_clipboard(self, dib_bytes):
        CF_DIB = 8
        GMEM_MOVEABLE = 0x0002

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        user32.OpenClipboard.argtypes = [ctypes.c_void_p]
        user32.OpenClipboard.restype = ctypes.c_int
        user32.EmptyClipboard.argtypes = []
        user32.EmptyClipboard.restype = ctypes.c_int
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        user32.SetClipboardData.restype = ctypes.c_void_p
        user32.CloseClipboard.argtypes = []
        user32.CloseClipboard.restype = ctypes.c_int

        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.restype = ctypes.c_int
        kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
        kernel32.GlobalFree.restype = ctypes.c_void_p

        if not user32.OpenClipboard(None):
            raise RuntimeError("Cannot open Windows clipboard.")

        h_global = None
        try:
            if not user32.EmptyClipboard():
                raise RuntimeError("Cannot clear clipboard.")

            h_global = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(dib_bytes))
            if not h_global:
                raise RuntimeError("Clipboard memory allocation failed.")

            p_global = kernel32.GlobalLock(h_global)
            if not p_global:
                raise RuntimeError("Clipboard memory lock failed.")

            try:
                ctypes.memmove(p_global, dib_bytes, len(dib_bytes))
            finally:
                kernel32.GlobalUnlock(h_global)

            if not user32.SetClipboardData(CF_DIB, h_global):
                raise RuntimeError("Failed to set image data to clipboard.")

            # Ownership moved to clipboard.
            h_global = None
        finally:
            user32.CloseClipboard()
            if h_global:
                kernel32.GlobalFree(h_global)

    def copy_plot_to_clipboard(self):
        if platform.system() != "Windows":
            messagebox.showerror("Unsupported", "Copy image to clipboard is currently supported on Windows only.")
            return
        try:
            self._prepare_plot_export()
            dib_bytes = self._canvas_to_dib_bytes()
            self._copy_dib_to_windows_clipboard(dib_bytes)
            messagebox.showinfo("Copied", "Plot image copied to clipboard.")
        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Failed to copy plot image.\n{e}")

