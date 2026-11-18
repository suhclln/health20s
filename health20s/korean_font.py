# -*- coding: utf-8 -*-
"""
matplotlib 한글 깨짐 해결 모듈 (코랩 / 윈도우 / 맥 / 리눅스 공통)

코랩에서 한글이 깨지는 이유
  - 코랩에는 한글 폰트가 없음
  - apt 로 나눔폰트를 깔아도, matplotlib은 시작할 때 만든 폰트 목록만 보기 때문에
    '런타임 재시작'을 하지 않으면 여전히 깨짐
해결
  - 폰트 파일을 찾은 뒤(없으면 설치·다운로드) fontManager.addfont() 로 직접 등록
    -> 런타임 재시작 없이 바로 한글이 나옴

사용법
    from korean_font import setup_korean_font
    setup_korean_font()      # 그래프 그리기 전에 한 번만 호출
"""
import glob
import os
import shutil
import subprocess
import sys
import urllib.request

import matplotlib as mpl
import matplotlib.font_manager as fm

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOCAL_FONT_DIR = os.path.join(_HERE, "fonts")
_DOWNLOAD_URL = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"

# 운영체제별로 흔히 있는 한글 폰트 파일 위치
_CANDIDATE_PATHS = [
    os.path.join(_LOCAL_FONT_DIR, "*.ttf"),                       # 프로젝트 안 fonts 폴더
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",            # 코랩/우분투 (apt fonts-nanum)
    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    "C:/Windows/Fonts/malgun.ttf",                                # 윈도우 (맑은 고딕)
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",                 # 맥
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/Library/Fonts/AppleGothic.ttf",
]
# 이미 설치된 폰트 중 한글이 들어있는 이름
_KOREAN_FONT_NAMES = ["NanumGothic", "NanumBarunGothic", "Malgun Gothic", "AppleGothic",
                      "Apple SD Gothic Neo", "Noto Sans KR", "Noto Sans CJK KR",
                      "Noto Sans CJK JP", "Noto Sans CJK SC"]

_done = None


def _find_file():
    for pattern in _CANDIDATE_PATHS:
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[0]
    return None


def _apt_install():
    """리눅스(코랩)에서 나눔폰트 설치. 실패해도 조용히 넘어감"""
    if not sys.platform.startswith("linux") or shutil.which("apt-get") is None:
        return
    try:
        subprocess.run(["apt-get", "-qq", "install", "-y", "fonts-nanum"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    except Exception:
        pass


def _download():
    """apt가 안 될 때 구글 폰트 저장소에서 나눔고딕 받기"""
    try:
        os.makedirs(_LOCAL_FONT_DIR, exist_ok=True)
        dst = os.path.join(_LOCAL_FONT_DIR, "NanumGothic-Regular.ttf")
        urllib.request.urlretrieve(_DOWNLOAD_URL, dst)
        return dst
    except Exception:
        return None


def _register(path):
    fm.fontManager.addfont(path)                       # 재시작 없이 등록하는 핵심
    return fm.FontProperties(fname=path).get_name()


def setup_korean_font(verbose=True):
    """한글 폰트를 찾아 matplotlib에 적용하고, 적용된 폰트 이름을 돌려줌"""
    global _done
    if _done:
        return _done

    name = None
    path = _find_file()
    if path is None:                                   # 이미 등록된 한글 폰트가 있는지
        installed = {f.name for f in fm.fontManager.ttflist}
        name = next((n for n in _KOREAN_FONT_NAMES if n in installed), None)
    if path is None and name is None:                  # 없으면 설치 -> 다운로드
        _apt_install()
        path = _find_file() or _download()
    if path is not None:
        name = _register(path)

    if name:
        mpl.rcParams["font.family"] = name
        if verbose:
            print(f"[한글 폰트] '{name}' 적용 완료")
    elif verbose:
        print("[한글 폰트] 한글 폰트를 찾지 못했어요. fonts/ 폴더에 .ttf 파일을 넣어 주세요.")
    mpl.rcParams["axes.unicode_minus"] = False         # 마이너스(-) 기호 깨짐 방지
    _done = name
    return name


if __name__ == "__main__":
    setup_korean_font()
