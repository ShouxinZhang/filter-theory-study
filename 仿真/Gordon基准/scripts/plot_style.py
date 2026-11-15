"""论文图统一字体与导出，明确使用真实宋体，缺失时不静默替换。"""
import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.text import Text
from pipeline.common import digest_file

COLORS = {"kf": "#475569", "ekf": "#475569", "bpf": "#0284c7", "enkf": "#ea580c", "etpf": "#0d9488"}
LINESTYLES = {"kf": "-", "ekf": "-", "bpf": "--", "enkf": "-.", "etpf": ":"}

def style():
    font_path = Path(os.environ.get("BASELINE_CHINESE_FONT", "/usr/local/share/fonts/simsun.ttc"))
    if not font_path.exists():
        raise RuntimeError("未找到宋体，请用 BASELINE_CHINESE_FONT 指定 SimSun 字体文件")
    font_manager.fontManager.addfont(str(font_path))
    family = font_manager.FontProperties(fname=str(font_path)).get_name()
    if family.lower() not in ("simsun", "nsimsun", "宋体", "新宋体"):
        raise RuntimeError("指定字体不是宋体: " + family)
    latin_path = Path(os.environ.get("BASELINE_LATIN_FONT", "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf"))
    if latin_path.exists():
        font_manager.fontManager.addfont(str(latin_path))
        latin_family = font_manager.FontProperties(fname=str(latin_path)).get_name()
    else:
        latin_family = "STIXGeneral"
        latin_path = Path(font_manager.findfont(font_manager.FontProperties(family=latin_family)))
    plt.rcParams.update({
        # 拉丁数字和数学负号使用衬线字体，中文字符回退到已注册的宋体
        "font.family": [latin_family, family], "font.size": 10, "font.weight": "normal",
        "axes.titlesize": 11, "axes.labelsize": 10, "axes.titleweight": "normal",
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "axes.unicode_minus": False, "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.8, "lines.linewidth": 1.15, "mathtext.fontset": "stix",
        "text.parse_math": True, "axes.formatter.use_mathtext": True,
        "figure.dpi": 120, "savefig.dpi": 300, "axes.grid": True, "grid.alpha": 0.16,
        "svg.fonttype": "path",  # 矢量图字形转路径，跨机器保持宋体外观
    })
    return {"family": family, "path": str(font_path), "sha256": digest_file(font_path),
            "latin_family": latin_family, "latin_path": str(latin_path), "latin_sha256": digest_file(latin_path),
            "math_renderer": "Matplotlib MathText", "math_fontset": "stix",
            "png_dpi": 300, "vector_format": "SVG", "svg_fonttype": "path"}

def save(fig, folder, name, rect=None):
    # MathText 的非公式片段仅使用首选字体；中英公式混排显式选择宋体，
    # 公式内的变量与正体缩写仍由 STIX 渲染，避免中文被替换为空框。
    for artist in fig.findobj(match=Text):
        label = artist.get_text()
        if "$" in label and any("\u3000" <= char <= "\u9fff" or "\uff00" <= char <= "\uffef" for char in label):
            artist.set_fontfamily(font_manager.FontProperties(
                fname=os.environ.get("BASELINE_CHINESE_FONT", "/usr/local/share/fonts/simsun.ttc")).get_name())
    fig.tight_layout(rect=rect)
    path = folder / name
    fig.savefig(path, bbox_inches="tight", dpi=300)
    fig.savefig(path.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)
