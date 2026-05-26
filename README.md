# Daily Time Box Planner

PySide6 기반의 현대적인 데스크톱 Daily Time Box Planner입니다.

## 실행

```bash
pip install -r requirements.txt
python3 app.py
```

## exe 빌드

```bash
pyinstaller planner.spec
```

## 기능

- 최초 실행 시 한 학기 과목 등록
- 과목별 난이도 설정: 쉬움, 보통, 어려움
- 기본 카테고리 `기타` 자동 생성
- To Do List 항목마다 과목 또는 `기타` 연결
- Brain Dump 저장
- 날짜별 Daily Time Box Planner 시간표
- 시간 블록 클릭 시 연결된 할 일 타이머 실행
- 타이머 기록을 과목 기준으로 저장
- `기타` 기록은 전체 일정 기록에 포함하지만 과목별 공부 통계에서는 제외
- 중단/미룸 기록
- Markdown 리포트 생성
- OpenAI API 피드백 구조

데이터는 `data/planner.sqlite3`에 자동 저장됩니다.

## 구조

- `ui/`: PySide6 화면과 카드 컴포넌트
- `core/`: 경로, 리포트, AI 피드백 구조
- `database/`: SQLite 저장소
- `styles/`: QSS 디자인 시스템
- `assets/`: 빌드 포함용 리소스 폴더
