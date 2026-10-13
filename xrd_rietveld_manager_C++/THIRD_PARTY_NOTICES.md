This application source is licensed under GNU GPL version 2 or, at your option, any later version (GPL-2.0-or-later); see ../LICENSE. This license applies to the project source, not to separately installed third-party packages or user-selected input data.

# Third-party notices

## XrayDB

The application reads Waasmaier–Kirfel elastic X-ray scattering coefficients at runtime from the separately installed `xraydb` Python package. This distribution contains neither XrayDB source code nor its SQLite database. Install it from the upstream Python package index using `requirements.txt`.

XrayDB states that its Python package code is available under the MIT License. Its database files and data sources are dedicated to CC0 1.0 to the extent possible and unless otherwise stated; check the upstream notice for current details. The coefficient source is D. Waasmaier and A. Kirfel (1995), “New analytical scattering-factor functions for free atoms and ions,” *Acta Crystallographica Section A*, 51, 416–431, [doi:10.1107/S0108767394013292](https://doi.org/10.1107/S0108767394013292).

- [XrayDB licensing and installation](https://xraypy.github.io/XrayDB/installation.html)
- [XrayDB Python API](https://xraypy.github.io/XrayDB/python.html)
- [XrayDB source repository](https://github.com/xraypy/XrayDB)

The project does not copy Profex, BGMN, Materials Project, FullProf, GSAS, GSAS-II, or VESTA source code or bundled assets in this distribution. Their names are used only to identify supported input workflows or provide attribution. Users are responsible for having rights to input files they select and for checking source-specific terms when redistributing exported data.
