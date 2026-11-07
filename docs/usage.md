# 사용 안내

[프로젝트 소개](../README.md) · [시뮬레이션 모델](scheduling-model.md)

## 설치

권장 환경은 Python 3.9.x와 PyQt5 5.15.7입니다. 프로젝트 루트에서 가상환경을 만들고 의존성을 설치합니다.

### Windows

```powershell
py -3.9 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe ui.py
```

### macOS와 Linux

```bash
python3.9 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python ui.py
```

가상환경을 활성화한 경우 아래 예제의 `python` 명령을 그대로 사용할 수 있습니다. 활성화하지 않았다면 Windows에서는 `.\.venv\Scripts\python.exe`, macOS·Linux에서는 `.venv/bin/python`으로 실행합니다.

## GUI 사용

```bash
python ui.py
```

1. 실행할 알고리즘을 선택합니다.
2. 코어 0~3을 Off·P-Core·E-Core로 설정합니다. P-Core는 최대 3개, E-Core는 최대 1개입니다.
3. 프로세스 ID·도착 시간(AT)·작업량(BT)을 입력하고 **추가**를 누릅니다. **랜덤 생성**으로 여러 프로세스를 만들 수도 있습니다.
4. RR을 선택했다면 시간 할당량을 설정합니다.
5. **시뮬레이션 실행**을 눌러 결과를 확인합니다.

프로세스 목록과 간트 차트는 왼쪽, 설정과 처리 결과는 오른쪽에 표시됩니다. 타임라인은 최대 4개 코어의 행과 가로 스크롤에 맞춘 높이를 유지합니다.

### 프로세스 관리

- 작업량(BT)은 1~45 범위입니다. **입력 초기화**는 작성 중인 입력값을 초기화합니다.
- 프로세스는 목록에서 선택한 뒤 **선택 삭제** 또는 Delete 키로 삭제합니다.
- 프로세스·결과 표는 정렬할 수 있습니다. 표의 값은 표시 전용이며 추가·삭제 버튼으로 관리합니다.
- 프로세스·알고리즘·코어 또는 RR 시간 할당량이 바뀌면 기존 결과가 초기화됩니다. 조건 변경 후 다시 실행해 주세요.

### DRR 시나리오 생성

1. 알고리즘을 **DRR**로 선택합니다.
2. GPT 모델과 질문 복잡도를 선택합니다. 선택 순서는 자유입니다.
3. 확인 창에서 생성에 동의하면 프로세스 3개가 추가됩니다.
4. 실행 버튼으로 스케줄링 결과를 확인합니다.

생성 승인·취소 후에는 선택한 모델과 복잡도가 초기화됩니다. DRR에서는 수동 입력과 일반 랜덤 생성 대신 시나리오 버튼을 사용합니다. GPT 모델은 로컬 생성 프리셋이므로 외부 API 호출이나 API 키가 필요하지 않습니다.

화면·스타일·이미지는 스크립트 위치를 기준으로 불러옵니다. 다른 작업 폴더에서도 `ui.py`의 전체 경로로 실행할 수 있으며 실행한 작업 폴더는 바뀌지 않습니다.

## CLI 데모

```bash
python Operating_System.py
```

GUI 없이 DRR 예제를 실행해 프로세스별 지표와 코어별 전력 모델 값을 출력합니다.

## 테스트

```bash
python -m unittest discover -s tests -v
```

엔진 계산, GUI 입력·정렬·삭제, 조건 변경 후 결과 초기화, DRR 생성·아이콘 선택, 작은 창의 배치, 외부 작업 폴더에서의 리소스 로딩을 확인합니다. GUI 테스트는 실제 Qt 위젯을 화면에 띄우지 않고 실행하며, PyQt5가 없으면 GUI 테스트만 건너뜁니다.

## Python 모듈 호출

프로젝트 루트에서 실행하거나 프로젝트 루트가 Python 모듈 검색 경로에 있어야 합니다. 알고리즘별 `main(Info)`는 공통 엔진을 호출하며 기존 입력·반환 형식을 유지합니다.

기존 `import FCFS` 형태의 코드는 `from algorithms import FCFS`로 바꿔 사용합니다.

### FCFS

```python
from algorithms import FCFS

info = [
    [(1, 0, 5), (2, 1, 3)],
    [1, 1, 1, 2],
]
result = FCFS.main(info)
```

SPN·SRTN·HRRN도 같은 입력 형식을 사용합니다. 코어 값은 `0=Off`, `1=P-Core`, `2=E-Core`입니다.

### RR

세 번째 값으로 시간 할당량을 전달합니다. 생략하면 2입니다.

```python
from algorithms import RR

result = RR.main([
    [(1, 0, 5), (2, 1, 3)],
    [1, 1, 1, 2],
    2,
])
```

### DRR

프로세스 정보에 GPT 모델 이름과 복잡도를 추가합니다.

```python
from algorithms import DRR

result = DRR.main([
    [(1, 0, 8, "GPT 3.5", 3), (2, 0, 16, "GPT 4", 8)],
    [1, 1, 1, 2],
])
```

반환 목록에는 코어 4개의 타임라인·전력 기록, 전체 전력 기록, 완료 프로세스 결과, 준비 큐 이력이 들어갑니다. DRR은 마지막에 강제 종료 프로세스 결과를 추가합니다.
