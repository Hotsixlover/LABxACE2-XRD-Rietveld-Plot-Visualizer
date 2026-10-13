# SPDX-License-Identifier: GPL-2.0-or-later
"""Optional C++ acceleration with transparent Python fallbacks.

The native library has a plain C ABI and is loaded with :mod:`ctypes`.  This
keeps it independent of the exact CPython minor version.  Callers deliberately
use the ``try_*`` functions: ``None`` means that the normal Python/NumPy path
must be used, while an empty array/list is a valid accelerated result.
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

import numpy as np


class _NativeAtom(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("z", ctypes.c_double),
        ("occupancy", ctypes.c_double),
        ("b_iso", ctypes.c_double),
        ("a", ctypes.c_double * 5),
        ("b", ctypes.c_double * 5),
        ("c", ctypes.c_double),
    ]


class _NativePeak(ctypes.Structure):
    _fields_ = [
        ("two_theta", ctypes.c_double),
        ("intensity", ctypes.c_double),
        ("h", ctypes.c_int32),
        ("k", ctypes.c_int32),
        ("l", ctypes.c_int32),
    ]


_library = None
_load_attempted = False
_load_error = "not loaded"


def _library_candidates():
    override = os.environ.get("XRDRM_NATIVE_LIBRARY", "").strip()
    if override:
        yield Path(override).expanduser()
    native_dir = Path(__file__).resolve().parent / "native"
    if sys.platform == "win32":
        names = ("xrd_native.dll",)
    elif sys.platform == "darwin":
        names = ("xrd_native.dylib", "libxrd_native.dylib")
    else:
        names = ("xrd_native.so", "libxrd_native.so")
    for name in names:
        yield native_dir / name


def _configure_library(library):
    library.xrd_native_version.argtypes = []
    library.xrd_native_version.restype = ctypes.c_char_p
    library.xrd_last_error.argtypes = []
    library.xrd_last_error.restype = ctypes.c_char_p

    library.xrd_load_dia_utf8.argtypes = [
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    library.xrd_load_dia_utf8.restype = ctypes.POINTER(ctypes.c_double)
    library.xrd_free_doubles.argtypes = [ctypes.POINTER(ctypes.c_double)]
    library.xrd_free_doubles.restype = None

    library.xrd_local_maxima.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_size_t,
        ctypes.c_double,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    library.xrd_local_maxima.restype = ctypes.POINTER(ctypes.c_int64)
    library.xrd_free_indices.argtypes = [ctypes.POINTER(ctypes.c_int64)]
    library.xrd_free_indices.restype = None

    library.xrd_calculate_reference_pattern.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(_NativeAtom),
        ctypes.c_size_t,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.POINTER(_NativePeak),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    library.xrd_calculate_reference_pattern.restype = ctypes.c_int


def _get_library():
    global _library, _load_attempted, _load_error
    if _load_attempted:
        return _library
    _load_attempted = True
    if os.environ.get("XRDRM_DISABLE_NATIVE", "").strip().lower() in {"1", "true", "yes", "on"}:
        _load_error = "disabled by XRDRM_DISABLE_NATIVE"
        return None

    errors = []
    for candidate in _library_candidates():
        if not candidate.is_file():
            continue
        try:
            loader = ctypes.WinDLL if sys.platform == "win32" else ctypes.CDLL
            library = loader(str(candidate))
            _configure_library(library)
            _library = library
            _load_error = ""
            return library
        except (OSError, AttributeError) as error:
            errors.append(f"{candidate}: {error}")
    _load_error = "; ".join(errors) if errors else "native library was not built"
    return None


def _last_error(library):
    raw = library.xrd_last_error()
    return raw.decode("utf-8", errors="replace") if raw else "unknown native error"


def backend_status():
    """Return diagnostic information without making native support mandatory."""
    library = _get_library()
    if library is None:
        return {"available": False, "version": None, "error": _load_error}
    raw_version = library.xrd_native_version()
    version = raw_version.decode("ascii", errors="replace") if raw_version else "unknown"
    return {"available": True, "version": version, "error": ""}


def try_load_dia_numeric(filepath, phase_count):
    """Return normalized DIA columns, or ``None`` to request Python fallback."""
    library = _get_library()
    if library is None:
        return None
    pointer = None
    try:
        rows = ctypes.c_size_t(0)
        encoded_path = os.fspath(filepath).encode("utf-8")
        pointer = library.xrd_load_dia_utf8(
            encoded_path,
            max(0, int(phase_count)),
            ctypes.byref(rows),
        )
        if not pointer:
            if rows.value == 0 and not library.xrd_last_error():
                return {
                    "x": np.array([], dtype=np.float64),
                    "obs": np.array([], dtype=np.float64),
                    "calc": np.array([], dtype=np.float64),
                    "back": np.array([], dtype=np.float64),
                    "diff": np.array([], dtype=np.float64),
                    "phases": [],
                }
            return None
        columns = 5 + max(0, int(phase_count))
        matrix = np.ctypeslib.as_array(
            pointer,
            shape=(rows.value * columns,),
        ).copy().reshape((rows.value, columns))
        return {
            "x": np.ascontiguousarray(matrix[:, 0]),
            "obs": np.ascontiguousarray(matrix[:, 1]),
            "calc": np.ascontiguousarray(matrix[:, 2]),
            "back": np.ascontiguousarray(matrix[:, 3]),
            "diff": np.ascontiguousarray(matrix[:, 4]),
            "phases": [np.ascontiguousarray(matrix[:, 5 + index]) for index in range(phase_count)],
        }
    except (OSError, ValueError, TypeError, OverflowError):
        return None
    finally:
        if pointer:
            library.xrd_free_doubles(pointer)


def try_local_maxima(values, threshold_fraction=0.05):
    """Return peak indices, or ``None`` when the C++ backend is unavailable."""
    library = _get_library()
    if library is None:
        return None
    pointer = None
    try:
        array = np.ascontiguousarray(values, dtype=np.float64)
        count = ctypes.c_size_t(0)
        pointer = library.xrd_local_maxima(
            array.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            array.size,
            float(threshold_fraction),
            ctypes.byref(count),
        )
        if not pointer:
            return np.array([], dtype=np.int64) if count.value == 0 else None
        return np.ctypeslib.as_array(pointer, shape=(count.value,)).copy()
    except (OSError, ValueError, TypeError, OverflowError):
        return None
    finally:
        if pointer:
            library.xrd_free_indices(pointer)


def try_calculate_reference_pattern(
    structure,
    form_factor_table,
    atomic_numbers,
    wavelength=1.5406,
    include_kalpha2=True,
):
    """Return ``(two_theta, intensity, hkl)`` tuples, or ``None`` on fallback."""
    library = _get_library()
    atoms = structure.get("atoms", [])
    if library is None or not atoms:
        return None
    try:
        cell = structure.get("cell", {})
        cell_values = (ctypes.c_double * 6)(
            float(cell["a"]),
            float(cell["b"]),
            float(cell["c"]),
            float(cell.get("alpha", 90.0)),
            float(cell.get("beta", 90.0)),
            float(cell.get("gamma", 90.0)),
        )
        native_atoms = (_NativeAtom * len(atoms))()
        for index, atom in enumerate(atoms):
            target = native_atoms[index]
            target.x = float(atom["x"])
            target.y = float(atom["y"])
            target.z = float(atom["z"])
            target.occupancy = float(atom.get("occ", 1.0))
            target.b_iso = max(0.0, float(atom.get("b_iso", 0.0)))
            species = str(atom.get("species", atom.get("element", "")))
            element = str(atom.get("element", ""))
            coefficients = form_factor_table.get(species) or form_factor_table.get(element)
            if coefficients:
                target.c = float(coefficients["c"])
                for coefficient in range(5):
                    target.a[coefficient] = float(coefficients["a"][coefficient])
                    target.b[coefficient] = float(coefficients["b"][coefficient])
            else:
                target.c = float(atomic_numbers.get(element, 10))

        # Typical reference patterns are far below this size.  Supplying a
        # buffer immediately avoids calculating the complete hkl grid twice.
        capacity = 65536
        output = (_NativePeak * capacity)()
        required = ctypes.c_size_t(0)
        status = library.xrd_calculate_reference_pattern(
            cell_values,
            native_atoms,
            len(atoms),
            float(wavelength),
            int(bool(include_kalpha2)),
            output,
            capacity,
            ctypes.byref(required),
        )
        if status < 0:
            return None
        if required.value == 0:
            return []
        if status == 1:
            capacity = required.value
            output = (_NativePeak * capacity)()
            status = library.xrd_calculate_reference_pattern(
                cell_values,
                native_atoms,
                len(atoms),
                float(wavelength),
                int(bool(include_kalpha2)),
                output,
                capacity,
                ctypes.byref(required),
            )
            if status != 0:
                return None
        return [
            (
                float(output[index].two_theta),
                float(output[index].intensity),
                (int(output[index].h), int(output[index].k), int(output[index].l)),
            )
            for index in range(required.value)
        ]
    except (KeyError, OSError, ValueError, TypeError, OverflowError):
        return None
