# C++ native acceleration

The UI and state model remain Python, while the CPU-heavy numerical kernels
run in `xrd_rietveld_manager/native/xrd_native.cpp`:

- DIA numeric parsing and normalization
- CIF reference-pattern enumeration and structure-factor calculation
- local-maximum detection for phase sticks

The bridge uses a stable C ABI through Python `ctypes`, so the DLL is not tied
to one CPython minor version. If the DLL is absent or a native call fails, the
existing Python/NumPy implementation is used automatically.

## Build on Windows

Install either Visual Studio Build Tools with **Desktop development with C++**,
or CMake and a C++17 compiler. Then run from PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_native.ps1
```

The source distribution does not include a prebuilt DLL. The script writes `xrd_rietveld_manager/native/xrd_native.dll` locally. The accelerator itself needs no Python package to build; the application reference-peak calculation also requires XrayDB from `requirements.txt`.

## Diagnostics and opt-out

```python
from xrd_rietveld_manager.native_backend import backend_status
print(backend_status())
```

Set `XRDRM_DISABLE_NATIVE=1` before launching to force the Python fallback.
Set `XRDRM_NATIVE_LIBRARY` to load a DLL from a custom location.
