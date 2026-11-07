# Processor Scheduling Simulator

운영체제 수업에서 진행한 **프로세서 스케줄링 시뮬레이터**를 여러 개발 브랜치의 코드를 정리해 하나의 실행 가능한 형태로 통합한 프로젝트입니다.

기존 프로젝트의 FCFS / RR / SPN / SRTN / HRRN 구현, GPT 질문 시나리오용 DRR(Dynamic Round Robin), P-Core / E-Core 전력 모델, PyQt GUI를 하나의 공통 스케줄링 엔진으로 연결했습니다.

## 주요 기능

- FCFS (First-Come, First-Served)
- RR (Round Robin)
- SPN (Shortest Process Next)
- SRTN (Shortest Remaining Time Next)
- HRRN (Highest Response Ratio Next)
- DRR (Dynamic Round Robin)
- 최대 4개 코어 구성
  - P-Core 최대 3개
  - E-Core 최대 1개
- P-Core / E-Core 처리 성능 및 전력 사용량 계산
- 프로세스별 AT / BT / WT / TT / NTT 계산
- Core별 Gantt Chart 표시
- GPT 모델 / 질문 복잡도를 이용한 DRR 프로세스 생성
- DRR의 복잡도 기반 P/E-Core 우선 배치
- DRR의 Remaining BT 기반 Dynamic Time Quantum
- BT가 30 이상인 프로세스의 30 work-unit 강제 종료 정책

## 프로세서 모델

| Core | 처리량 | 동작 전력 | 시동 전력 |
|---|---:|---:|---:|
| P-Core | 2 work units / sec | 3 W / sec | 0.5 W |
| E-Core | 1 work unit / sec | 1 W / sec | 0.1 W |

프로젝트의 기존 정의를 따라 각 tick에서 사용된 전력 값을 누적해 표시합니다.

## DRR 정책

DRR은 일반 RR에 다음 정책을 추가합니다.

1. Remaining BT와 Complexity를 이용해 P-Core / E-Core 우선순위를 정합니다.
   - Remaining BT가 1 이하이거나 Complexity가 1~5이면 E-Core 우선
   - 그 외에는 P-Core 우선
2. 선호 Core가 사용 중이면 유휴 상태의 다른 Core를 사용하여 불필요한 대기를 줄입니다.
3. Preemption 후 Remaining BT에 따라 Time Quantum을 다시 계산합니다.

| Remaining BT | Time Quantum |
|---:|---:|
| 1 ~ 10 | 2 |
| 11 ~ 20 | 4 |
| 21 ~ 30 | 6 |
| 31 이상 | 8 |

## 실행 환경

- Python 3.9.x
- PyQt5 5.15.7

### 설치

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## GUI 실행

```bash
python ui.py
```

화면·스타일·이미지는 `assets/`에서 스크립트 위치를 기준으로 불러옵니다. 다른 작업 폴더에서 `ui.py`의 전체 경로로 실행해도 같은 화면을 사용할 수 있으며, 실행한 작업 폴더는 바뀌지 않습니다.

1. 스케줄링 알고리즘을 선택합니다.
2. Core 0~3을 P-Core / E-Core / Off 중에서 선택합니다.
3. 프로세스를 직접 입력하거나 Random 버튼으로 생성합니다.
4. RR은 Time Quantum을 지정합니다.
5. DRR은 GPT 모델과 Complexity를 선택하면 시나리오용 프로세스 3개가 생성됩니다.
6. 실행 버튼을 누르면 Gantt Chart, 처리 결과, Core별 전력 사용량이 표시됩니다.

프로세스·결과·Gantt 표는 표시 전용입니다. 프로세스는 기존 추가·삭제 버튼으로 관리하며, 표 정렬은 그대로 사용할 수 있습니다. 프로세스·알고리즘·코어 또는 RR의 Time Quantum을 변경하면 이전 결과가 초기화되므로 다시 실행해 주세요.

프로세스와 Gantt Chart는 왼쪽에서, 실행 설정과 처리 결과는 오른쪽에서 확인합니다. 실행 시간·평균 대기 시간·평균 NTT·총 전력 사용량은 상단 요약 카드로 표시하며, 작은 창에서는 스크롤로 각 영역에 접근할 수 있습니다. 알고리즘 설명은 선택 상자 아래에 표시됩니다.

타임라인은 최대 4개 코어의 행과 가로 스크롤에 맞춰 높이를 유지하며, 여유 공간은 프로세스 목록에 배분합니다.

실행·랜덤 생성·추가·초기화·삭제와 입력 증감 버튼은 기존 이미지 리소스를 사용합니다. DRR의 GPT 모델·복잡도는 그림과 이름으로 선택하며, 선택한 항목은 컬러 아이콘으로 표시됩니다.

## CLI 데모

GUI 없이 DRR 예제를 실행할 수도 있습니다.

```bash
python Operating_System.py
```

## 테스트

권장 Python 3.9 환경에서 스케줄링 엔진과 GUI 입력 흐름을 `unittest`로 검증할 수 있습니다.

```bash
python -m unittest discover -s tests -v
```

GUI 테스트는 `requirements.txt`의 PyQt5를 사용하며, 실제 Qt 위젯을 화면에 띄우지 않고 검증합니다. PyQt5가 설치되지 않은 환경에서는 GUI 테스트만 건너뛰고 엔진 테스트를 실행합니다.

테스트 항목에는 다음이 포함됩니다.

- FCFS 대기시간 계산
- RR Time Quantum에 따른 Preemption
- DRR Complexity 기반 E-Core 우선 배치
- 사용하지 않는 E-Core의 전력 미소모
- 장시간 DRR 프로세스의 30 work-unit 강제 종료
- P-Core / E-Core 개수 제한
- 삭제·수동 PID 입력 후 Random / DRR 생성의 번호 중복 방지
- 표 정렬 후 프로세스 추가·선택·삭제와 표시 값 일치
- 표시 전용 표의 편집 방지
- 분석 조건 변경·실행 실패 시 이전 결과 초기화, 거부된 입력의 기존 결과 보존
- 요약 지표·프로세스 개수 표시와 DRR 버튼 흐름, 작은 창에서의 입력 접근성
- 다른 작업 폴더에서 GUI 리소스 로딩과 작업 폴더 유지

## 프로젝트 구조

```text
processor-scheduling-simulator/
├─ scheduler.py          # 공통 스케줄링 / 전력 계산 엔진
├─ ui.py                 # PyQt GUI와 스케줄러 연결
├─ Operating_System.py   # CLI 데모
├─ algorithms/           # 알고리즘별 main(Info) 호출 모듈
│  ├─ __init__.py
│  ├─ FCFS.py
│  ├─ RR.py
│  ├─ SPN.py
│  ├─ SRTN.py
│  ├─ HRRN.py
│  └─ DRR.py
├─ assets/               # GUI 리소스
│  ├─ os.ui              # Qt Designer 화면 배치
│  ├─ styles.qss         # 화면 색상·글꼴·표·버튼 테마
│  └─ images/            # 로고와 기존 이미지
├─ docs/                 # 기존 프로젝트 문서
├─ tests/                # 엔진·GUI·리소스 경로 회귀 테스트
├─ .gitignore
├─ CHANGELOG.md
├─ requirements.txt
└─ README.md
```

계산 엔진과 GUI·CLI 실행 파일은 루트에 유지합니다. 알고리즘별 호출 모듈은 `algorithms/`, 화면 배치·스타일·이미지는 `assets/`, 검증 코드는 `tests/`, 기존 프로젝트 문서는 `docs/`에서 관리합니다.

## 알고리즘 모듈 사용

알고리즘별 `main(Info)`의 입력·반환 형식은 기존과 같습니다. 모듈을 `algorithms/`로 이동했으므로, 기존 `import FCFS` 대신 `from algorithms import FCFS`로 가져옵니다. 프로젝트 루트에서 실행하거나 프로젝트 루트가 Python 모듈 검색 경로에 있어야 합니다. GUI·CLI 실행 명령은 그대로 사용할 수 있습니다.

```python
from algorithms import FCFS

info = [
    [(1, 0, 5), (2, 1, 3)],
    [1, 1, 1, 2],
]
result = FCFS.main(info)
```

RR은 세 번째 값으로 Time Quantum을 전달할 수 있습니다.

```python
from algorithms import RR

result = RR.main([
    [(1, 0, 5), (2, 1, 3)],
    [1, 1, 1, 2],
    2,
])
```

DRR은 프로세스 정보에 GPT 모델과 Complexity를 추가합니다.

```python
from algorithms import DRR

result = DRR.main([
    [(1, 0, 8, "GPT 3.5", 3), (2, 0, 16, "GPT 4", 8)],
    [1, 1, 1, 2],
])
```

## 정리한 내용

기존 브랜치마다 별도로 존재하던 스케줄링 코드와 GUI 코드를 그대로 병합하지 않고, 공통 로직을 `scheduler.py`로 통합했습니다. 이를 통해 알고리즘마다 중복되어 있던 Process / Processor / 전력 계산 코드를 제거하고 GUI와 CLI가 동일한 계산 결과를 사용하도록 정리했습니다.
