// SPDX-License-Identifier: GPL-2.0-or-later
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <limits>
#include <map>
#include <new>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#if defined(_WIN32)
#define XRD_EXPORT extern "C" __declspec(dllexport)
#else
#define XRD_EXPORT extern "C" __attribute__((visibility("default")))
#endif

namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;
thread_local std::string g_last_error;

struct Vec3 {
    double x;
    double y;
    double z;
};

Vec3 cross(const Vec3& a, const Vec3& b) {
    return {
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    };
}

double dot(const Vec3& a, const Vec3& b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

double norm(const Vec3& value) {
    return std::sqrt(dot(value, value));
}

Vec3 scale(const Vec3& value, double factor) {
    return {value.x * factor, value.y * factor, value.z * factor};
}

Vec3 add(const Vec3& a, const Vec3& b, const Vec3& c) {
    return {a.x + b.x + c.x, a.y + b.y + c.y, a.z + b.z + c.z};
}

std::array<std::array<double, 3>, 3> invert_3x3(
    const std::array<std::array<double, 3>, 3>& m
) {
    const double determinant =
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
    if (!std::isfinite(determinant) || std::abs(determinant) <= 1e-18) {
        throw std::runtime_error("singular reciprocal lattice");
    }
    const double inv_det = 1.0 / determinant;
    return {{
        {{(m[1][1] * m[2][2] - m[1][2] * m[2][1]) * inv_det,
          (m[0][2] * m[2][1] - m[0][1] * m[2][2]) * inv_det,
          (m[0][1] * m[1][2] - m[0][2] * m[1][1]) * inv_det}},
        {{(m[1][2] * m[2][0] - m[1][0] * m[2][2]) * inv_det,
          (m[0][0] * m[2][2] - m[0][2] * m[2][0]) * inv_det,
          (m[0][2] * m[1][0] - m[0][0] * m[1][2]) * inv_det}},
        {{(m[1][0] * m[2][1] - m[1][1] * m[2][0]) * inv_det,
          (m[0][1] * m[2][0] - m[0][0] * m[2][1]) * inv_det,
          (m[0][0] * m[1][1] - m[0][1] * m[1][0]) * inv_det}},
    }};
}

double parse_number(const std::string& token) {
    std::size_t used = 0;
    const double result = std::stod(token, &used);
    if (used != token.size()) {
        throw std::invalid_argument("invalid numeric token");
    }
    return result;
}

std::filesystem::path path_from_utf8(const char* value) {
    if (value == nullptr || *value == '\0') {
        throw std::invalid_argument("empty file path");
    }
#if defined(_WIN32)
    return std::filesystem::u8path(value);
#else
    return std::filesystem::path(value);
#endif
}

}  // namespace

struct XrdNativeAtom {
    double x;
    double y;
    double z;
    double occupancy;
    double b_iso;
    double a[5];
    double b[5];
    double c;
};

struct XrdNativePeak {
    double two_theta;
    double intensity;
    std::int32_t h;
    std::int32_t k;
    std::int32_t l;
};

XRD_EXPORT const char* xrd_native_version() {
    return "1.0.0";
}

XRD_EXPORT const char* xrd_last_error() {
    return g_last_error.c_str();
}

XRD_EXPORT void xrd_free_doubles(double* values) {
    delete[] values;
}

XRD_EXPORT void xrd_free_indices(std::int64_t* values) {
    delete[] values;
}

XRD_EXPORT double* xrd_load_dia_utf8(
    const char* path_utf8,
    std::size_t phase_count,
    std::size_t* row_count
) {
    g_last_error.clear();
    if (row_count == nullptr) {
        g_last_error = "row_count pointer is null";
        return nullptr;
    }
    *row_count = 0;
    try {
        std::ifstream input(path_from_utf8(path_utf8));
        if (!input) {
            throw std::runtime_error("could not open DIA file");
        }

        std::string line;
        std::getline(input, line);  // metadata/header line
        const std::size_t column_count = 5 + phase_count;
        std::vector<double> rows;
        while (std::getline(input, line)) {
            std::istringstream stream(line);
            std::vector<std::string> tokens;
            std::string token;
            while (stream >> token) {
                tokens.push_back(token);
            }
            if (tokens.empty() || tokens.size() < 4) {
                continue;
            }
            const std::size_t start = rows.size();
            try {
                const double x = parse_number(tokens[0]);
                const double observed = parse_number(tokens[1]);
                const double calculated = parse_number(tokens[2]);
                const double background = parse_number(tokens[3]);
                rows.resize(start + column_count, 0.0);
                rows[start] = x;
                rows[start + 1] = observed;
                rows[start + 2] = calculated;
                rows[start + 3] = background;
                rows[start + 4] = observed - calculated;
                for (std::size_t phase = 0; phase < phase_count; ++phase) {
                    const std::size_t token_index = 4 + phase;
                    if (token_index < tokens.size()) {
                        rows[start + 5 + phase] = parse_number(tokens[token_index]);
                    }
                }
            } catch (const std::exception&) {
                rows.resize(start);
                continue;
            }
        }

        const std::size_t count = rows.size() / column_count;
        if (count == 0) {
            return nullptr;
        }
        double max_observed = rows[1];
        for (std::size_t row = 1; row < count; ++row) {
            max_observed = std::max(max_observed, rows[row * column_count + 1]);
        }
        if (max_observed > 0.0) {
            for (std::size_t row = 0; row < count; ++row) {
                const std::size_t offset = row * column_count;
                for (std::size_t column = 1; column < column_count; ++column) {
                    rows[offset + column] /= max_observed;
                }
            }
        }

        double* result = new double[rows.size()];
        std::copy(rows.begin(), rows.end(), result);
        *row_count = count;
        return result;
    } catch (const std::exception& error) {
        g_last_error = error.what();
        return nullptr;
    } catch (...) {
        g_last_error = "unknown DIA parsing error";
        return nullptr;
    }
}

XRD_EXPORT std::int64_t* xrd_local_maxima(
    const double* values,
    std::size_t value_count,
    double threshold_fraction,
    std::size_t* peak_count
) {
    g_last_error.clear();
    if (peak_count == nullptr) {
        g_last_error = "peak_count pointer is null";
        return nullptr;
    }
    *peak_count = 0;
    if (values == nullptr || value_count < 3) {
        return nullptr;
    }
    try {
        double maximum = values[0];
        for (std::size_t index = 1; index < value_count; ++index) {
            if (std::isnan(values[index])) {
                maximum = std::numeric_limits<double>::quiet_NaN();
                break;
            }
            maximum = std::max(maximum, values[index]);
        }
        const double threshold = maximum * threshold_fraction;
        std::vector<std::int64_t> peaks;
        for (std::size_t index = 1; index + 1 < value_count; ++index) {
            if (values[index] > values[index - 1]
                && values[index] > values[index + 1]
                && values[index] > threshold) {
                peaks.push_back(static_cast<std::int64_t>(index));
            }
        }
        if (peaks.empty()) {
            return nullptr;
        }
        std::int64_t* result = new std::int64_t[peaks.size()];
        std::copy(peaks.begin(), peaks.end(), result);
        *peak_count = peaks.size();
        return result;
    } catch (const std::exception& error) {
        g_last_error = error.what();
        return nullptr;
    } catch (...) {
        g_last_error = "unknown peak-search error";
        return nullptr;
    }
}

XRD_EXPORT int xrd_calculate_reference_pattern(
    const double* cell,
    const XrdNativeAtom* atoms,
    std::size_t atom_count,
    double wavelength,
    int include_kalpha2,
    XrdNativePeak* output,
    std::size_t output_capacity,
    std::size_t* required_count
) {
    g_last_error.clear();
    if (required_count == nullptr) {
        g_last_error = "required_count pointer is null";
        return -1;
    }
    *required_count = 0;
    if (cell == nullptr || atoms == nullptr || atom_count == 0) {
        return 0;
    }
    try {
        const double a = cell[0];
        const double b = cell[1];
        const double c = cell[2];
        const double alpha = cell[3] * kPi / 180.0;
        const double beta = cell[4] * kPi / 180.0;
        const double gamma = cell[5] * kPi / 180.0;
        const double sin_gamma = std::sin(gamma);
        if (std::abs(sin_gamma) <= 1e-12) {
            throw std::runtime_error("invalid unit-cell gamma angle");
        }

        const Vec3 avec{a, 0.0, 0.0};
        const Vec3 bvec{b * std::cos(gamma), b * sin_gamma, 0.0};
        const double cx = c * std::cos(beta);
        const double cy = c * (std::cos(alpha) - std::cos(beta) * std::cos(gamma)) / sin_gamma;
        const double cz = std::sqrt(std::max(c * c - cx * cx - cy * cy, 1e-12));
        const Vec3 cvec{cx, cy, cz};
        const double volume = dot(avec, cross(bvec, cvec));
        if (!std::isfinite(volume) || std::abs(volume) <= 1e-18) {
            throw std::runtime_error("invalid unit-cell volume");
        }
        const Vec3 astar = scale(cross(bvec, cvec), 1.0 / volume);
        const Vec3 bstar = scale(cross(cvec, avec), 1.0 / volume);
        const Vec3 cstar = scale(cross(avec, bvec), 1.0 / volume);

        std::vector<std::array<double, 2>> radiation{{wavelength, 1.0}};
        if (include_kalpha2 != 0) {
            radiation.push_back({wavelength * (1.54439 / 1.54056), 0.5});
        }
        const double shortest_wavelength = std::min_element(
            radiation.begin(), radiation.end(),
            [](const auto& left, const auto& right) { return left[0] < right[0]; }
        )->at(0);
        const double max_two_theta = 120.0;
        const double q_max = 2.0 * std::sin(max_two_theta * kPi / 360.0) / shortest_wavelength;
        const std::array<std::array<double, 3>, 3> reciprocal{{
            {{astar.x, bstar.x, cstar.x}},
            {{astar.y, bstar.y, cstar.y}},
            {{astar.z, bstar.z, cstar.z}},
        }};
        const auto reciprocal_inverse = invert_3x3(reciprocal);
        std::array<int, 3> bounds{};
        for (std::size_t row = 0; row < 3; ++row) {
            const auto& r = reciprocal_inverse[row];
            const double row_norm = std::sqrt(r[0] * r[0] + r[1] * r[1] + r[2] * r[2]);
            bounds[row] = static_cast<int>(std::max(3.0, std::ceil(q_max * row_norm) + 1.0));
        }

        struct AccumulatedPeak {
            double two_theta;
            double intensity;
            std::int32_t h;
            std::int32_t k;
            std::int32_t l;
        };
        std::map<std::int64_t, AccumulatedPeak> grouped;
        constexpr double tolerance = 1e-5;
        constexpr double cthm1 = 0.7998;

        for (int h = -bounds[0]; h <= bounds[0]; ++h) {
            for (int k = -bounds[1]; k <= bounds[1]; ++k) {
                for (int l = -bounds[2]; l <= bounds[2]; ++l) {
                    if (h == 0 && k == 0 && l == 0) {
                        continue;
                    }
                    const Vec3 q = add(scale(astar, static_cast<double>(h)),
                                       scale(bstar, static_cast<double>(k)),
                                       scale(cstar, static_cast<double>(l)));
                    const double qn = norm(q);
                    if (qn <= 1e-12) {
                        continue;
                    }
                    const double d_spacing = 1.0 / qn;
                    for (const auto& line : radiation) {
                        const double line_wavelength = line[0];
                        const double line_weight = line[1];
                        const double argument = line_wavelength / (2.0 * d_spacing);
                        if (argument <= 0.0 || argument >= 1.0) {
                            continue;
                        }
                        const double theta = std::asin(argument);
                        const double two_theta = 2.0 * theta * 180.0 / kPi;
                        if (two_theta <= 0.0 || two_theta > max_two_theta) {
                            continue;
                        }
                        const double sine_theta = std::sin(theta);
                        const double cosine_theta = std::cos(theta);
                        const double s_sq = (sine_theta / line_wavelength) * (sine_theta / line_wavelength);
                        double real_f = 0.0;
                        double imag_f = 0.0;
                        for (std::size_t atom_index = 0; atom_index < atom_count; ++atom_index) {
                            const auto& atom = atoms[atom_index];
                            double atomic_f = atom.c;
                            for (std::size_t coefficient = 0; coefficient < 5; ++coefficient) {
                                atomic_f += atom.a[coefficient] * std::exp(-atom.b[coefficient] * s_sq);
                            }
                            const double thermal = std::exp(-std::max(0.0, atom.b_iso) * s_sq);
                            const double phase = 2.0 * kPi * (
                                static_cast<double>(h) * atom.x
                                + static_cast<double>(k) * atom.y
                                + static_cast<double>(l) * atom.z
                            );
                            const double amplitude = atom.occupancy * atomic_f * thermal;
                            real_f += amplitude * std::cos(phase);
                            imag_f += amplitude * std::sin(phase);
                        }
                        const double structure_intensity = real_f * real_f + imag_f * imag_f;
                        if (structure_intensity <= 1e-10) {
                            continue;
                        }
                        const double safe_sine = std::max(sine_theta, 1e-12);
                        const double safe_cosine = std::max(cosine_theta, 1e-12);
                        const double polarization = 1.0 + cthm1 * std::pow(std::cos(2.0 * theta), 2.0);
                        const double lorentz_polarization = polarization /
                            ((1.0 + cthm1) * safe_sine * safe_sine * safe_cosine);
                        const double intensity = line_weight * structure_intensity * lorentz_polarization;
                        // Python's round() and NumPy both use ties-to-even.
                        const auto key = static_cast<std::int64_t>(std::nearbyint(two_theta / tolerance));
                        const auto found = grouped.find(key);
                        if (found == grouped.end()) {
                            grouped.emplace(key, AccumulatedPeak{
                                two_theta,
                                intensity,
                                static_cast<std::int32_t>(h),
                                static_cast<std::int32_t>(k),
                                static_cast<std::int32_t>(l),
                            });
                        } else {
                            found->second.intensity += intensity;
                        }
                    }
                }
            }
        }

        double maximum_intensity = 0.0;
        for (const auto& item : grouped) {
            maximum_intensity = std::max(maximum_intensity, item.second.intensity);
        }
        std::vector<XrdNativePeak> peaks;
        if (maximum_intensity > 0.0) {
            for (const auto& item : grouped) {
                const auto& peak = item.second;
                const double relative = peak.intensity / maximum_intensity;
                if (relative >= 1e-5) {
                    peaks.push_back({
                        peak.two_theta,
                        relative * 100.0,
                        peak.h,
                        peak.k,
                        peak.l,
                    });
                }
            }
        }
        std::sort(peaks.begin(), peaks.end(), [](const auto& left, const auto& right) {
            return left.two_theta < right.two_theta;
        });
        *required_count = peaks.size();
        if (output == nullptr || output_capacity == 0) {
            return 0;
        }
        if (output_capacity < peaks.size()) {
            g_last_error = "reference-pattern output buffer is too small";
            return 1;
        }
        std::copy(peaks.begin(), peaks.end(), output);
        return 0;
    } catch (const std::exception& error) {
        g_last_error = error.what();
        return -1;
    } catch (...) {
        g_last_error = "unknown reference-pattern error";
        return -1;
    }
}
