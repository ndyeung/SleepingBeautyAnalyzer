from pathlib import Path
import pandas as pd
import numpy as np
# ==================================================
# Cross-Method Comparison
# Du & Wu (2018) / Ke et al. (2015) / van Raan (2004)
# Optionally also includes van Raan EXTENDED
# ==================================================
def run_comparison(
    bcp_file,
    ke_file,
    vanraan_file,
    output_file,
    top_fraction=0.10,
    vanraan_extended_file=None
):
    bcp_df = pd.read_excel(bcp_file, sheet_name="Bcp_Summary")
    ke_df = pd.read_excel(ke_file, sheet_name="Ke_Summary")
    vr_df = pd.read_excel(vanraan_file, sheet_name="VanRaan_Summary")
    vr_sub = vr_df[
        [
            "Paper Number",
            "Is Sleeping Beauty",
            "Awakening Year",
            "Best Sleep Class",
            "Best Awake Class"
        ]
    ].rename(
        columns={
            "Awakening Year":
                "Awakening Year (van Raan 2004)",
            "Is Sleeping Beauty":
                "Is Sleeping Beauty (van Raan 2004)",
            "Best Sleep Class":
                "Best Sleep Class (van Raan 2004)",
            "Best Awake Class":
                "Best Awake Class (van Raan 2004)"
        }
    )
    bcp_sub = bcp_df[[
        "Paper Number", "Title", "Journal", "Publication Year",
        "Total Citations", "Bcp", "Awakening Year", "Rank"
    ]].rename(columns={
        "Bcp": "Bcp (Du & Wu 2018)",
        "Awakening Year": "Awakening Year (Du & Wu 2018)",
        "Rank": "Rank_Bcp",
        "Total Citations": "Total Citations"
    })
    ke_sub = ke_df[[
        "Paper Number", "Beauty Coefficient", "Awakening Year", "Rank"
    ]].rename(columns={
        "Beauty Coefficient": "B (Ke et al. 2015)",
        "Awakening Year": "Awakening Year (Ke et al. 2015)",
        "Rank": "Rank_B"
    })
    merged = bcp_sub.merge(ke_sub, on="Paper Number", how="outer")
    merged = merged.merge(vr_sub, on="Paper Number", how="outer")
    # --------------------------------------------------------
    # Optional: van Raan EXTENDED
    # --------------------------------------------------------
    has_extended = vanraan_extended_file is not None
    if has_extended:
        vr_ext_df = pd.read_excel(
            vanraan_extended_file,
            sheet_name="VanRaanExt_Summary"
        )
        vr_ext_sub = vr_ext_df[
            [
                "Paper Number",
                "Is Sleeping Beauty",
                "Awakening Year",
                "Best Sleep Class",
                "Best Awake Class",
                "Best Sleep Length (s)",
                "Sufficient History for max_s"
            ]
        ].rename(
            columns={
                "Is Sleeping Beauty":
                    "Is Sleeping Beauty (van Raan Extended)",
                "Awakening Year":
                    "Awakening Year (van Raan Extended)",
                "Best Sleep Class":
                    "Best Sleep Class (van Raan Extended)",
                "Best Awake Class":
                    "Best Awake Class (van Raan Extended)",
                "Best Sleep Length (s)":
                    "Best Sleep Length s (van Raan Extended)",
                "Sufficient History for max_s":
                    "Sufficient History (van Raan Extended)"
            }
        )
        merged = merged.merge(vr_ext_sub, on="Paper Number", how="outer")
    n = len(merged)
    top_cutoff = max(1, int(n * top_fraction))
    merged["High_Bcp"] = merged["Rank_Bcp"] <= top_cutoff
    merged["High_B"] = merged["Rank_B"] <= top_cutoff
    merged["High_VanRaan_Original"] = (
        merged["Is Sleeping Beauty (van Raan 2004)"] == "Yes"
    )
    if has_extended:
        merged["High_VanRaan_Extended"] = (
            merged["Is Sleeping Beauty (van Raan Extended)"] == "Yes"
        )
        # Combined flag: counts as "van Raan says yes" if EITHER
        # the original OR the extended version caught it.
        # This avoids double-counting the same underlying method
        # in Consistency_Count.
        merged["High_VanRaan_Any"] = (
            merged["High_VanRaan_Original"]
            | merged["High_VanRaan_Extended"]
        )
    else:
        merged["High_VanRaan_Any"] = merged["High_VanRaan_Original"]

    merged["Consistency_Count"] = (
        merged["High_Bcp"].astype(int)
        + merged["High_B"].astype(int)
        + merged["High_VanRaan_Any"].astype(int)
    )
    merged = (
        merged
        .sort_values(
            ["Consistency_Count", "Rank_Bcp"],
            ascending=[False, True]
        )
        .reset_index(drop=True)
    )
    merged.insert(0, "Overall Rank", range(1, len(merged) + 1))

    notes_rows = [
        f"User-defined high-paper threshold: {top_fraction*100:g}%",
        "",
        "COMPARISON SHEET - HOW TO READ",
        "",
        "This sheet merges results from three Sleeping Beauty detection methods:",
        "- Bcp (Du & Wu, 2018): continuous score, higher = more 'sleeping beauty'-like.",
        "- B (Ke et al., 2015): continuous score, higher = more 'sleeping beauty'-like.",
        "- van Raan (2004): categorical classification (Yes/No), based on discrete "
        "sleep-length/depth/awake-intensity thresholds (s = 5-10 years only).",
        "",
        "'High_Bcp' and 'High_B' flag papers ranked in the top "
        f"{top_fraction*100:g}% under each respective method.",
        "'High_VanRaan_Original' flags papers classified 'Yes' under the original "
        "van Raan (2004) method (s = 5-10 years).",
    ]
    if has_extended:
        notes_rows += [
            "'High_VanRaan_Extended' flags papers classified 'Yes' under the van Raan "
            "EXTENDED method (wider sleep-length range - see VanRaanExtended_results.xlsx "
            "for the exact s range used).",
            "'High_VanRaan_Any' flags papers caught by EITHER the original OR the "
            "extended van Raan method. THIS combined flag (not the original alone) "
            "feeds into Consistency_Count below, so long-dormancy Sleeping Beauties "
            "missed by the original 5-10yr window but caught by the Extended method "
            "are still properly credited.",
        ]
    else:
        notes_rows += [
            "van Raan Extended results were not provided for this comparison run. "
            "Consistency_Count below reflects the ORIGINAL van Raan (2004) method only, "
            "which cannot detect Sleeping Beauties with a true dormancy period longer "
            "than 10 years, by construction. Papers with very long slow-burn citation "
            "histories may be under-counted as a result - consider re-running this "
            "comparison with van Raan Extended results included.",
        ]
    notes_rows += [
        "",
        "'Consistency_Count' (0-3) counts how many of the three underlying methods "
        "(Bcp, Ke, van Raan) flag the paper as a strong Sleeping Beauty candidate.",
        "",
        "Papers with Consistency_Count = 3 are flagged by ALL THREE methods and are "
        "the strongest candidates for manual citation trajectory review.",
        "Papers with Consistency_Count = 0 or 1 may still be interesting but are "
        "only supported by a single method's definition - treat with more caution.",
        "",
        "Note: van Raan's method, as originally defined, excludes self-citations "
        "from cs and cw; this tool uses total citations instead (see Notes sheet "
        "in VanRaan_results.xlsx for details)."
    ]
    notes_df = pd.DataFrame({"Notice": notes_rows})

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        merged.to_excel(writer, sheet_name="Comparison", index=False)
        notes_df.to_excel(writer, sheet_name="Notes", index=False)
    return len(merged)


if __name__ == "__main__":
    BASE = Path(__file__).resolve().parent.parent
    count = run_comparison(
        BASE / "outputs" / "DuWu_results.xlsx",
        BASE / "outputs" / "Ke_results.xlsx",
        BASE / "outputs" / "VanRaan_results.xlsx",
        BASE / "outputs" / "Comparison_results.xlsx",
        vanraan_extended_file=BASE / "outputs" / "VanRaanExtended_results.xlsx"
    )
    print(f"Compared {count} papers")
