# LAB×ACE²-XRD Rietveld Plot Visualizer

**Version:** 1.0.0

## English

### About

LAB×ACE²-XRD Rietveld Plot Visualizer is an independently implemented visualization companion for X-ray diffraction (XRD) and Rietveld workflows. It reads supported data exported by Profex/BGMN and other refinement programs so users can plot and compare results.

The project was inspired by the scientific workflows and materials-data experience of Profex and the Materials Project. It is an add-on in the workflow sense: a complementary tool used alongside those projects, not an official plugin, extension, or component of either one. It is not affiliated with, sponsored by, or endorsed by Profex, BGMN, or the Materials Project.

To the best of the developer’s knowledge, no source code from Profex, BGMN, or the Materials Project was copied into this application. The application works with data files users select or export themselves.

### Data and supported formats

Supported inputs include Profex/BGMN DIA profiles, GSAS and GSAS-II CSV exports, and FullProf WinPLOTR PRF profiles (constant-wavelength 2θ data). See [PARSER_FORMATS.md](xrd_rietveld_manager_C++/PARSER_FORMATS.md) for details.

No CIF reference structures or example CIF files are bundled in this distribution. Import a CIF you obtained yourself through the application. For example, you may download a structure CIF from Materials Project and load it locally; this application does not provide an official Materials Project API integration.

### Run

Requires Python 3.13 and the packages in `xrd_rietveld_manager_C++/requirements.txt`. Install them first:

```powershell
python -m pip install -r .\xrd_rietveld_manager_C++\requirements.txt
```

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" ".\LAB×ACE²-XRD Rietveld Plot Visualizer.py"
```

The shared displayed product name is defined in `xrd_rietveld_manager_C++/xrd_rietveld_manager/branding.py`. Internal Python package names, the C++ DLL name, and saved-file extensions are retained for compatibility. The existing `xrd_rietveld_manager_C++/run_ui2.py` entry point remains available.

### License and intended use

This program is licensed under the GNU General Public License version 2 or, at your option, any later version (`GPL-2.0-or-later`); see [LICENSE](LICENSE). It was developed for non-commercial academic and research use. That purpose statement describes the project’s intent; it does not limit the GPL permissions. Commercial use, modification, and redistribution are allowed when the license terms are followed.

No third-party CIF structures, Profex/VESTA binaries, logos, screenshots, manuals, or example profiles are intentionally included in this distribution. The parser test profiles are synthetic. The optional native accelerator is provided as C++ source and can be built locally; a prebuilt DLL is not included.

See [THIRD_PARTY_NOTICES.md](xrd_rietveld_manager_C++/THIRD_PARTY_NOTICES.md) for dependency and data attribution. The GPL applies to this project’s source; separately installed dependencies and user-selected input data retain their own terms.

### References

When using source software or data in research, cite the relevant work. For Materials Project data, include the database version used and any applicable property-specific methods references.

1. N. Döbelin and R. Kleeberg (2015). “Profex: a graphical user interface for the Rietveld refinement program BGMN.” *Journal of Applied Crystallography*, 48, 1573–1580. [https://doi.org/10.1107/S1600576715014685](https://doi.org/10.1107/S1600576715014685)
2. M. K. Horton et al. (2025). “Accelerated data-driven materials science with the Materials Project.” *Nature Materials*, 24, 1522–1532. [https://doi.org/10.1038/s41563-025-02272-0](https://doi.org/10.1038/s41563-025-02272-0)
3. A. Jain et al. (2013). “Commentary: The Materials Project: A materials genome approach to accelerating materials innovation.” *APL Materials*, 1, 011002. [https://doi.org/10.1063/1.4812323](https://doi.org/10.1063/1.4812323)

## 한국어

### 프로그램 소개

LAB×ACE²-XRD Rietveld Plot Visualizer는 X선 회절(XRD) 리트벨트 분석 결과를 그래프로 확인하고 비교할 수 있도록 별도로 개발한 시각화 프로그램입니다. Profex/BGMN을 비롯한 분석 프로그램에서 내보낸 데이터를 불러와 활용할 수 있습니다.

이 프로그램은 Profex와 Materials Project의 분석 환경과 데이터 활용 방식에서 아이디어를 얻어, 기존 분석 작업을 보완하는 도구로 제작했습니다. 두 프로젝트의 공식 플러그인이나 구성요소는 아니며, Profex·BGMN·Materials Project와 제휴하거나 후원·승인받은 관계도 없습니다.

개발자가 확인한 바로는 해당 프로젝트의 소스 코드를 가져오지 않고 독립적으로 구현했습니다. 분석 프로그램에서 내보낸 파일이나 사용자가 직접 선택한 데이터를 불러와 처리합니다.

### 데이터 및 지원 형식

Profex/BGMN DIA 프로파일, GSAS 및 GSAS-II CSV 파일, FullProf WinPLOTR PRF 프로파일(상수 파장 2θ 데이터)을 지원합니다. 형식별 지원 범위와 파서 정보는 [PARSER_FORMATS.md](xrd_rietveld_manager_C++/PARSER_FORMATS.md)에서 확인할 수 있습니다.

이 배포본에는 CIF 예제나 기준 구조 파일이 포함되어 있지 않습니다. 사용자가 준비한 CIF 파일을 프로그램에서 직접 불러오면 됩니다. Materials Project에서 구조 CIF를 내려받아 사용할 수도 있지만, 이 프로그램이 Materials Project에 직접 접속하거나 API를 통해 데이터를 가져오지는 않습니다.

### 실행 방법

Python 3.13과 프로젝트 소스에 명시된 필수 패키지가 필요합니다.

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" ".\LAB×ACE²-XRD Rietveld Plot Visualizer.py"
```

프로그램 화면에 표시되는 제품명은 `xrd_rietveld_manager_C++/xrd_rietveld_manager/branding.py`에서 관리합니다. 내부 Python 패키지명, C++ DLL 이름, 저장 파일 확장자는 기존 호환성을 위해 유지했습니다. 기존 실행 파일인 `xrd_rietveld_manager_C++/run_ui2.py`도 계속 사용할 수 있습니다.

### 라이선스 및 이용 목적

이 프로그램의 소스 코드는 GNU GPL 2판 또는 이후 버전 중 선택하여 사용할 수 있습니다(`GPL-2.0-or-later`). 자세한 조건은 [LICENSE](LICENSE)를 확인하세요. 비영리 학술·연구 목적으로 개발했지만, 이 문구는 개발 배경을 설명합니다. GPL 조건을 지키는 한 상업적 이용·수정·재배포도 허용됩니다.

제3자 CIF 구조, Profex/VESTA 실행 파일, 로고, 스크린샷, 설명서 또는 예제 프로파일은 이 배포본에 의도적으로 포함하지 않았습니다. 파서 검증용 프로파일은 형식 확인을 위해 만든 합성 데이터입니다. 선택 기능인 네이티브 가속기는 C++ 소스로 제공하며, 사전 빌드 DLL은 포함하지 않습니다.

의존성과 데이터 출처는 [THIRD_PARTY_NOTICES.md](xrd_rietveld_manager_C++/THIRD_PARTY_NOTICES.md)에서 확인할 수 있습니다. GPL은 이 프로젝트의 소스에 적용되며, 별도로 설치하는 의존성과 사용자가 선택하는 입력 데이터에는 각각의 조건이 적용됩니다.

### 참고 문헌

연구에 Profex나 Materials Project의 소프트웨어 또는 데이터를 활용했다면 해당 자료를 인용해 주세요. Materials Project 데이터를 사용한 연구를 발표할 때는 사용한 데이터베이스 버전과 해당 물성에 적용되는 방법론 논문도 함께 확인해 인용하는 것이 좋습니다.

1. N. Döbelin and R. Kleeberg (2015). “Profex: a graphical user interface for the Rietveld refinement program BGMN.” *Journal of Applied Crystallography*, 48, 1573–1580. [https://doi.org/10.1107/S1600576715014685](https://doi.org/10.1107/S1600576715014685)
2. M. K. Horton et al. (2025). “Accelerated data-driven materials science with the Materials Project.” *Nature Materials*, 24, 1522–1532. [https://doi.org/10.1038/s41563-025-02272-0](https://doi.org/10.1038/s41563-025-02272-0)
3. A. Jain et al. (2013). “Commentary: The Materials Project: A materials genome approach to accelerating materials innovation.” *APL Materials*, 1, 011002. [https://doi.org/10.1063/1.4812323](https://doi.org/10.1063/1.4812323)
