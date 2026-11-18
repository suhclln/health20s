# -*- coding: utf-8 -*-
"""
그래프 함수 모음 - 모두 matplotlib Figure 를 돌려줌
(PNG 저장 / 스트림릿 / API 이미지가 같은 함수를 공유)

추정값(2018) 표시: 실제 값은 실선·꽉 찬 점, 추정 구간은 점선·속이 빈 점 -> 선은 끊기지 않음
"""
import textwrap

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

import data
from korean_font import setup_korean_font

setup_korean_font()
plt.rcParams["figure.dpi"] = 110

COLOR = {"전체": "#444444", "남자": "#2b7bba", "여자": "#d6604d",
         "20대 남": "#2b7bba", "20대 여": "#d6604d"}
PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf"]


# ------------------------------------------------------------------
# 공통
# ------------------------------------------------------------------
def _style(ax, title, ylabel="", years=None, comma=False):
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3)
    if years is not None:
        ax.set_xticks(list(years))
    if comma:
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def _source(fig, text):
    fig.text(0.01, -0.01, text, fontsize=8, color="gray", ha="left", va="top")


def _line(ax, x, y, est, color, label, lw=2.2, ls="-", show_last=True, fmt="{:.1f}"):
    """추정 칸은 점선+빈 점으로 그리고, 선은 끊기지 않게 이어 줌"""
    x, y, est = np.asarray(x), np.asarray(y, dtype=float), np.asarray(est, dtype=bool)
    ax.plot(x, np.where(est, np.nan, y), ls=ls, lw=lw, color=color, marker="o", ms=5, label=label)
    for i in np.where(est)[0]:
        lo, hi = max(i - 1, 0), min(i + 2, len(x))
        ax.plot(x[lo:hi], y[lo:hi], ls=(0, (3, 2)), lw=lw, color=color)
        ax.plot(x[i], y[i], marker="o", ms=7, mfc="white", mec=color, mew=2, zorder=5)
    if show_last and len(y):
        ax.annotate(fmt.format(y[-1]), (x[-1], y[-1]), textcoords="offset points",
                    xytext=(6, 0), va="center", fontsize=9, color=color)


def _est_legend(ax, has_est, **kw):
    handles, labels = ax.get_legend_handles_labels()
    if has_est:
        handles.append(Line2D([], [], ls=(0, (3, 2)), color="gray", marker="o", mfc="white", mec="gray"))
        labels.append("추정값 (앞뒤 연도 선형보간)")
    ax.legend(handles, labels, frameon=False, **kw)


# ------------------------------------------------------------------
# 1~3. 19-29세 성별 추이 (수진율 / 비만 / 미충족 의료)
# ------------------------------------------------------------------
def _age_sex_fig(df, title, ylabel, source):
    fig, ax = plt.subplots(figsize=(9.5, 5))
    years = sorted(df["연도"].unique())
    for sex in ["전체", "남자", "여자"]:
        d = df[(df["대상"] == "19-29세") & (df["성별"] == sex)].sort_values("연도")
        _line(ax, d["연도"], d["값"], d["추정"], COLOR[sex],
              "19-29세 (남녀 전체)" if sex == "전체" else f"19-29세 {sex}")
    d = df[(df["대상"] == "19세 이상 전체") & (df["성별"] == "전체")].sort_values("연도")
    _line(ax, d["연도"], d["값"], d["추정"], "gray", "19세 이상 전체", lw=1.6, ls="--")
    _style(ax, title, ylabel, years)
    _est_legend(ax, df["추정"].any())
    _source(fig, f"출처: {source}. 20대는 조사 기준상 19-29세")
    fig.tight_layout()
    return fig


def fig_checkup(df=None):
    return _age_sex_fig(df if df is not None else data.checkup(),
                        "20대(19-29세) 건강검진 수진율 추이", "수진율 (%)", "국민건강영양조사(질병관리청)")


def fig_obesity(df=None):
    return _age_sex_fig(df if df is not None else data.obesity(),
                        "20대(19-29세) 비만 유병률 추이 (체질량지수 기준)", "유병률 (%)", "국민건강영양조사(질병관리청)")


def fig_unmet(df=None):
    return _age_sex_fig(df if df is not None else data.unmet(),
                        "미충족 의료율 (최근 1년 병·의원에 못 간 비율)", "분율 (%)", "국민건강영양조사(질병관리청), 2020~2023")


# ------------------------------------------------------------------
# 4. 대사증후군 위험요인 (2018 추정)
# ------------------------------------------------------------------
def fig_mets(df=None):
    df = df if df is not None else data.mets()
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), sharey=True)
    for ax, sex in zip(axes, ["전체", "남자", "여자"]):
        for c, f in zip(PALETTE, data.METS_FACTORS):
            d = df[(df["성별"] == sex) & (df["요인"] == f)].sort_values("연도")
            _line(ax, d["연도"], d["비율"], d["추정"], c, f, lw=2)
        _style(ax, f"20대 {'남녀 전체' if sex == '전체' else sex}", "", data.YEARS)
        ax.tick_params(axis="x", rotation=45)
    axes[0].set_ylabel("수검자 중 위험요인 보유 비율 (%)")
    _est_legend(axes[0], df["추정"].any(), fontsize=9)
    fig.suptitle("20대 대사증후군 위험요인 보유율", fontsize=14, fontweight="bold")
    fig.tight_layout()
    _source(fig, "출처: 건강검진 통계(국민건강보험공단), 20~24세+25~29세 합산.\n"
                 "2018년은 원자료의 20대 수검자수가 비정상적으로 적어(자료 없음) 2017·2019년 값의 선형보간으로 추정. "
                 "고중성지방·낮은 HDL은 2019년부터 수준이 크게 달라져 추정 오차가 클 수 있음")
    return fig


# ------------------------------------------------------------------
# 5. 질환의심 판정 인원
# ------------------------------------------------------------------
def fig_suspect(df=None):
    df = df if df is not None else data.suspect()
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    for c, it in zip(PALETTE, data.SUSPECT_ITEMS):
        d = df[df["항목"] == it].sort_values("연도")
        _line(ax, d["연도"], d["인원"], d["추정"], c, it, lw=2, show_last=False)
    ax.axvline(2018, ls=":", color="gray")
    _style(ax, "20대 일반건강검진 질환의심 판정 인원 (항목별)", "인원 (명)", data.YEARS, comma=True)
    ax.text(2018.08, ax.get_ylim()[1] * 0.97, "2018년 이상지질혈증 급감\n(판정 기준 변경 추정)",
            fontsize=8, color="gray", va="top")
    _est_legend(ax, df["추정"].any(), loc="center left", bbox_to_anchor=(1, 0.5))
    _source(fig, "출처: 건강검진 통계(국민건강보험공단), 20~24세+25~29세 합산. 인원은 수검자 규모의 영향도 받음")
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------
# 6. 우울 에피소드(F32)
# ------------------------------------------------------------------
def fig_f32(df=None):
    df = df if df is not None else data.f32()
    p = df.pivot(index="연도", columns="구분", values="환자수").reindex(data.YEARS)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 5.2))
    a1.bar(p.index, p["20대 남"], color=COLOR["남자"], label="남")
    a1.bar(p.index, p["20대 여"], bottom=p["20대 남"], color=COLOR["여자"], label="여")
    for x, v in zip(p.index, p["20대 전체"]):
        a1.text(x, v, f"{int(v):,}", ha="center", va="bottom", fontsize=8)
    _style(a1, "20대 우울 에피소드(F32) 진료 환자수", "환자수 (명)", data.YEARS, comma=True)
    a1.tick_params(axis="x", rotation=45)
    a1.legend(frameon=False)

    for col, c, lab in [("20대 전체", "#7b3294", "20대"), ("전 연령", "gray", "전 연령")]:
        idx = p[col] / p[col].iloc[0] * 100
        est = df[df["구분"] == col].set_index("연도")["추정"].reindex(data.YEARS).fillna(False)
        _line(a2, idx.index, idx.values, est.values, c, lab, fmt="{:.0f}")
    _style(a2, "환자수 증가 추이 (2015년 = 100)", "지수", data.YEARS)
    a2.tick_params(axis="x", rotation=45)
    _est_legend(a2, df["추정"].any())
    _source(fig, "출처: 건강보험심사평가원 3단 상병 통계 (F32 우울 에피소드)")
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------
# 7~8. 입원 다빈도 질병
# ------------------------------------------------------------------
def fig_inpatient_top(df=None, top_n=10):
    df = df if df is not None else data.inpatient_top()
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.4))
    for ax, yr in zip(axes, sorted(df["기준연도"].unique())):
        d = df[(df["기준연도"] == yr) & (df["순위"] <= top_n)].sort_values("순위")
        pos = np.arange(len(d))[::-1]
        ax.barh(pos, d["환자수"], color="#4c78a8")
        ax.set_yticks(pos)
        ax.set_yticklabels([textwrap.fill(n, 16) for n in d["질병"]], fontsize=9)
        for y, v in zip(pos, d["환자수"]):
            ax.text(v, y, f" {int(v):,}", va="center", fontsize=8)
        _style(ax, f"{yr}년 20대 입원 다빈도 질병 TOP{top_n}")
        ax.set_xlim(0, d["환자수"].max() * 1.18)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
        ax.set_xlabel("환자수 (명)")
    _source(fig, "출처: 건강보험심사평가원 다빈도 질병 통계(입원, 3단 상병). 2022년 1위 U07은 코로나19 응급사용 코드")
    fig.tight_layout()
    return fig


def fig_inpatient_trend(df=None):
    df = df if df is not None else data.inpatient_trend()
    fig, ax = plt.subplots(figsize=(11, 5.6))
    years = sorted(df["연도"].unique())
    for c, (code, d) in zip(PALETTE, df.groupby("코드", sort=False)):
        d = d.sort_values("연도")
        name = d["질병"].iloc[0]
        name = name if len(name) <= 14 else name[:13] + "…"
        _line(ax, d["연도"], d["환자수"], d["추정"], c, f"{code} {name}", lw=2, show_last=False)
    _style(ax, "20대 주요 입원 질병 환자수 추이 (2025년 TOP8 기준)", "환자수 (명)", years, comma=True)
    _est_legend(ax, df["추정"].any(), fontsize=8, loc="center left", bbox_to_anchor=(1, 0.5))
    _source(fig, "출처: 건강보험심사평가원 다빈도 질병 통계(입원)")
    fig.tight_layout()
    return fig


# 지표 키 -> (그래프 함수, PNG 파일명)
FIGURES = {
    "checkup":         (fig_checkup, "01_checkup_rate.png"),
    "obesity":         (fig_obesity, "02_obesity.png"),
    "unmet":           (fig_unmet, "03_unmet_medical.png"),
    "mets":            (fig_mets, "04_metabolic_risk.png"),
    "suspect":         (fig_suspect, "05_suspect_items.png"),
    "f32":             (fig_f32, "06_depression_f32.png"),
    "inpatient_top":   (fig_inpatient_top, "07_inpatient_top10.png"),
    "inpatient_trend": (fig_inpatient_trend, "08_inpatient_trend.png"),
}
