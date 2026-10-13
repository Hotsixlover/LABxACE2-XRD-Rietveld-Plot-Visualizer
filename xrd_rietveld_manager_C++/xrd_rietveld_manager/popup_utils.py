# SPDX-License-Identifier: GPL-2.0-or-later
"""Multi-monitor popup placement and the popup palette used by the legacy UI."""

import ctypes
from ctypes import wintypes
import platform
import tkinter as tk


POPUP_SURFACE_BG = "#f8f9fa"
POPUP_PRIMARY_BG = "#4285f4"
POPUP_PRIMARY_ACTIVE_BG = "#3367d6"
POPUP_SECONDARY_BG = "#f1f3f4"
POPUP_SECONDARY_ACTIVE_BG = "#e8eaed"


def enable_per_monitor_dpi_awareness():
    """Enable the donor program's strongest available Windows DPI mode."""
    if platform.system() != "Windows":
        return
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        setter = user32.SetProcessDpiAwarenessContext
        setter.argtypes = [ctypes.c_void_p]
        setter.restype = wintypes.BOOL
        if setter(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        setter = shcore.SetProcessDpiAwareness
        setter.argtypes = [ctypes.c_int]
        setter.restype = ctypes.c_long
        if setter(2) in (0, -2147024891):
            return
    except Exception:
        pass
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        setter = user32.SetProcessDPIAware
        setter.argtypes = []
        setter.restype = wintypes.BOOL
        setter()
    except Exception:
        pass


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", _Rect),
        ("rcWork", _Rect),
        ("dwFlags", wintypes.DWORD),
    ]


def _user32():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(_Rect)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user32.MonitorFromPoint.restype = wintypes.HANDLE
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_MonitorInfo)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL
    return user32


def native_toplevel_hwnd(widget):
    if platform.system() != "Windows":
        return None
    try:
        widget.update_idletasks()
        user32 = _user32()
        inner = wintypes.HWND(int(widget.winfo_id()))
        wrapper = user32.GetParent(inner)
        return wrapper if wrapper else inner
    except Exception:
        return None


def monitor_workarea_for_point(x, y, fallback_widget=None):
    x, y = int(x), int(y)
    if platform.system() == "Windows":
        try:
            user32 = _user32()
            monitor = user32.MonitorFromPoint(wintypes.POINT(x, y), 2)
            info = _MonitorInfo()
            info.cbSize = ctypes.sizeof(_MonitorInfo)
            if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                area = info.rcWork
                return int(area.left), int(area.top), int(area.right), int(area.bottom)
        except Exception:
            pass
    try:
        widget = fallback_widget
        left = int(widget.winfo_vrootx()) if widget is not None else 0
        top = int(widget.winfo_vrooty()) if widget is not None else 0
        width = int(widget.winfo_screenwidth()) if widget is not None else 1920
        height = int(widget.winfo_screenheight()) if widget is not None else 1080
        return left, top, left + width, top + height
    except Exception:
        return 0, 0, 1920, 1080


def move_toplevel_to_pointer(window, width, height, fallback_widget=None, gap=14):
    """Move a drag preview using native physical cursor coordinates on Windows."""
    width, height = max(1, int(width)), max(1, int(height))
    if platform.system() == "Windows":
        try:
            user32 = _user32()
            pointer = wintypes.POINT()
            if not user32.GetCursorPos(ctypes.byref(pointer)):
                raise OSError("GetCursorPos failed")
            left, top, right, bottom = monitor_workarea_for_point(pointer.x, pointer.y, fallback_widget)
            x = max(left, min(right - width, int(pointer.x) + int(gap)))
            y = max(top, min(bottom - height, int(pointer.y) - height // 2))
            hwnd = native_toplevel_hwnd(window)
            if not hwnd:
                raise OSError("Drag preview HWND is unavailable")
            # SWP_NOZORDER | SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_FRAMECHANGED
            flags = 0x0004 | 0x0010 | 0x0040 | 0x0020
            if not user32.SetWindowPos(hwnd, None, x, y, width, height, flags):
                raise OSError("SetWindowPos failed")
            user32.ShowWindow(hwnd, 5)
            user32.BringWindowToTop(hwnd)
            return x, y
        except Exception:
            pass
    return None


def _host_metrics(host):
    if platform.system() == "Windows":
        user32 = _user32()
        hwnd = native_toplevel_hwnd(host)
        rect = _Rect()
        if hwnd and user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            pointer = wintypes.POINT()
            inside = bool(user32.GetCursorPos(ctypes.byref(pointer))) and (
                rect.left <= pointer.x < rect.right and rect.top <= pointer.y < rect.bottom
            )
            anchor = pointer if inside else wintypes.POINT(
                int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2)
            )
            work = monitor_workarea_for_point(anchor.x, anchor.y, host)
            return (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)), work
    host.update_idletasks()
    left, top = int(host.winfo_rootx()), int(host.winfo_rooty())
    right = left + max(1, int(host.winfo_width()))
    bottom = top + max(1, int(host.winfo_height()))
    return (left, top, right, bottom), monitor_workarea_for_point(
        (left + right) // 2, (top + bottom) // 2, host
    )


def place_window_on_parent_monitor(window, parent, width, height, center=True):
    """Place and reveal a popup with the donor UI's monitor-aware animation."""
    width, height = max(100, int(width)), max(100, int(height))
    host = parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent
    window.withdraw()
    try:
        window.transient(host)
    except Exception:
        pass
    try:
        final_alpha = float(window.attributes("-alpha")) or 1.0
        window.attributes("-alpha", 0.0)
        alpha_supported = True
    except Exception:
        final_alpha = 1.0
        alpha_supported = False

    def position(y_offset=0, show=False, activate=False):
        if not window.winfo_exists():
            return
        host_rect, work = _host_metrics(host)
        host_left, host_top, host_right, host_bottom = host_rect
        work_left, work_top, work_right, work_bottom = work
        placed_width = min(width, max(100, work_right - work_left))
        placed_height = min(height, max(100, work_bottom - work_top))
        if center:
            x = host_left + ((host_right - host_left) - placed_width) // 2
            y = host_top + ((host_bottom - host_top) - placed_height) // 2
        else:
            x, y = host_left, host_top
        x = max(work_left, min(work_right - placed_width, x))
        y = max(work_top, min(work_bottom - placed_height, y + int(y_offset)))

        hwnd = native_toplevel_hwnd(window)
        if platform.system() == "Windows" and hwnd:
            flags = 0x0004 | 0x0010 | (0x0040 if show else 0)
            if not _user32().SetWindowPos(hwnd, None, x, y, placed_width, placed_height, flags):
                raise OSError("SetWindowPos failed")
        else:
            window.geometry(f"{placed_width}x{placed_height}{x:+d}{y:+d}")
        if show:
            window.deiconify()
        if activate:
            window.lift()
            window.focus_set()

    def finish():
        if not window.winfo_exists():
            return
        try:
            if alpha_supported:
                window.attributes("-alpha", final_alpha)
            position(0, True, True)
        except Exception:
            pass

    def animate(frame):
        if not window.winfo_exists():
            return
        try:
            progress = max(0.0, min(1.0, frame / 12.0))
            eased = 1.0 - (1.0 - progress) ** 3
            if alpha_supported:
                window.attributes("-alpha", final_alpha * eased)
            position(round(10 * (1.0 - eased)), True, False)
            if frame >= 12:
                finish()
            else:
                window.after(14, lambda: animate(frame + 1))
        except Exception:
            finish()

    try:
        window.geometry(f"{width}x{height}")
        window.update_idletasks()
        position(0, False, False)
        window.deiconify()
        window.update_idletasks()
        position(0, True, False)
        for delay in (20, 60, 120):
            window.after(delay, lambda: position(0, True, False))
        window.after(145, lambda: animate(1))
    except Exception:
        try:
            if alpha_supported:
                window.attributes("-alpha", final_alpha)
            window.deiconify()
            window.lift()
        except Exception:
            pass


def install_parented_native_dialogs(messagebox, filedialog, simpledialog):
    """Give every native dialog a main-window owner when callers omit one."""
    for module, names in (
        (messagebox, ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel", "askretrycancel", "askquestion")),
        (filedialog, ("askopenfilename", "askopenfilenames", "asksaveasfilename", "askdirectory")),
        (simpledialog, ("askstring", "askinteger", "askfloat")),
    ):
        for name in names:
            original = getattr(module, name, None)
            if original is None or getattr(original, "_xrd_parented", False):
                continue

            def wrapped(*args, _original=original, **kwargs):
                if kwargs.get("parent") is None:
                    root = getattr(tk, "_default_root", None)
                    if root is not None:
                        try:
                            if root.winfo_exists():
                                kwargs["parent"] = root
                        except Exception:
                            pass
                return _original(*args, **kwargs)

            wrapped._xrd_parented = True
            setattr(module, name, wrapped)
