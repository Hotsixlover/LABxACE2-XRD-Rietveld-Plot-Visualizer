# SPDX-License-Identifier: GPL-2.0-or-later
"""Chemical-formula labels and stable phase colors for BGMN DIA data."""

import colorsys
import hashlib
import math
import re
from functools import lru_cache


_ELEMENT_SYMBOLS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Ir", "Pt", "Au", "Hg", "Os",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
}


def _restore_formula_capitalization(formula_text):
    """Restore element-symbol capitalization while preserving digits."""
    text = str(formula_text or "")
    has_uppercase = any(char.isupper() for char in text)
    output = []
    index = 0

    while index < len(text):
        char = text[index]
        if char.isdigit() or char in "()[]":
            output.append(char)
            index += 1
            continue
        if not char.isalpha():
            index += 1
            continue

        if has_uppercase and char.isupper():
            if index + 1 < len(text) and text[index + 1].islower():
                candidate = char + text[index + 1].lower()
                if candidate in _ELEMENT_SYMBOLS:
                    output.append(candidate)
                    index += 2
                    continue
            candidate = char.upper()
            if candidate in _ELEMENT_SYMBOLS:
                output.append(candidate)
                index += 1
                continue

        matched_symbol = None
        for symbol_length in (2, 1):
            piece = text[index:index + symbol_length]
            if len(piece) != symbol_length or not piece.isalpha():
                continue
            candidate = piece[0].upper() + piece[1:].lower()
            if candidate in _ELEMENT_SYMBOLS:
                matched_symbol = candidate
                break

        if matched_symbol is not None:
            output.append(matched_symbol)
            index += len(matched_symbol)
        else:
            index += 1

    return "".join(output)


def extract_chemical_formula(structure_name):
    """Extract a clean display formula from a DIA STRUC database name."""
    raw_name = str(structure_name or "").strip()
    if not raw_name:
        return ""

    cleaned = re.sub(r"(?i)^STRUC\[\d+\]\s*=\s*", "", raw_name)
    cleaned = cleaned.split()[0] if cleaned.split() else ""

    had_cod_prefix = bool(re.match(r"(?i)^cod\d*", cleaned))
    if had_cod_prefix:
        cleaned = re.sub(r"(?i)^cod\d*", "", cleaned, count=1)

    cleaned = re.split(r"(?i)mp(?=\d)", cleaned, maxsplit=1)[0]
    cleaned = re.sub(
        r"(?i)(?:pna\d*|pnma|c2c|[pcirfab]\d[a-z0-9/_+\-]*)sym$",
        "",
        cleaned,
    )
    cleaned = re.sub(r"(?i)sym$", "", cleaned)

    if had_cod_prefix:
        trailing_digits = re.search(r"(\d+)$", cleaned)
        if trailing_digits:
            digit_text = trailing_digits.group(1)
            formula_digits = digit_text
            if len(digit_text) > 11:
                formula_digits = digit_text[:-11]
            elif len(digit_text) > 7:
                formula_digits = digit_text[:-7]
            cleaned = cleaned[:trailing_digits.start(1)] + formula_digits

    cleaned = re.sub(r"[^A-Za-z0-9()\[\]]", "", cleaned)
    formula = _restore_formula_capitalization(cleaned)
    formula = re.sub(r"PO4([2-9]\d*)$", r"(PO4)\1", formula)
    return formula if formula else raw_name


def format_chemical_formula_mathtext(formula):
    """Convert stoichiometric numbers to Matplotlib MathText subscripts."""
    text = str(formula or "")
    if not text or "$" in text or "_{" in text or "^{" in text:
        return text

    chemical_pattern = (
        r"^(?:"
        r"[A-Z][a-z]?(?:\d+)?"
        r"|\((?:[A-Z][a-z]?(?:\d+)?)+\)(?:\d+)?"
        r")+$"
    )
    if not re.fullmatch(chemical_pattern, text):
        return text
    return re.sub(r"(\d+)", r"$_{\1}$", text)


def parse_formula_element_counts(formula_text):
    """Parse ``Na3Fe2(PO4)3`` into an element-count dictionary."""
    text = str(formula_text or "").strip()
    if not text:
        return {}

    tokens = re.findall(r"[A-Z][a-z]?|\d+|\(|\)", text)
    if not tokens:
        return {}

    stack = [{}]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "(":
            stack.append({})
            index += 1
            continue
        if token == ")":
            group_counts = stack.pop() if len(stack) > 1 else {}
            index += 1
            multiplier = 1
            if index < len(tokens) and tokens[index].isdigit():
                multiplier = int(tokens[index])
                index += 1
            for symbol, count in group_counts.items():
                stack[-1][symbol] = stack[-1].get(symbol, 0) + count * multiplier
            continue
        if re.fullmatch(r"[A-Z][a-z]?", token):
            symbol = token
            count = 1
            index += 1
            if index < len(tokens) and tokens[index].isdigit():
                count = int(tokens[index])
                index += 1
            stack[-1][symbol] = stack[-1].get(symbol, 0) + count
            continue
        return {}

    if len(stack) != 1:
        return {}
    return stack[0]


def _rgb01_to_hex(rgb_triplet):
    def clamp01(value):
        return max(0.0, min(1.0, float(value)))

    red, green, blue = (
        int(round(clamp01(value) * 255.0))
        for value in rgb_triplet
    )
    return f"#{red:02X}{green:02X}{blue:02X}"


def _canonical_formula_composition_key(formula_text):
    """Return an order-independent, empirical-composition key."""
    counts = parse_formula_element_counts(formula_text)
    if not counts:
        cleaned_text = re.sub(r"\s+", "", str(formula_text or ""))
        return f"TEXT:{cleaned_text}"

    integer_counts = {
        str(element): max(1, int(count))
        for element, count in counts.items()
    }
    common_divisor = 0
    for count in integer_counts.values():
        common_divisor = math.gcd(common_divisor, count)
    if common_divisor <= 0:
        common_divisor = 1

    reduced_counts = {
        element: count // common_divisor
        for element, count in integer_counts.items()
    }
    return "|".join(
        f"{element}:{reduced_counts[element]}"
        for element in sorted(reduced_counts)
    )


def _stable_composition_color(composition_key):
    """Map one normalized composition to one permanent vivid color."""
    fingerprint = hashlib.blake2s(
        str(composition_key).encode("utf-8"),
        digest_size=16,
        person=b"XRDColor",
    ).digest()

    hue_sector_count = 18
    hue_sector = int.from_bytes(
        fingerprint[0:2],
        byteorder="big",
        signed=False,
    ) % hue_sector_count
    hue = ((hue_sector * 137.50776405) % 360.0) / 360.0

    saturation_levels = (0.78, 0.88, 0.96)
    value_levels = (0.76, 0.86, 0.96)
    saturation = saturation_levels[fingerprint[2] % len(saturation_levels)]
    value = value_levels[fingerprint[3] % len(value_levels)]
    return _rgb01_to_hex(colorsys.hsv_to_rgb(hue, saturation, value))


@lru_cache(maxsize=512)
def _generate_formula_color_cached(normalized_formula_text):
    composition_key = _canonical_formula_composition_key(
        normalized_formula_text
    )
    return _stable_composition_color(composition_key)


def generate_formula_color(formula_text):
    """Return the source program's deterministic composition-based color."""
    return _generate_formula_color_cached(str(formula_text or ""))


def assign_distinct_formula_colors(formula_texts):
    """Assign stable colors independently of DIA and phase ordering."""
    assigned = {}
    for formula_text in formula_texts:
        formula_text = str(formula_text or "")
        if formula_text not in assigned:
            assigned[formula_text] = generate_formula_color(formula_text)
    return assigned
