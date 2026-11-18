# -*- coding: utf-8 -*-
"""
20대 건강 데이터 대시보드 (Streamlit)

실행:  streamlit run streamlit_app.py
데이터 출처 선택
  - 로컬 파일 : 같은 폴더(또는 data/)의 CSV/XLSX 를 직접 읽음
  - API 서버  : api_server.py 가 켜져 있으면 그 주소에서 JSON 을 받아 그림 (예: http://localhost:5000)
"""
import io

import pandas as pd
import requests
import streamlit as st

import charts
import data

st.set_page_config(page_title="20대 건강 데이터", page_icon="📊", layout="wide")


# ------------------------------------------------------------------
# 데이터 가져오기 (로컬 / API)
# ------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_local(key):
    return data.INDICATORS[key][1]()


@st.cache_data(show_spinner=False, ttl=60)
def load_api(base, key):
    r = requests.get(f"{base.rstrip('/')}/api/indicators/{key}", timeout=15)
    r.raise_for_status()
    return pd.DataFrame(r.json()["data"])


@st.cache_data(show_spinner=False, ttl=60)
def summary_api(base):
    r = requests.get(f"{base.rstrip('/')}/api/summary", timeout=15)
    r.raise_for_status()
    return r.json()


def get(key):
    if api_url:
        try:
            return load_api(api_url, key)
        except Exception as e:
            st.warning(f"API 연결 실패 → 로컬 파일 사용 ({e})")
    return load_local(key)


# ------------------------------------------------------------------
# 사이드바
# ------------------------------------------------------------------
st.sidebar.title("📊 20대 건강 데이터")
source = st.sidebar.radio("데이터 출처", ["로컬 파일", "API 서버"])
api_url = ""
if source == "API 서버":
    api_url = st.sidebar.text_input("API 주소", "http://localhost:5000")

labels = {k: v[0] for k, v in data.INDICATORS.items()}
key = st.sidebar.radio("지표 선택", list(labels), format_func=lambda k: labels[k])
show_est = st.sidebar.checkbox("추정값 강조 표시", value=True)
st.sidebar.caption("2018년 대사증후군 자료는 원자료 결측으로 2017·2019년 선형보간 추정값입니다.")

# ------------------------------------------------------------------
# 상단 핵심 수치
# ------------------------------------------------------------------
st.title("20대 건강 지표 한눈에 보기")
try:
    s = summary_api(api_url) if api_url else data.summary()
except Exception:
    s = data.summary()
unmet_key = next(k for k in s if k.startswith("20대 미충족"))

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"건강검진 수진율 ({s['기준연도']})", f"{s['20대 건강검진 수진율(%)']}%",
          f"{s['20대 건강검진 수진율(%)'] - s['19세 이상 건강검진 수진율(%)']:.1f}%p (성인 전체 대비)")
c2.metric(f"비만 유병률 ({s['기준연도']})", f"{s['20대 비만 유병률(%)']}%")
c3.metric(unmet_key.replace("20대 ", "").replace("(%, ", " (").rstrip(")") + ")", f"{s[unmet_key]}%")
c4.metric("우울 환자 (2015→2024)", f"{s['20대 우울 에피소드 환자수(명)']:,}명",
          f"{s['20대 우울 환자 증가(배, 2015 대비)']}배 (전 연령 {s['전 연령 우울 환자 증가(배, 2015 대비)']}배)")

st.divider()

# ------------------------------------------------------------------
# 선택한 지표
# ------------------------------------------------------------------
title, _, src = data.INDICATORS[key]
df = get(key)
st.subheader(title)
st.caption(f"출처: {src}")

if "추정" in df and df["추정"].any():
    years = sorted(df.loc[df["추정"], "연도"].unique())
    st.info(f"추정값 포함: {', '.join(map(str, years))}년 (앞뒤 연도 선형보간). 그래프에서 점선·빈 점으로 표시됩니다.")

tab1, tab2, tab3 = st.tabs(["보고서용 그래프", "인터랙티브 그래프", "데이터 표"])

with tab1:
    fig = charts.FIGURES[key][0](df)
    st.pyplot(fig)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    st.download_button("PNG 다운로드", buf.getvalue(), file_name=charts.FIGURES[key][1], mime="image/png")

with tab2:
    # 지표별로 '연도 x 계열' 표로 바꿔서 기본 선그래프/막대그래프로 표시
    if key in ("checkup", "obesity", "unmet"):
        sex = st.selectbox("성별", ["전체", "남자", "여자"])
        d = df[df["성별"] == sex]
        wide = d.pivot(index="연도", columns="대상", values="값")
    elif key == "mets":
        sex = st.selectbox("성별", ["전체", "남자", "여자"])
        wide = df[df["성별"] == sex].pivot(index="연도", columns="요인", values="비율")
    elif key == "suspect":
        items = st.multiselect("항목", data.SUSPECT_ITEMS, default=data.SUSPECT_ITEMS[:4])
        wide = df[df["항목"].isin(items)].pivot(index="연도", columns="항목", values="인원")
    elif key == "f32":
        groups = st.multiselect("구분", ["20대 전체", "20대 남", "20대 여", "전 연령"],
                                default=["20대 남", "20대 여"])
        wide = df[df["구분"].isin(groups)].pivot(index="연도", columns="구분", values="환자수")
    elif key == "inpatient_top":
        yr = st.radio("기준연도", sorted(df["기준연도"].unique()), horizontal=True)
        n = st.slider("상위 몇 개", 5, 20, 10)
        wide = df[(df["기준연도"] == yr) & (df["순위"] <= n)].set_index("질병")[["환자수"]]
    else:  # inpatient_trend
        wide = df.assign(이름=df["코드"] + " " + df["질병"].str[:12]) \
                 .pivot(index="연도", columns="이름", values="환자수")

    if key == "inpatient_top":
        st.bar_chart(wide, horizontal=True)
    elif key == "f32":
        st.bar_chart(wide)
    else:
        wide.index = wide.index.astype(str)       # x축에 2,018 처럼 쉼표가 붙지 않게
        st.line_chart(wide)

with tab3:
    view = df.copy()
    if show_est and "추정" in view:
        st.dataframe(view.style.apply(
            lambda r: ["background-color: #fff3cd" if r["추정"] else "" for _ in r], axis=1),
            hide_index=True)
        st.caption("노란색 줄 = 추정값")
    else:
        st.dataframe(view, hide_index=True)
    st.download_button("CSV 다운로드", view.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"{key}.csv", mime="text/csv")
