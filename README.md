# 20대 건강 데이터 시각화 (PNG · Streamlit · API)

| 파일 | 역할 |
|---|---|
| `korean_font.py` | 한글 깨짐 해결 (코랩은 나눔폰트 자동 설치 + 재시작 없이 등록) |
| `data.py` | 데이터 8종 불러오기 + 2018년 등 빈 연도 선형보간 추정 (`추정` 열로 표시) |
| `charts.py` | 그래프 함수 8개 (추정 구간 = 점선·빈 점) |
| `make_png.py` | PNG 8장 저장 → `python make_png.py` |
| `api_server.py` | REST API → `python api_server.py` (http://localhost:5000) |
| `streamlit_app.py` | 대시보드 → `streamlit run streamlit_app.py` |
| `colab_run.ipynb` | 코랩에서 위 전부를 순서대로 실행 |

데이터 파일은 이 폴더, `data/` 폴더, 또는 코랩 `/content` 에 두면 자동으로 찾습니다.
다른 위치라면 환경변수 `HEALTH_DATA_DIR` 로 지정하세요.

## 내 PC에서 실행
```
pip install -r requirements.txt
python make_png.py
python api_server.py          # 터미널 1
streamlit run streamlit_app.py  # 터미널 2
```

## API 예시
- `/api/indicators` 지표 목록
- `/api/indicators/checkup?성별=여자&from=2020`
- `/api/indicators/mets?요인=복부비만` (2018년 행은 `"추정": true`)
- `/api/charts/f32.png` 그래프 이미지
- `/api/summary` 핵심 수치
