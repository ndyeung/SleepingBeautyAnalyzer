from pathlib import Path
import pandas as pd
import numpy as np

# ==================================================
# Van Raan (2004) - Sleeping Beauties in Science
# ==================================================
#
# NOTE ON SELF-CITATIONS:
# Van Raan (2004) explicitly excludes self-citations when computing
# both cs (sleep depth) and cw (awake intensity). A standard WoS
# Citation Report export provides only total per-year citation counts
# (self-citations included). This implementation therefore computes
# cs and cw from TOTAL citations - a known, documented deviation from
# the original paper's self-citation-excluded methodology.
# ==================================================

SLEEP_LENGTHS = range(5, 11)  # s = 5,6,7,8,9,10 (as defined in the paper)


def classify_sleep_depth(cs, s):
    """
    cs = total citations accumulated during the s-year sleeping period.
    Deep sleep:      cs in [0, s]      (<=1 citation/year on average)
    Less deep sleep: cs in [s+1, 2s]   (1-2 citations/year on average)
    Anything above 2s does not qualify as "sleeping" for this s.
    """
    if cs <= s:
        return "deep"
    elif cs <= 2 * s:
        return "less_deep"
    else:
        return None


def classify_awake_intensity(cw):
    """
    cw = total citations accumulated during the 4-year awakening window
    immediately following the sleeping period.
    Classes as defined in van Raan (2004): [21,30],[31,40],[41,50],[51,60],>60
    cw < 21 does not qualify as an "awakening" under this scheme.
    """
    if cw > 60:
        return ">60"
    elif 51 <= cw <= 60:
        return "51-60"
    elif 41 <= cw <= 50:
        return "41-50"
    elif 31 <= cw <= 40:
        return "31-40"
    elif 21 <= cw <= 30:
        return "21-30"
    else:
        return None


# Ordering used to rank "how extreme" a qualifying combination is,
# mirroring van Raan's own framing of the most extreme case
# (s=10, cs=0, cw>60) as the most notable Sleeping Beauty.
_AWAKE_RANK = {
    ">60": 5,
    "51-60": 4,
    "41-50": 3,
    "31-40": 2,
    "21-30": 1,
    None: 0
}
_SLEEP_RANK = {"deep": 2, "less_deep": 1, None: 0}


def analyze_paper_sleeping_beauty(citation_df, publication_year, s_values=SLEEP_LENGTHS):
    """
    citation_df: DataFrame with columns ["Year", "Citations"], covering
                 the paper's full citation history from publication year
                 onward.
    publication_year: int, year of publication (t0).

    Returns:
        all_matches: list of dicts, one per qualifying (s, cs, cw) combo
        best_match: dict, the single most "extreme" qualifying combo
                    (or None if the paper never qualifies as a Sleeping Beauty)
    """
    citation_map = dict(
        zip(citation_df["Year"], citation_df["Citations"])
    )

    all_matches = []

    for s in s_values:
        sleep_years = [publication_year + i for i in range(s)]
        cs = sum(citation_map.get(y, 0) for y in sleep_years)
        sleep_class = classify_sleep_depth(cs, s)
        if sleep_class is None:
            continue  # too heavily cited during "sleep" -> not sleeping for this s

        awake_years = [publication_year + s + i for i in range(4)]
        cw = sum(citation_map.get(y, 0) for y in awake_years)
        awake_class = classify_awake_intensity(cw)
        if awake_class is None:
            continue  # not enough citations in awakening window -> no match

        all_matches.append({
            "SleepLength_s": s,
            "SleepCitations_cs": int(cs),
            "SleepClass": sleep_class,
            "AwakeCitations_cw": int(cw),
            "AwakeClass": awake_class
        })

    if not all_matches:
        return all_matches, None

    best_match = max(
        all_matches,
        key=lambda m: (
            _AWAKE_RANK[m["AwakeClass"]],
            _SLEEP_RANK[m["SleepClass"]],
            m["SleepLength_s"]
        )
    )

    return all_matches, best_match


# ==================================================
# Main Analysis Function
# ==================================================
def run_vanraan(input_file, output_file):
    wos = pd.read_excel(
        input_file,
        sheet_name="MasterData"
    )

    # Stable paper numbering (same convention as duwu.py / ke.py)
    wos["SortTitle"] = (
        wos["Title"]
        .astype(str)
        .str.replace(r"<[^>]+>", "", regex=True)
        .str.strip()
        .str.lower()
    )
    wos = (
        wos
        .sort_values("SortTitle")
        .reset_index(drop=True)
    )
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

        all_matches, best_match = analyze_paper_sleeping_beauty(
            citation_df, publication_year
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
    # Rank: Sleeping Beauties first, then by awake intensity / sleep length
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
        summary_df.to_excel(writer, sheet_name="VanRaan_Summary", index=False)
        detail_df.to_excel(writer, sheet_name="VanRaan_AllMatches", index=False)
        history_df.to_excel(writer, sheet_name="Citation_History", index=False)

        # ------------------------------------------------
        # Methodological caveat sheet (self-citations)
        # ------------------------------------------------
        notes_df = pd.DataFrame({
            "Notice": [
                "METHODOLOGICAL CAVEAT - SELF-CITATIONS",
                "",
                "Van Raan (2004) explicitly computes both 'depth of sleep' (cs) and "
                "'awake intensity' (cw) using citation counts with SELF-CITATIONS EXCLUDED.",
                "",
                "This tool computes cs and cw from TOTAL citation counts as provided by the "
                "Web of Science Citation Report export, which does NOT separate out self-citations.",
                "",
                "As a result, cs and cw values in this file may be somewhat HIGHER than the "
                "values van Raan's original method would produce. This can, in some cases, cause "
                "a paper to be classified as 'less deep sleep' instead of 'deep sleep', or to "
                "narrowly miss the sleep/awake thresholds entirely.",
                "",
                "If a self-citation-filtered citation history becomes available, it should be used "
                "in place of the raw per-year citation counts to fully replicate the original "
                "Van Raan (2004) methodology.",
                "",
                "Reference: van Raan, A.F.J. (2004). Sleeping Beauties in science. "
                "Scientometrics, 59(3), 467-472."
            ]
        })
        notes_df.to_excel(writer, sheet_name="Notes", index=False)

    return len(summary_df)


# ==================================================
# Standalone test
# ==================================================
if __name__ == "__main__":
    BASE = Path(__file__).resolve().parent.parent
    count = run_vanraan(
        BASE / "outputs" / "master_dataset.xlsx",
        BASE / "outputs" / "VanRaan_results.xlsx"
    )
    print(f"Processed {count} papers")
