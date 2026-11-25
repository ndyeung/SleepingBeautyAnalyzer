from pathlib import Path
import pandas as pd
import numpy as np


# ==================================================
# Ke et al. (2015)
# Beauty Coefficient
# ==================================================

def calculate_beauty_coefficient(citation_df):

    df = citation_df.copy()

    citations = (
        pd.to_numeric(
            df["Citations"],
            errors="coerce"
        )
        .fillna(0)
        .clip(lower=0)
        .to_numpy()
    )

    n = len(citations)

    if n == 0:
        return {
            "BeautyCoefficient": np.nan,
            "PeakYear": np.nan,
            "PeakCitations": np.nan,
            "AwakeningYear": np.nan,
            "TotalCitations": 0
        }

    total_citations = citations.sum()

    if total_citations == 0:
        return {
            "BeautyCoefficient": 0,
            "PeakYear": np.nan,
            "PeakCitations": 0,
            "AwakeningYear": np.nan,
            "TotalCitations": 0
        }

    # Peak citation year
    peak_idx = int(np.argmax(citations))


    c0 = citations[0]
    ctm = citations[peak_idx]

    tm = peak_idx

    # Ke et al. define B = 0 if tm = 0
    if tm == 0:
        return {
            "BeautyCoefficient": 0,
            "PeakYear": int(df.loc[0, "Year"]),
            "PeakCitations": int(ctm),
            "AwakeningYear": int(df.loc[0, "Year"]),
            "TotalCitations": int(total_citations)
        }

    beauty = 0
    for t in range(tm + 1):
        ct = citations[t]
        lt = ((ctm - c0) / tm) * t + c0
        score = (lt - ct) / max(1, ct)
        beauty += score

    # Awakening time via point-to-line distance (Eq. 3)
    denom = np.sqrt((ctm - c0)**2 + tm**2)
    distances = []
    for t in range(tm + 1):
        ct = citations[t]
        dt = abs((ctm - c0) * t - tm * ct + tm * c0) / denom
        distances.append(dt)
    awakening_idx = int(np.argmax(distances))

    awakening_year = int(
        df.loc[
            awakening_idx,
            "Year"
        ]
    )

    peak_year = int(
        df.loc[
            peak_idx,
            "Year"
        ]
    )


    return {
        "BeautyCoefficient":
            float(beauty),

        "PeakYear":
            peak_year,

        "PeakCitations":
            int(ctm),

        "AwakeningYear":
            awakening_year,

        "TotalCitations":
            int(total_citations)
    }


# ==================================================
# Main Analysis Function
# ==================================================

def run_ke(
        input_file,
        output_file):

    wos = pd.read_excel(
        input_file,
        sheet_name="MasterData"
    )

    # Stable paper numbering
    wos["SortTitle"] = (
        wos["Title"]
        .astype(str)
        .str.replace(
            r"<[^>]+>",
            "",
            regex=True
        )
        .str.strip()
        .str.lower()
    )

    wos = (
        wos
        .sort_values("SortTitle")
        .reset_index(drop=True)
    )

    wos = wos.drop(
        columns=["SortTitle"]
    )

    year_columns = []

    for col in wos.columns:

        try:

            year = int(str(col))

            if (
                year >= 1950
                and
                year <= 2100
            ):

                year_columns.append(col)

        except:
            pass

    year_columns = sorted(
        year_columns,
        key=int
    )

    results = []

    history_rows = []

    for paper_number, (_, row) in enumerate(
            wos.iterrows(),
            start=1):

        if pd.isna(
            row["Publication Year"]
        ):
            continue

        publication_year = int(
            row["Publication Year"]
        )

        paper_years = [

            col

            for col
            in year_columns

            if int(col)
            >= publication_year

        ]

        history_complete = (
            str(publication_year)
            in [str(x) for x in year_columns]
        )

        citations = []

        for col in paper_years:

            value = pd.to_numeric(
                row[col],
                errors="coerce"
            )

            if pd.isna(value):
                value = 0

            citations.append(value)

        citation_df = pd.DataFrame({

            "Year":
            [int(y) for y in paper_years],

            "Citations":
            citations

        })

        result = calculate_beauty_coefficient(
            citation_df
        )

        sleep_length = (
            result["AwakeningYear"] - publication_year
            if not pd.isna(result["AwakeningYear"]) else np.nan
        )
        
        results.append({

            "Paper Number":
            paper_number,

            "Title":
            row["Title"],

            "Journal":
            row["Source Title"],

            "Publication Year":
            publication_year,

            "Total Citations":
            result["TotalCitations"],

            "Complete Citation History":
                "Yes"
                if history_complete
                else "No",

            "Beauty Coefficient":
            result["BeautyCoefficient"],

            "Peak Citation Year":
            result["PeakYear"],

            "Peak Citations":
            result["PeakCitations"],

            "Awakening Year":
            result["AwakeningYear"],
            
            "Sleep Length": sleep_length

        })

        history_row = {

            "Paper Number":
            paper_number,

            "Title":
            row["Title"],

            "Journal":
            row["Source Title"],

            "Publication Year":
            publication_year,

            "Complete Citation History":
                "Yes"
                if history_complete
                else "No",
            

        }

        for i, c in enumerate(citations):

            history_row[
                f"Year {i+1}"
            ] = c

        history_rows.append(
            history_row
        )

    results_df = pd.DataFrame(
        results
    )

    results_df = (
        results_df
        .sort_values(
            "Beauty Coefficient",
            ascending=False,
            na_position="last"
        )
        .reset_index(drop=True)
    )

    results_df.insert(
        0,
        "Rank",
        range(
            1,
            len(results_df) + 1
        )
    )

    history_df = pd.DataFrame(
        history_rows
    )

    with pd.ExcelWriter(
            output_file,
            engine="openpyxl"
    ) as writer:

        results_df.to_excel(
            writer,
            sheet_name="Ke_Summary",
            index=False
        )

        history_df.to_excel(
            writer,
            sheet_name="Citation_History",
            index=False
        )

    return len(results_df)


if __name__ == "__main__":

    BASE = (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )

    count = run_ke(
        BASE / "outputs" / "master_dataset.xlsx",
        BASE / "outputs" / "Ke_results.xlsx"
    )

    print(
        f"Processed {count} papers"
    )
