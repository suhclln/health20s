# -*- coding: utf-8 -*-
"""
20대 건강 데이터 불러오기 + 2018년 빈틈 추정 (PNG / 스트림릿 / API가 모두 이 모듈을 사용)

모든 함수는 '정리된(tidy) 표'를 돌려주고, 추정한 칸은 '추정' 열이 True 로 표시됨.

[2018년 추정 방식]
  - 대사증후군 위험요인 파일의 2018년은 20대 수검자수가 다른 해의 약 1/6 수준(여성은 거의 0명)이라
    실제 값으로 쓸 수 없어 '자료 없음'으로 보고 비워 둔 뒤,
    2017년과 2019년 값을 직선으로 이어 채움(선형 보간) = (2017 + 2019) / 2
  - 그 밖에 연도 중간이 비어 있는 경우도 같은 방식으로 자동 보간 -> 그래프에 빈틈이 생기지 않음
"""
import functools
import glob
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="Workbook contains no default style")

YEARS = list(range(2015, 2025))           # 최근 10년
MISSING_YEARS = {"mets": [2018]}          # '자료 없음'으로 보고 추정할 연도 (데이터별)
AGE20 = ["20 ~ 24세", "25 ~ 29세"]        # 건강검진 통계의 20대 구간

_HERE = os.path.dirname(os.path.abspath(__file__))
_SEARCH_DIRS = [os.environ.get("HEALTH_DATA_DIR", ""),
                os.path.join(_HERE, "data"), _HERE,
                os.path.join(os.getcwd(), "data"), os.getcwd(),
                "/content/data", "/content", "/mnt/user-data/uploads"]


# ------------------------------------------------------------------
# 공통 도우미
# ------------------------------------------------------------------
def find(pattern):
    """여러 폴더에서 파일 찾기 (파일명 뒤 날짜가 달라도 OK)"""
    for d in _SEARCH_DIRS:
        if d:
            hits = sorted(glob.glob(os.path.join(d, pattern)))
            if hits:
                return hits[0]
    raise FileNotFoundError(
        f"'{pattern}' 파일을 찾지 못했어요. 데이터 파일을 data/ 폴더에 넣거나 "
        f"환경변수 HEALTH_DATA_DIR 로 경로를 알려 주세요.")


def _num(s):
    return pd.to_numeric(pd.Series(s).astype(str).str.replace(",", ""), errors="coerce").values


def fill_years(df, keys, value, years, missing=()):
    """
    keys 별로 years 전체를 채운 표를 만듦.
    - missing 에 든 연도는 값이 있어도 '자료 없음'으로 지우고
    - 비어 있는 연도는 앞뒤 연도로 선형 보간, '추정'=True 로 표시
    """
    out = []
    for k, g in df.groupby(keys, sort=False):
        s = g.groupby("연도")[value].sum(min_count=1).reindex(years).astype(float)
        s.loc[[y for y in missing if y in s.index]] = np.nan
        est = s.isna()
        s = s.interpolate(method="linear", limit_area="inside")
        part = pd.DataFrame({"연도": years, value: s.values, "추정": est.values & s.notna().values})
        for col, v in zip(keys if isinstance(keys, list) else [keys], k if isinstance(k, tuple) else (k,)):
            part[col] = v
        out.append(part)
    cols = (keys if isinstance(keys, list) else [keys]) + ["연도", value, "추정"]
    return pd.concat(out, ignore_index=True)[cols]


# ------------------------------------------------------------------
# 1~2. 국민건강영양조사: 건강검진 수진율 / 비만 유병률
# ------------------------------------------------------------------
def _knhanes(pattern):
    raw = pd.read_csv(find(pattern), encoding="cp949", header=None)
    years, metric = raw.iloc[0, 3:].astype(int).tolist(), raw.iloc[1, 3:].tolist()
    rows = []
    for _, r in raw.iloc[2:].iterrows():
        if r[2] == "19-29세" and str(r[1]).startswith("연령별"):
            target = "19-29세"
        elif r[1] == "전체" and r[2] == "19세이상":
            target = "19세 이상 전체"
        else:
            continue
        for j, (y, m) in enumerate(zip(years, metric)):
            if "분율" in str(m):
                rows.append((target, r[0], y, r[3 + j]))
    df = pd.DataFrame(rows, columns=["대상", "성별", "연도", "값"])
    df["값"] = _num(df["값"])
    return fill_years(df, ["대상", "성별"], "값", YEARS)


@functools.lru_cache(maxsize=None)
def checkup():
    """건강검진 수진율(%) - 19-29세 / 19세 이상 전체, 성별"""
    return _knhanes("건강검진_수진율*.csv")


@functools.lru_cache(maxsize=None)
def obesity():
    """비만 유병률(%, 체질량지수 기준) - 19-29세 / 19세 이상 전체, 성별"""
    return _knhanes("비만_유병률*.csv")


# ------------------------------------------------------------------
# 3. 미충족 의료율 (2020~2023)
# ------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def unmet():
    raw = pd.read_csv(find("미충족_의료율*.csv"), encoding="cp949", header=None)
    years, metric = raw.iloc[0, 2:].astype(int).tolist(), raw.iloc[1, 2:].tolist()
    rows = []
    for _, r in raw.iloc[2:].iterrows():
        if r[0] not in ("19-29세", "전체"):
            continue
        target = "19-29세" if r[0] == "19-29세" else "19세 이상 전체"
        for j, (y, m) in enumerate(zip(years, metric)):
            if "분율" in str(m):
                rows.append((target, r[1], y, r[2 + j]))
    df = pd.DataFrame(rows, columns=["대상", "성별", "연도", "값"])
    df["값"] = _num(df["값"])
    return fill_years(df, ["대상", "성별"], "값", sorted(set(years)))


# ------------------------------------------------------------------
# 4. 대사증후군 위험요인 보유율 (20대) - 2018 추정
# ------------------------------------------------------------------
METS_FACTORS = ["복부비만", "높은혈압", "높은혈당", "고중성지방혈증", "낮은 HDL 콜레스테롤 혈증"]


@functools.lru_cache(maxsize=None)
def mets():
    raw = pd.read_csv(find("연령별_성별_대사증후군*.csv"), encoding="cp949", header=None)
    hdr, body = raw.iloc[:4], raw.iloc[4:]
    rows = []
    for j in range(2, raw.shape[1]):
        year, factor, kind, val = (hdr.iloc[i, j] for i in range(4))
        if "인원" in str(kind) and str(val) == "원데이터":
            for _, r in body.iterrows():
                if r[0] in AGE20:
                    rows.append((r[1], int(year), factor, r[j]))
    df = pd.DataFrame(rows, columns=["성별", "연도", "요인", "인원"])
    df["인원"] = _num(df["인원"])
    df["성별"] = df["성별"].replace({"합계": "전체"})
    df = df.groupby(["성별", "연도", "요인"], as_index=False)["인원"].sum()

    total = df[df["요인"] == "수검자수"].set_index(["성별", "연도"])["인원"]
    rate = df[df["요인"].isin(METS_FACTORS)].copy()
    rate["비율"] = rate["인원"].values / total.reindex(list(zip(rate["성별"], rate["연도"]))).values * 100
    out = fill_years(rate[["성별", "요인", "연도", "비율"]], ["성별", "요인"], "비율",
                     YEARS, missing=MISSING_YEARS["mets"])
    out["비율"] = out["비율"].round(2)
    return out


# ------------------------------------------------------------------
# 5. 일반건강검진 질환의심 판정 인원 (20대, 항목별)
# ------------------------------------------------------------------
SUSPECT_ITEMS = ["간장질환", "이상지질혈증", "고혈압", "신장질환", "당뇨병", "기타흉부질환", "빈혈증"]


@functools.lru_cache(maxsize=None)
def suspect():
    raw = pd.read_csv(find("연령별_성별_일반건강검진_판정결과*.csv"), encoding="cp949", header=None)
    hdr, body = raw.iloc[:3], raw.iloc[3:]
    body = body[body[0].isin(AGE20) & (body[1] == "합계")]
    rows = []
    for j in range(2, raw.shape[1]):
        year, item = int(hdr.iloc[0, j]), hdr.iloc[2, j]
        if item in SUSPECT_ITEMS:
            for _, r in body.iterrows():
                rows.append((item, year, r[j]))
    df = pd.DataFrame(rows, columns=["항목", "연도", "인원"])
    df["인원"] = np.nan_to_num(_num(df["인원"]))      # '-' 는 0명
    return fill_years(df, "항목", "인원", YEARS)


# ------------------------------------------------------------------
# 6. 우울 에피소드(F32) 환자수
# ------------------------------------------------------------------
def _year_cols(raw):
    return {int(str(v)[:4]): j for j, v in raw.iloc[2].items()
            if isinstance(v, str) and v.endswith("년") and v[:4].isdigit()}


@functools.lru_cache(maxsize=None)
def f32():
    """구분: 20대 남 / 20대 여 / 20대 전체 / 전 연령"""
    raw = pd.read_excel(find("질병소분류_3단상병*.xlsx"), header=None)
    cols = _year_cols(raw)
    rows = []
    for _, r in raw.iloc[4:].iterrows():
        if r[2] == "20_29세" and r[1] in ("남", "여"):
            label = f"20대 {r[1]}"
        elif r[1] == "계" and r[2] == "계":
            label = "전 연령"
        else:
            continue
        for y, j in cols.items():
            rows.append((label, y, r[j]))
    df = pd.DataFrame(rows, columns=["구분", "연도", "환자수"])
    df["환자수"] = _num(df["환자수"])
    both = df[df["구분"].isin(["20대 남", "20대 여"])].groupby("연도", as_index=False)["환자수"].sum()
    both["구분"] = "20대 전체"
    return fill_years(pd.concat([df, both]), "구분", "환자수", YEARS)


# ------------------------------------------------------------------
# 7~8. 입원 다빈도 질병 (20대) - 두 파일 합치기
# ------------------------------------------------------------------
def _freq(pattern):
    raw = pd.read_excel(find(pattern), header=None)
    cols = _year_cols(raw)
    base = max(cols)
    rows = []
    for _, r in raw.iloc[4:].iterrows():
        for y, j in cols.items():
            rows.append((base, int(r[3]), r[1], r[2], y, r[j]))
    df = pd.DataFrame(rows, columns=["기준연도", "순위", "코드", "질병", "연도", "환자수"])
    df["환자수"] = _num(df["환자수"])
    return df


@functools.lru_cache(maxsize=None)
def _freq_all():
    return pd.concat([_freq("다빈도질병통계*_2022.xlsx"),
                      _freq("다빈도질병통계*_2022_2025.xlsx")], ignore_index=True)


@functools.lru_cache(maxsize=None)
def inpatient_top():
    """기준연도(2022, 2025)별 입원 TOP20"""
    f = _freq_all()
    return f[f["연도"] == f["기준연도"]][["기준연도", "순위", "코드", "질병", "환자수"]] \
        .sort_values(["기준연도", "순위"]).reset_index(drop=True)


@functools.lru_cache(maxsize=None)
def inpatient_trend(top_n=8):
    """2025년 TOP N 질병의 2021~2025 환자수"""
    f = _freq_all()
    top = f[(f["기준연도"] == 2025) & (f["연도"] == 2025) & (f["순위"] <= top_n)]
    names = dict(zip(top["코드"], top["질병"]))
    d = f[f["코드"].isin(names)].drop_duplicates(["코드", "연도"])[["코드", "연도", "환자수"]]
    out = fill_years(d, "코드", "환자수", list(range(2021, 2026)))
    out.insert(1, "질병", out["코드"].map(names))
    return out


# ------------------------------------------------------------------
# 한 번에 쓰기 위한 목록 (API / 스트림릿에서 사용)
# ------------------------------------------------------------------
INDICATORS = {
    "checkup":         ("건강검진 수진율", checkup, "국민건강영양조사(질병관리청)"),
    "obesity":         ("비만 유병률", obesity, "국민건강영양조사(질병관리청)"),
    "unmet":           ("미충족 의료율", unmet, "국민건강영양조사(질병관리청)"),
    "mets":            ("대사증후군 위험요인 보유율", mets, "건강검진 통계(국민건강보험공단)"),
    "suspect":         ("건강검진 질환의심 판정 인원", suspect, "건강검진 통계(국민건강보험공단)"),
    "f32":             ("우울 에피소드(F32) 환자수", f32, "건강보험심사평가원"),
    "inpatient_top":   ("입원 다빈도 질병 TOP20", inpatient_top, "건강보험심사평가원"),
    "inpatient_trend": ("주요 입원 질병 추이", inpatient_trend, "건강보험심사평가원"),
}


def summary():
    """20대 핵심 수치 (가장 최근 연도)"""
    def last(df, **cond):
        d = df
        for k, v in cond.items():
            d = d[d[k] == v]
        d = d.sort_values("연도").iloc[-1]
        return int(d["연도"]), round(float(d.iloc[list(d.index).index(
            [c for c in ("값", "비율", "환자수") if c in d.index][0])]), 1)

    y, c20 = last(checkup(), 대상="19-29세", 성별="전체")
    _, call = last(checkup(), 대상="19세 이상 전체", 성별="전체")
    _, o20 = last(obesity(), 대상="19-29세", 성별="전체")
    uy, u20 = last(unmet(), 대상="19-29세", 성별="전체")
    f = f32().pivot(index="연도", columns="구분", values="환자수")
    return {
        "기준연도": y,
        "20대 건강검진 수진율(%)": c20, "19세 이상 건강검진 수진율(%)": call,
        "20대 비만 유병률(%)": o20,
        f"20대 미충족 의료율(%, {uy})": u20,
        "20대 우울 에피소드 환자수(명)": int(f["20대 전체"].iloc[-1]),
        "20대 우울 환자 증가(배, 2015 대비)": round(float(f["20대 전체"].iloc[-1] / f["20대 전체"].iloc[0]), 1),
        "전 연령 우울 환자 증가(배, 2015 대비)": round(float(f["전 연령"].iloc[-1] / f["전 연령"].iloc[0]), 1),
    }


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    for key, (title, fn, _) in INDICATORS.items():
        d = fn()
        print(f"\n== {title} ({key}) {d.shape}, 추정 칸 {int(d.get('추정', pd.Series(dtype=bool)).sum())}개")
        print(d.head(3).to_string())
    print(summary())
