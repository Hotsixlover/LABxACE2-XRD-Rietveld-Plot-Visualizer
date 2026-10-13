# LAB×ACE²-XRD Rietveld Plot Visualizer — Source Package

## English

This folder contains the modular Python application and optional C++ acceleration source. The displayed product identity is centralized in `xrd_rietveld_manager/branding.py`. A prebuilt DLL is omitted; the application uses its Python fallback until you build the accelerator locally.

The application is an independently implemented visualization companion for XRD/Rietveld workflows. It was inspired by Profex and the Materials Project and is intended to be used alongside their data and workflows. It is not an official plugin or affiliated product. To the best of the developer’s knowledge, no source code from those projects was copied.

Supported profile inputs include Profex/BGMN DIA, GSAS/GSAS-II CSV, and FullProf WinPLOTR PRF (constant-wavelength 2θ). See [PARSER_FORMATS.md](PARSER_FORMATS.md) for parser details.

No CIF structures or examples are included. Load a CIF selected by the user from the application. Install runtime dependencies from this folder with `python -m pip install -r requirements.txt`. The existing `run_ui2.py` compatibility entry point remains available:

```powershell
python run_ui2.py
```

Internal package and native DLL/file-format compatibility identifiers are unchanged. See the [main README](../README.md) for the bilingual project description and references to Profex and the Materials Project.

### License and intended use

This software is licensed under GNU GPL version 2 or, at your option, any later version (`GPL-2.0-or-later`); see [LICENSE](../LICENSE). It was developed for non-commercial academic and research use, but that purpose statement does not restrict the GPL permissions. Commercial use, modification, and redistribution are permitted under the license terms.

## 한국어

이 폴더에는 프로그램의 Python 소스 코드와 선택적 C++ 가속기 소스가 들어 있습니다. 사전 빌드 DLL은 제외했으며, 직접 빌드하기 전까지는 Python 대체 계산 경로를 사용합니다. 화면에 표시되는 제품명은 `xrd_rietveld_manager/branding.py`에서 한곳에 관리합니다.

이 프로그램은 XRD 리트벨트 분석 결과를 시각화하는 독립 구현 도구입니다. Profex와 Materials Project에서 아이디어를 얻어 두 프로젝트의 데이터와 분석 작업 흐름을 보완하도록 만들었습니다. 공식 플러그인이나 제휴 제품은 아니며, 개발자가 확인한 바로는 해당 프로젝트의 소스 코드를 가져오지 않았습니다.

Profex/BGMN DIA, GSAS/GSAS-II CSV, FullProf WinPLOTR PRF(상수 파장 2θ) 프로파일을 지원합니다. 자세한 내용은 [PARSER_FORMATS.md](PARSER_FORMATS.md)를 참고하세요.

이 배포본에는 CIF 구조 파일이나 예제 CIF가 들어 있지 않습니다. 사용자가 준비한 CIF를 프로그램에서 직접 불러오면 됩니다. 실행 패키지는 `python -m pip install -r requirements.txt`로 설치하세요. 기존 실행 경로인 `run_ui2.py`도 계속 사용할 수 있습니다.

```powershell
python run_ui2.py
```

기존 프로그램과의 호환성을 위해 내부 패키지명과 DLL·파일 형식 식별자는 그대로 유지했습니다. 전체 소개와 Profex·Materials Project 참고 문헌은 [상위 README](../README.md)에서 확인할 수 있습니다.

### 라이선스 및 이용 목적

이 프로그램의 소스 코드는 GNU GPL 2판 또는 이후 버전 중 선택하여 사용할 수 있습니다(`GPL-2.0-or-later`). 자세한 조건은 [LICENSE](../LICENSE)를 확인하세요. 비영리 학술·연구 목적으로 개발했지만, 이 문구는 개발 배경을 설명합니다. GPL 조건을 지키는 한 상업적 이용·수정·재배포도 허용됩니다.
