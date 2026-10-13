# SPDX-License-Identifier: GPL-2.0-or-later
"""Format-specific readers. No Tk, plotting, colors or display offsets here.

Parsers return intensity arrays in source units (the optional DIA native reader
already normalizes). ProfileData.normalized() applies the shared display policy.
Only constant-wavelength 2-theta profiles are accepted by the current plot UI.
"""
from dataclasses import dataclass, field
from pathlib import Path
import csv
import re

import numpy as np


PROFILE_FILE_TYPES = [
    ("Rietveld profiles", "*.dia *.csv *.prf *.txt"),
    ("Profex / BGMN", "*.dia"),
    ("GSAS / GSAS-II CSV", "*.csv *.txt"),
    ("FullProf / WinPLOTR", "*.prf"),
    ("All files", "*.*"),
]


class ProfileParseError(ValueError):
    """A file is unsupported or cannot be interpreted without guessing."""


@dataclass
class ProfileData:
    x: object
    obs: object
    calc: object
    back: object = field(default_factory=list)
    phases: dict = field(default_factory=dict)
    source_format: str = ""
    metadata: dict = field(default_factory=dict)

    def normalized(self):
        """Validate before publishing any data to the UI; preserve DIA scaling."""
        x = np.asarray(self.x, dtype=float)
        arrays = {"Observed": np.asarray(self.obs, dtype=float),
                  "Calculated": np.asarray(self.calc, dtype=float),
                  "Background": np.asarray(self.back, dtype=float)}
        arrays.update({name: np.asarray(values, dtype=float)
                       for name, values in self.phases.items()})
        if x.ndim != 1 or x.size < 2 or not np.all(np.isfinite(x)):
            raise ProfileParseError("At least two finite profile points are required.")
        for name, values in arrays.items():
            if name == "Background" and values.size == 0:
                continue
            if values.shape != x.shape or not np.all(np.isfinite(values)):
                raise ProfileParseError(f"{name}: invalid values or a different point count.")
        steps = np.diff(x)
        if np.all(steps < 0):
            x = x[::-1]
            arrays = {name: values[::-1] for name, values in arrays.items()}
        elif not np.all(steps > 0):
            raise ProfileParseError("X values must be strictly monotonic; duplicate or mixed scans were found.")
        divisor = float(np.max(arrays["Observed"]))
        if divisor <= 0:
            divisor = 1.0
        arrays = {name: values / divisor for name, values in arrays.items()}
        # Exported residual curves can have a plotting offset (FullProf/LIVEPLOT).
        arrays["Difference"] = arrays["Observed"] - arrays["Calculated"]
        return x, arrays


def _read_lines(path):
    raw = Path(path).read_bytes()
    try:
        return raw.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError:
        return raw.decode("latin1").splitlines()


def _number(value):
    return float(value.strip().replace("D", "E").replace("d", "e"))


def _key(value):
    return re.sub(r"[^a-z0-9]", "", value.lower().replace("\u03b8", "theta"))


_ALIASES = {
    "x": {"x", "2theta", "twotheta", "2thetadeg", "2thetadegrees"},
    "obs": {"yobs", "iobs", "observed", "obs"},
    "calc": {"ycal", "ycalc", "ical", "icalc", "calculated", "calc"},
    "back": {"ybkg", "ibkg", "backg", "background", "bkg", "bgr", "yback", "ybackg"},
    "diff": {"yobsycal", "yobsycalc", "obscalc", "difference", "diff"},
}


def _columns(tokens):
    result = {}
    for index, token in enumerate(tokens):
        name = _key(token)
        for role, aliases in _ALIASES.items():
            if name in aliases:
                if role in result:
                    raise ProfileParseError(f"Ambiguous duplicate {role} columns.")
                result[role] = index
    return result


def _require_2theta(label):
    key = _key(label)
    if key not in _ALIASES["x"] and not key.startswith(("2theta", "twotheta")):
        raise ProfileParseError(
            f"Unsupported X axis: {label}. Export a constant-wavelength 2-theta profile; "
            "TOF, d-spacing, Q and energy axes cannot be mixed with the current XRD plot.")


def parse_dia(path, native_reader=None):
    lines = _read_lines(path)
    if not lines:
        raise ProfileParseError("Empty DIA file.")
    matches = sorted(re.findall(r"STRUC\[(\d+)\]=([^\s]+)", lines[0]), key=lambda item: int(item[0]))
    names = [name for _, name in matches]
    if len(names) != len(set(names)):
        raise ProfileParseError("DIA contains duplicate phase names.")
    native = native_reader(path, len(names)) if native_reader else None
    if native is not None:
        return ProfileData(native["x"], native["obs"], native["calc"], native["back"],
                           {name: native["phases"][i] for i, name in enumerate(names)}, "Profex / BGMN DIA")
    rows = []
    for line in lines[1:]:
        parts = line.split()
        try:
            row = [float(parts[i]) for i in range(4)]
            row.extend(float(parts[4+i]) if 4+i < len(parts) else 0.0 for i in range(len(names)))
        except (ValueError, IndexError):
            continue  # Preserve the existing DIA fallback behavior.
        rows.append(row)
    if not rows:
        raise ProfileParseError("No DIA profile points found (expected X, observed, calculated, background).")
    data = np.asarray(rows, dtype=float)
    return ProfileData(data[:, 0], data[:, 1], data[:, 2], data[:, 3],
                       {name: data[:, 4+i] for i, name in enumerate(names)}, "Profex / BGMN DIA")


def parse_gsas_csv(path):
    lines = _read_lines(path)
    # LIVEPLOT uses a quoted descriptive header and a leading empty CSV field.
    legacy_header = next((i for i, line in enumerate(lines)
                          if "columns are x i(obs) i(calc)" in line.lower()), None)
    if legacy_header is not None:
        return _parse_liveplot(lines, legacy_header)

    metadata = {}
    for index, line in enumerate(lines):
        tokens = next(csv.reader([line], skipinitialspace=True))
        if tokens and tokens[0].strip().lower().startswith("instparm:") and len(tokens) > 1:
            metadata[tokens[0].split(":", 1)[1].strip()] = tokens[1].strip()
        keys = [_key(token) for token in tokens]
        if any(key.startswith("yobs") for key in keys) and not any(key in _ALIASES["calc"] for key in keys):
            raise ProfileParseError("This CSV has no calculated profile. Export GSAS-II 'histogram CSV file', not 'stacked CSV file'.")
        if not any(key in _ALIASES["obs"] for key in keys) or not any(key in _ALIASES["calc"] for key in keys):
            continue
        # An explicit non-angular axis must not be mistaken for the auxiliary Q column.
        _require_2theta(tokens[0])
        cols = _columns(tokens)
        if "x" not in cols:
            raise ProfileParseError("CSV has no recognized 2-theta column.")
        instrument_type = metadata.get("Type", "").upper()
        if instrument_type and (len(instrument_type) < 3 or instrument_type[2] not in "CB"):
            raise ProfileParseError(f"GSAS-II instrument type {instrument_type} is not a constant-wavelength 2-theta profile.")
        rows = []
        for line_number, data_line in enumerate(lines[index+1:], index+2):
            if not data_line.strip() or data_line.lstrip().startswith(("#", "!")):
                continue
            fields = next(csv.reader([data_line], skipinitialspace=True))
            try:
                rows.append([_number(fields[cols[role]]) for role in ("x", "obs", "calc")]
                            + ([_number(fields[cols["back"]])] if "back" in cols else []))
            except (ValueError, IndexError) as exc:
                raise ProfileParseError(f"CSV line {line_number}: invalid or missing profile value.") from exc
        return _from_rows(rows, "GSAS-II / profile CSV", metadata, "back" in cols)
    raise ProfileParseError("No GSAS profile header found. Use GSAS-II histogram CSV or GSAS/EXPGUI LIVEPLOT CSV; project and reflection-only files are not profiles.")


def _from_rows(rows, source_format, metadata, has_background):
    if not rows:
        raise ProfileParseError("No observed/calculated profile points found.")
    data = np.asarray(rows, dtype=float)
    return ProfileData(data[:, 0], data[:, 1], data[:, 2],
                       data[:, 3] if has_background else [], source_format=source_format, metadata=metadata)


def _parse_liveplot(lines, header_index):
    metadata = {}
    for line in lines[:header_index]:
        text = line.strip().strip('"')
        if text.lower().startswith("x axis label "):
            label = text[len("x axis label "):]
            _require_2theta(label)
            metadata["x_label"] = label
        if text.lower().startswith("y axis label "):
            label = text[len("y axis label "):]
            if any(part in label.lower() for part in ("sqrt", "log", "square root", "sigma")):
                raise ProfileParseError("Export LIVEPLOT with a linear, unweighted intensity axis (no log/square-root/sigma transform).")
            metadata["y_label"] = label
    if "x_label" not in metadata:
        raise ProfileParseError("LIVEPLOT X-axis label is missing. Export again with X units set to 2-Theta.")
    rows, backgrounds = [], []
    for line_number, line in enumerate(lines[header_index+1:], header_index+2):
        if not line.strip():
            continue
        fields = next(csv.reader([line], skipinitialspace=True))
        if fields and not fields[0].strip():
            fields = fields[1:]  # the initial comma is part of the official exporter
        if not any(value.strip() for value in fields[:3]):
            continue  # reflection-only rows may outnumber the profile points
        try:
            rows.append([_number(fields[i]) for i in range(3)])
            backgrounds.append(_number(fields[3]) if len(fields) > 3 and fields[3].strip() else None)
        except (ValueError, IndexError) as exc:
            raise ProfileParseError(f"LIVEPLOT line {line_number}: invalid profile value.") from exc
    has_background = any(value is not None for value in backgrounds)
    if has_background:
        if any(value is None for value in backgrounds):
            raise ProfileParseError("LIVEPLOT background is missing from some profile points.")
        rows = [row + [background] for row, background in zip(rows, backgrounds)]
    return _from_rows(rows, "GSAS / EXPGUI LIVEPLOT CSV", metadata, has_background)


def parse_fullprof_prf(path):
    lines = _read_lines(path)
    for index, line in enumerate(lines):
        tokens = line.split()
        keys = [_key(token) for token in tokens]
        if not any(key in _ALIASES["obs"] for key in keys) or not any(key in _ALIASES["calc"] for key in keys):
            continue
        _require_2theta(tokens[0])
        # Bragg/Posr/(hkl) columns are a separate table printed alongside profiles.
        boundary = next((i for i, key in enumerate(keys) if key in {"bragg", "posr", "hkl"}), len(tokens))
        cols = _columns(tokens[:boundary])
        if not {"x", "obs", "calc"}.issubset(cols):
            raise ProfileParseError("Unsupported FullProf profile column header.")
        count, wavelength = None, None
        for header in lines[:index]:
            fields = header.split()
            if len(fields) >= 3 and re.fullmatch(r"\d+", fields[0]) and re.fullmatch(r"\d+", fields[1]):
                if int(fields[0]) > 0 and int(fields[1]) >= 2:
                    try:
                        wavelength = _number(fields[2])
                    except ValueError:
                        continue
                    count = int(fields[1])
                    break
        if count is None:
            raise ProfileParseError("FullProf profile point count is missing. Export the WinPLOTR PRF format with a Yobs/Ycal header.")
        rows = []
        width = max(cols.values()) + 1
        for line_number, data_line in enumerate(lines[index+1:], index+2):
            if len(rows) == count:
                break  # never consume reflection-only records after the profile
            if not data_line.strip():
                continue
            fields = data_line.split()
            try:
                # Also validate unused residual fields so a truncated row cannot shift columns.
                values = [_number(value) for value in fields[:width]]
                if len(values) != width:
                    raise ValueError("short row")
                rows.append([values[cols[role]] for role in ("x", "obs", "calc")]
                            + ([values[cols["back"]]] if "back" in cols else []))
            except (ValueError, IndexError) as exc:
                raise ProfileParseError(f"FullProf line {line_number}: truncated or invalid profile row.") from exc
        if len(rows) != count:
            raise ProfileParseError(f"FullProf declares {count} points but only {len(rows)} were found.")
        return _from_rows(rows, "FullProf / WinPLOTR PRF", {"wavelength": wavelength, "declared_points": count}, "back" in cols)
    raise ProfileParseError("Unsupported PRF variant. Export the FullProf WinPLOTR format with 2Theta, Yobs and Ycal columns.")


def parse_profile(path, native_reader=None, format_hint=None):
    suffix = (format_hint or Path(path).suffix.lstrip(".")).lower()
    if suffix == "dia":
        return parse_dia(path, native_reader)
    if suffix == "prf":
        return parse_fullprof_prf(path)
    if suffix in {"csv", "txt"}:
        return parse_gsas_csv(path)
    raise ProfileParseError("Unsupported profile file. Select Profex/BGMN .dia, GSAS/GSAS-II .csv, or FullProf .prf.")
