# -*- coding: utf-8 -*-
"""
그래프 8개를 PNG로 저장
    python make_png.py            -> figures/ 폴더에 저장
    python make_png.py 저장폴더
"""
import os
import sys

import matplotlib
if "ipykernel" not in sys.modules:          # 터미널/코랩 '!python' 실행 시 창 없이 저장만
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

from charts import FIGURES


def main(out_dir="figures"):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for key, (make, fname) in FIGURES.items():
        fig = make()
        path = os.path.join(out_dir, fname)
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)
        print("저장:", path)
    return paths


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "figures")
