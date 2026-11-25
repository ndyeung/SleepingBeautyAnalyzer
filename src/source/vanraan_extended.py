from pathlib import Path
import pandas as pd
import numpy as np
from source.vanraan import (
    classify_sleep_depth,
    classify_awake_intensity,
    analyze_paper_sleeping_beauty
)
# ==================================================
# Van Raan EXTENDED - not part of the original 2004 paper
#
# The original van Raan (2004) method only tests sleep lengths
# s = 5 to s = 10 years. This variant extends that range to
# detect longer-dormancy Sleeping Beauties that the original
# method is structurally unable to find (see Notes sheet).
# ==================================================
def run_vanraan_extended(input_file, output_file, min_s=5, max_s=30):
    sleep_lengths = range(min_s, max_s + 1)
    wos = pd.read_excel(input_file, sheet_name="MasterData")
    wos["SortTitle"] = (
        wos["Title"].astype(str)
        .str.replace(r"<[^>]+>", "", regex=True)
        .str.strip()
        .str.lower()
    )
    wos = wos.sort_values("SortTitle").reset_index(drop=True)
    wos.drop(columns=["SortTitle"], inplace=True)
    year_columns = []
    for col in wos.columns:
        try:
            year = int(str(col))
            if 1950 <= year <= 2100:
                year_columns.append(col)
        except Exception:
            pass
    year_columns = sorted(year_columns, key=int)
    summary_rows = []
    detail_rows = []
    history_rows = []
    for paper_number, (_, row) in enumerate(wos.iterrows(), start=1):
        if pd.isna(row["Publication Year"]):
            continue
        publication_year = int(row["Publication Year"])
        paper_years = [
            col for col in year_columns
            if int(col) >= publication_year
        ]
        citations = []
        for col in paper_years:
            value = pd.to_numeric(row[col], errors="coerce")
            if pd.isna(value):
                value = 0
            citations.append(value)
        citation_df = pd.DataFrame({
            "Year": [int(y) for y in paper_years],
            "Citations": citations
        })
        # -----------------------------------------------
        # Flag whether this paper even has enough history
        # to be fairly tested at the requested max_s
        # -----------------------------------------------
        years_of_history = len(paper_years)
        sufficient_history = years_of_history >= (max_s + 4)
        all_matches, best_match = analyze_paper_sleeping_beauty(
            citation_df, publication_year, s_values=sleep_lengths
        )
        is_sb = best_match is not None
        total_citations = int(sum(citations))
        awakening_year = (
            publication_year + best_match["SleepLength_s"]
            if is_sb else np.nan
        )
        summary_rows.append({
            "Paper Number": paper_number,
            "Title": row["Title"],
            "Journal": row["Source Title"],
            "Publication Year": publication_year,
            "Total Citations": total_citations,
            "Years of History Available": years_of_history,
            "Sufficient History for max_s": "Yes" if sufficient_history else "No",
            "Is Sleeping Beauty": "Yes" if is_sb else "No",
            "Best Sleep Length (s)": best_match["SleepLength_s"] if is_sb else np.nan,
            "Best Sleep Citations (cs)": best_match["SleepCitations_cs"] if is_sb else np.nan,
            "Best Sleep Class": best_match["SleepClass"] if is_sb else None,
            "Awakening Year": awakening_year,
            "Best Awake Citations (cw)": best_match["AwakeCitations_cw"] if is_sb else np.nan,
            "Best Awake Class": best_match["AwakeClass"] if is_sb else None,
            "Number of Qualifying (s,cs,cw) Combos": len(all_matches)
        })
        for match in all_matches:
            detail_rows.append({
                "Paper Number": paper_number,
                "Title": row["Title"],
                "Journal": row["Source Title"],
                "Publication Year": publication_year,
                "Sleep Length (s)": match["SleepLength_s"],
                "Sleep Citations (cs)": match["SleepCitations_cs"],
                "Sleep Class": match["SleepClass"],
                "Awake Citations (cw)": match["AwakeCitations_cw"],
                "Awake Class": match["AwakeClass"]
            })
        history_row = {
            "Paper Number": paper_number,
            "Title": row["Title"],
            "Journal": row["Source Title"],
            "Publication Year": publication_year
        }
        for i, c in enumerate(citations):
            history_row[f"Year {i+1}"] = c
        history_rows.append(history_row)

    summary_df = pd.DataFrame(summary_rows)
    awake_order = {">60": 5, "51-60": 4, "41-50": 3, "31-40": 2, "21-30": 1, None: 0, np.nan: 0}
    summary_df["_awake_rank"] = summary_df["Best Awake Class"].map(
        lambda x: awake_order.get(x, 0)
    )
    summary_df = (
        summary_df
        .sort_values(
            ["Is Sleeping Beauty", "_awake_rank", "Best Sleep Length (s)"],
            ascending=[False, False, False]
        )
        .drop(columns=["_awake_rank"])
        .reset_index(drop=True)
    )
    detail_df = pd.DataFrame(detail_rows)
    history_df = pd.DataFrame(history_rows)

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="VanRaanExt_Summary", index=False)
        detail_df.to_excel(writer, sheet_name="VanRaanExt_AllMatches", index=False)
        history_df.to_excel(writer, sheet_name="Citation_History", index=False)

        notes_df = pd.DataFrame({
            "Notice": [
                "METHODOLOGICAL NOTE - THIS IS AN EXTENDED / MODIFIED METHOD",
                "",
                f"This sheet uses sleep lengths s = {min_s} to {max_s} years, "
                "which is WIDER than the original van Raan (2004) definition "
                "(s = 5 to 10 years only).",
                "",
                "This is NOT the original van Raan (2004) method. It is a variant "
                "designed to detect longer-dormancy Sleeping Beauties that the "
                "original method cannot find by construction. Use the separate "
                "'van Raan (2004)' results if you need the original, literature-"
                "faithful classification.",
                "",
                "'Sufficient History for max_s' flags whether each paper has enough "
                "years of citation data to be fairly tested at the requested max_s. "
                "Papers published too recently to have reached "
                f"{max_s + 4} years of history should be interpreted with caution "
                "if classified 'No' - they may simply be too young to show a long "
                "dormancy/awakening pattern yet, not genuinely non-Sleeping-Beauties.",
                "",
                "As with the original method, self-citations are NOT excluded from "
                "cs/cw here, which is also a deviation from van Raan's original "
                "self-citation-filtered methodology."
            ]
        })
        notes_df.to_excel(writer, sheet_name="Notes", index=False)

    return len(summary_df)
# ==================================================
# Standalone test
# ==================================================
if __name__ == "__main__":
    BASE = Path(__file__).resolve().parent.parent
    count = run_vanraan_extended(
        BASE / "outputs" / "master_dataset.xlsx",
        BASE / "outputs" / "VanRaanExtended_results.xlsx",
        min_s=5,
        max_s=30
    )
    print(f"Processed {count} papers")
