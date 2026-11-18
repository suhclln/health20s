# -*- coding: utf-8 -*-
"""
20대 건강 데이터 REST API (Flask - 코랩에 기본 설치되어 있음)

실행:  python api_server.py            -> http://localhost:5000
       python api_server.py 8000       -> 포트 바꾸기

엔드포인트
  GET /                                  사용 안내
  GET /api/indicators                    지표 목록
  GET /api/indicators/<key>              지표 데이터(JSON, '추정' 표시 포함)
        ?성별=남자  ?대상=19-29세  ?from=2018&to=2024   (열 이름=값 으로 필터)
  GET /api/charts/<key>.png              지표 그래프 이미지
  GET /api/summary                       20대 핵심 수치 요약
<key>: checkup, obesity, unmet, mets, suspect, f32, inpatient_top, inpatient_trend
"""
import io
import sys

import matplotlib
matplotlib.use("Agg")                       # 서버에서는 창 없이 이미지로만
import matplotlib.pyplot as plt
from flask import Flask, jsonify, request, send_file

import charts
import data

app = Flask(__name__)
app.json.ensure_ascii = False               # JSON에서 한글이 \uXXXX 로 깨지지 않게
app.json.sort_keys = False


@app.after_request
def _cors(resp):                            # 다른 주소의 웹앱(팀원 앱)에서도 호출 가능하게
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


def _bad(key):
    return jsonify(error=f"없는 지표: {key}", 가능한_지표=list(data.INDICATORS)), 404


@app.get("/")
def index():
    return jsonify(
        설명="20대 건강 데이터 API",
        엔드포인트={
            "/api/indicators": "지표 목록",
            "/api/indicators/<key>": "지표 데이터 (예: /api/indicators/checkup?성별=여자)",
            "/api/charts/<key>.png": "그래프 이미지 (예: /api/charts/f32.png)",
            "/api/summary": "핵심 수치 요약",
        })


@app.get("/api/indicators")
def indicators():
    return jsonify([{"key": k, "이름": t, "출처": s, "주소": f"/api/indicators/{k}",
                     "그래프": f"/api/charts/{k}.png"}
                    for k, (t, _, s) in data.INDICATORS.items()])


@app.get("/api/indicators/<key>")
def indicator(key):
    if key not in data.INDICATORS:
        return _bad(key)
    title, fn, source = data.INDICATORS[key]
    df = fn().copy()
    year_col = "연도" if "연도" in df else "기준연도"
    for k, v in request.args.items():
        if k == "from":
            df = df[df[year_col] >= int(v)]
        elif k == "to":
            df = df[df[year_col] <= int(v)]
        elif k in df.columns:
            df = df[df[k].astype(str) == v]
    est = int(df["추정"].sum()) if "추정" in df else 0
    return jsonify(key=key, 이름=title, 출처=source, 행수=len(df), 추정값_개수=est,
                   추정_방법="2018년 등 자료가 없는 연도는 앞뒤 연도 선형보간" if est else None,
                   data=df.to_dict(orient="records"))


@app.get("/api/charts/<key>.png")
def chart(key):
    if key not in charts.FIGURES:
        return _bad(key)
    fig = charts.FIGURES[key][0]()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.get("/api/summary")
def summary():
    return jsonify(data.summary())


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(host="0.0.0.0", port=port, debug=False)
