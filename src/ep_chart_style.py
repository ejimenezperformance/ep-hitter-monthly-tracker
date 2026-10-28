"""EP brand chart style (navy / gold / off-white). Navy-gold is safe for the common
color-vision deficiencies (they differ strongly in lightness); every chart also carries
direct text labels so no meaning depends on color alone."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

NAVY, GOLD, OFFWHITE, GRAY = "#0B1B33", "#D4A53A", "#F5F3EC", "#8A8F98"


def apply():
    names = {f.name for f in font_manager.fontManager.ttflist}
    family = "Poppins" if "Poppins" in names else "DejaVu Sans"
    plt.rcParams.update({
        "font.family": family, "figure.facecolor": OFFWHITE, "axes.facecolor": OFFWHITE,
        "axes.edgecolor": NAVY, "axes.labelcolor": NAVY, "xtick.color": NAVY, "ytick.color": NAVY,
        "text.color": NAVY, "axes.spines.top": False, "axes.spines.right": False,
        "axes.titleweight": "bold", "axes.titlesize": 13, "savefig.dpi": 200,
        "savefig.bbox": "tight", "savefig.facecolor": OFFWHITE,
    })


def footer(fig, text="Emerson Jimenez | Emerson Performance (EP) | Data: Baseball Savant / Statcast, 2026 regular season"):
    fig.text(0.01, -0.07, text, fontsize=7.5, color=GRAY, ha="left")
