from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ==================================================
# Fixed color lookup for every possible combination
# of agreeing methods. Using frozenset so order doesn't
# matter when looking up a combination's color.
# ==================================================
_DUWU = "Du & Wu (2018)"
_KE = "Ke et al. (2015)"
_VR = "van Raan (2004)"
_VRE = "van Raan (2004 Extended)"

_LABEL_ORDER = [_DUWU, _KE, _VR, _VRE]

_COLOR_MAP = {
    frozenset([_DUWU]): "red",
    frozenset([_KE]): "blue",
    frozenset([_VR]): "orange",
    frozenset([_VRE]): "purple",

    frozenset([_DUWU, _KE]): "green",
    frozenset([_DUWU, _VR]): "brown",
    frozenset([_DUWU, _VRE]): "magenta",
    frozenset([_KE, _VR]): "cyan",
    frozenset([_KE, _VRE]): "olive",
    frozenset([_VR, _VRE]): "gold",

    frozenset([_DUWU, _KE, _VR]): "black",
    frozenset([_DUWU, _KE, _VRE]): "darkslategray",
    frozenset([_DUWU, _VR, _VRE]): "saddlebrown",
    frozenset([_KE, _VR, _VRE]): "teal",

    frozenset([_DUWU, _KE, _VR, _VRE]): "dimgray",
}


def _get_color_for_labels(labels):
    key = frozenset(labels)
    return _COLOR_MAP.get(key, "gray")  # fallback, shouldn't normally trigger


def _get_label_text(labels):
    # Keep a consistent, predictable ordering regardless of dict
    # insertion order, so the same combination always reads the
    # same way across every figure.
    ordered = [l for l in _LABEL_ORDER if l in labels]
    text = " & ".join(ordered) + (" agree" if len(ordered) > 1 else "")

    # Wrap onto 2 lines if 3+ methods are involved, so the legend
    # box doesn't stretch too wide.
    if len(ordered) >= 3:
        mid = (len(ordered) + 1) // 2
        line1 = " & ".join(ordered[:mid])
        line2 = " & ".join(ordered[mid:]) + " agree"
        text = line1 + " &\n" + line2
    return text

def generate_trajectory_figures(
    paper_numbers,
    duwu_file,
    ke_file,
    vanraan_file,
    output_folder,
    vanraan_extended_file=None
):
    duwu_summary = pd.read_excel(duwu_file, sheet_name="Bcp_Summary")
    duwu_history = pd.read_excel(duwu_file, sheet_name="Citation_History")
    ke_summary = pd.read_excel(ke_file, sheet_name="Ke_Summary")
    vanraan_summary = pd.read_excel(vanraan_file, sheet_name="VanRaan_Summary")

    has_extended = vanraan_extended_file is not None
    if has_extended:
        vanraan_ext_summary = pd.read_excel(
            vanraan_extended_file,
            sheet_name="VanRaanExt_Summary"
        )

    output_folder.mkdir(parents=True, exist_ok=True)
    count = 0
    
    for pid in paper_numbers:
        history = duwu_history[duwu_history["Paper Number"] == pid]
        if len(history) == 0:
            continue
        history = history.iloc[0]
        title = history["Title"]

        year_columns = [
            c for c in history.index
            if str(c).startswith("Year ")
        ]
        citations = []
        for c in year_columns:
            value = history[c]
            if pd.isna(value):
                break
            citations.append(value)
        ages = list(range(1, len(citations) + 1))

        # ------------------------
        # Du & Wu
        # ------------------------
        duwu_row = duwu_summary[
            duwu_summary["Paper Number"] == pid
        ].iloc[0]
        publication_year = int(duwu_row["Publication Year"])
        duwu_awake_age = None
        if not pd.isna(duwu_row["Awakening Year"]):
            duwu_awake_age = (
                int(duwu_row["Awakening Year"]) - publication_year + 1
            )
        bcp = duwu_row["Bcp"]

        # ------------------------
        # Ke
        # ------------------------
        ke_row = ke_summary[ke_summary["Paper Number"] == pid].iloc[0]
        ke_awake_age = None
        if not pd.isna(ke_row["Awakening Year"]):
            ke_awake_age = (
                int(ke_row["Awakening Year"]) - publication_year + 1
            )
        beauty = ke_row["Beauty Coefficient"]

        # ------------------------
        # van Raan (original)
        # ------------------------
        vr_row = vanraan_summary[
            vanraan_summary["Paper Number"] == pid
        ].iloc[0]
        sleep_length = vr_row["Best Sleep Length (s)"]
        is_sb_original = (vr_row["Is Sleeping Beauty"] == "Yes")

        vr_awake_age_original = None
        if is_sb_original and not pd.isna(sleep_length):
            vr_awake_age_original = int(sleep_length) + 1

        # ------------------------
        # van Raan (extended) - optional
        # ------------------------
        is_sb_extended = False
        vr_awake_age_extended = None
        if has_extended:
            vr_ext_rows = vanraan_ext_summary[
                vanraan_ext_summary["Paper Number"] == pid
            ]
            if len(vr_ext_rows) > 0:
                vr_ext_row = vr_ext_rows.iloc[0]
                sleep_length_ext = vr_ext_row["Best Sleep Length (s)"]
                is_sb_extended = (vr_ext_row["Is Sleeping Beauty"] == "Yes")
                if is_sb_extended and not pd.isna(sleep_length_ext):
                    vr_awake_age_extended = int(sleep_length_ext) + 1

        # ------------------------
        # Combined status - just for the subtitle ("van Raan=Yes/No")
        # ------------------------
        is_sb_combined = is_sb_original or is_sb_extended

        # ------------------------
        # Plot
        # ------------------------
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(ages, citations, marker="o", linewidth=2, markersize=4)

        x_min = 1
        x_max = len(citations)
        x_pad = max(0.5, (x_max - x_min) * 0.03)
        ax.set_xlim(x_min, x_max + x_pad)

        ymax = max(citations)
        y_pad = max(1, ymax * 0.08)
        ax.set_ylim(0, ymax + y_pad)

        if ymax <= 15:
            ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
        else:
            ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=10))

        # ---------------------------------
        # X-axis: force integer-only tick marks
        # (Publication Age only exists in whole years -
        # ticks like 2.5 are meaningless and confusing)
        # ---------------------------------
        if x_max <= 20:
            ax.xaxis.set_major_locator(mticker.MultipleLocator(2))
        else:
            ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=10))

        # ---------------------------------
        # Method agreement logic
        # Every unique combination of agreeing methods gets its own
        # fixed, predefined color (see _COLOR_MAP above), and the
        # label always explicitly lists every method involved -
        # no more vague "All methods agree" shorthand.
        # ---------------------------------
        methods = {}
        if duwu_awake_age is not None:
            methods.setdefault(duwu_awake_age, []).append(_DUWU)
        if ke_awake_age is not None:
            methods.setdefault(ke_awake_age, []).append(_KE)
        if vr_awake_age_original is not None:
            methods.setdefault(vr_awake_age_original, []).append(_VR)
        if vr_awake_age_extended is not None:
            methods.setdefault(vr_awake_age_extended, []).append(_VRE)

        for age, labels in methods.items():
            color = _get_color_for_labels(labels)
            label = _get_label_text(labels)
            ax.axvline(
                age, color=color, linestyle="--", linewidth=2, label=label
            )
            
        # ---------------------------------
        # Titles
        # ---------------------------------
        ax.set_title("")
        ax.set_xlabel("Publication Age (Years)")
        ax.set_ylabel("Annual Citations")

        total_citations = int(sum(citations))

        van_raan_text = "Yes" if is_sb_combined else "No"
        if is_sb_combined and not is_sb_original:
            van_raan_text += " (Extended only)"

        plt.suptitle(
            f"Total Citations={total_citations}   "
            f"Bcp={bcp:.2f}   B={beauty:.2f}   van Raan={van_raan_text}",
            fontsize=10
        )
        ax.legend()
        plt.tight_layout(rect=[0, 0.08, 1, 0.95])
        fig.text(0.5, 0.02, f"P{pid}: {title}", ha="center", fontsize=10)

        outfile = output_folder / f"P{pid}_MethodComparison.png"
        plt.savefig(outfile, dpi=600, bbox_inches="tight")
        plt.close()
        count += 1

    return count
