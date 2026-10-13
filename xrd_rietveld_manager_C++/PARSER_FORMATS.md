# Rietveld 프로파일 입력

2026-10-13: Profex/BGMN DIA, GSAS/EXPGUI LIVEPLOT CSV,
GSAS-II histogram CSV, FullProf WinPLOTR PRF 입력을 지원합니다.
DATA의 기존 파일 추가 버튼에서 서로 다른 형식의 파일을 함께 선택할 수 있습니다.
선택한 파일의 요약에 인식된 형식이 표시됩니다.

## 구조

기존에는 `DataLoader.load_dia()`에 DIA 해석, 정규화, 색상 및 레이어 초기화가
모두 들어 있었으며 일반 파일 추가와 Figure Set 재연결이 이 함수를 직접 호출했습니다.

현재 구조:

```text
FileManager / Figure Set
  -> DataLoader.load()
    -> profile_parsers.parse_profile()
      -> parse_dia()          : Profex / BGMN
      -> parse_gsas_csv()     : GSAS-II CSV 또는 GSAS LIVEPLOT CSV
      -> parse_fullprof_prf() : FullProf WinPLOTR
    -> ProfileData.normalized(): 공통 검증, 정규화, Difference 재계산
    -> DataLoader: 배열 캐시, 색상, 사용 가능한 레이어 초기화
  -> 기존 플롯 / 템플릿 / 내보내기
```

- `profile_parsers.py`: UI와 독립적인 형식별 파서와 공통 데이터 구조.
- `data_loader.py`: 파서 결과를 기존 리스트/NumPy 인터페이스에 연결.
- `file_manager.py`: 지원 확장자 선택, 실패한 파일 제외, 오류 안내.
- `figure_set_manager.py`: 새 형식의 원본 파일 재연결 지원.
- `layers_manager.py`: 원본에 없는 레이어는 표시 목록에서 제외.
- 기존 `load_dia()` 호출도 호환용 메서드로 유지됩니다.
- DIA 수치 로딩은 기존 C++ DLL을 우선 사용하고, 없으면 Python으로 읽습니다.
  새 CSV/PRF의 형식 해석은 Python이며, 기존 C++ 계산 기능은 유지됩니다.

## 프로그램별 사용할 파일

| 프로그램 | 지원 입력 | 준비 방법 |
|---|---|---|
| Profex / BGMN | `.dia` | 기존 방식 그대로 사용 |
| GSAS-II | `.csv` | Export → Powder data as → histogram CSV file. 구버전에서는 CSV file로 표시될 수 있음 |
| GSAS / EXPGUI | `.csv`, `.txt` | LIVEPLOT → Export plot → as .csv file. X축은 2-Theta, Y축은 선형 강도 사용 |
| FullProf | `.prf` | `2Theta Yobs Ycal ...` 헤더와 프로파일 점 개수를 포함하는 WinPLOTR용 PRF 사용 |

GSAS-II는 열 이름으로 `x`, `y_obs`, `y_calc`, `y_bkg`를 식별합니다.
`weight`와 `Q`를 강도로 읽지 않습니다. `stacked CSV`에는 계산 패턴이 없으므로
그 형식은 안내와 함께 거부합니다. 반사 목록만 담긴 CSV도 프로파일로 읽지 않습니다.

GSAS LIVEPLOT의 설명형 헤더, 앞쪽 빈 CSV 열, 프로파일 옆에 함께 출력되는
반사 정보를 구분합니다. FullProf도 프로파일 점 개수와 헤더를 기준으로 읽어
옆이나 끝에 붙은 Bragg 반사 정보를 프로파일 강도로 해석하지 않습니다.

## 처리 기준과 범위

- 현재는 **일정 파장의 2θ 프로파일**을 지원합니다. 명시적으로 TOF, d, Q,
  에너지 축인 파일은 안내와 함께 거부하며 자동 축 변환은 하지 않습니다.
  GSAS-II의 `Instparm: Type`을 확인합니다. 메타데이터 없는 일반 `x` 헤더는
  이 프로그램의 2θ 열로 해석하므로 입력 파일의 단위를 확인해야 합니다.
- `.gpx`, `.EXP`, `.pcr` 프로젝트/제어 파일 직접 읽기는 지원하지 않습니다.
- 관측값과 계산값이 필수입니다. 파일에 없는 Background는 만들지 않으며,
  배경 차감 기능은 그 파일에 대해 적용되지 않습니다.
- 강도는 기존 DIA와 동일하게 관측 최댓값으로 나눕니다. 모든 강도 열에 같은
  계수를 사용하며 X축은 변경하지 않습니다. 내림차순 X는 전체 열과 함께 뒤집습니다.
- Difference는 항상 정규화된 Observed−Calculated입니다. FullProf/LIVEPLOT에서
  내보낸 표시용 잔차의 수직 오프셋은 가져오지 않습니다.
- FullProf의 제외 구간 표시와 저장된 잔차 마스킹은 가져오지 않습니다. 계산된
  Difference는 파일에 들어 있는 모든 프로파일 점에 대한 Obs−Calc입니다.
- 이번 확장은 **Observed / Calculated / Background / Difference 프로파일**이 대상입니다.
  CSV/PRF의 Bragg 반사 목록을 별도 막대로 표시하거나 상별 전체 계산 곡선을
  복원하지 않습니다. DIA의 기존 상별 곡선과 CIF 참조 기능은 유지됩니다.
- 숫자 오류, NaN/Inf, 점 개수 불일치, 중복되거나 순서가 섞인 X축은 오류로 처리합니다.
  DIA의 기존 잘못된 행 건너뛰기 동작은 호환성을 위해 유지합니다.
- 표준 헤더가 없는 PRF 변형은 추측해서 읽지 않고 지원 형식 안내를 표시합니다.

## 검증

- 자동 테스트 **57개 통과**: 기존 39개 + 신규 18개.
- GSAS/GSAS-II는 공식 내보내기 코드의 형식으로 만든 합성 fixture로 열 매핑,
  가중치 제외, 반사 행 분리, 잔차 오프셋 제거를 확인했습니다.
- 실제 Tk 애플리케이션에서 네 형식 혼합 입력, 잘못된 파일 제외, 배경 누락,
  겹침/분할/3D, 배경 차감, 템플릿 재적용, XY CSV 내보내기를 확인했습니다.
- 사용자의 실제 GSAS/FullProf 결과 파일은 아직 제공되지 않았습니다.

재실행:

```powershell
python -B -m unittest discover -s tests -q
python -B validation/verify_multiformat_ui.py
```

Python 3.13과 기존 프로그램 의존성이 있는 환경에서 실행했습니다.
`validation/mixed_profiles_smoke.png`는 기능 점검용 합성 데이터의 플롯입니다.

