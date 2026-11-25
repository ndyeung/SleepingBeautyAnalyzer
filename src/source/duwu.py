from pathlib import Path
import pandas as pd
import numpy as np


# ==================================================
# Du & Wu (2018)
# ==================================================

def calculate_bcp(citation_df):

    df = citation_df.copy()

    total_citations = df["Citations"].sum()

    if total_citations == 0:

        return {
            "Bcp": np.nan,
            "AwakeningYear": np.nan,
            "SleepLength": np.nan,
            "SleepDepth": np.nan,
            "TotalCitations": 0
        }

    df["CumCitation"] = df["Citations"].cumsum()

    df["CumPercent"] = (
        df["CumCitation"]
        / total_citations
    )

    c0 = df["CumPercent"].iloc[0]

    tm = len(df) - 1

    if tm == 0:

        return {
            "Bcp": np.nan,
            "AwakeningYear": df["Year"].iloc[0],
            "SleepLength": 0,
            "SleepDepth": np.nan,
            "TotalCitations": total_citations
        }

    df["t"] = np.arange(len(df))

    df["y_t"] = (
        ((1 - c0) / tm) * df["t"]
        + c0
    )

    df["Difference"] = (
        df["y_t"]
        - df["CumPercent"]
    )

    bcp = df["Difference"].sum()

    df["Distance"] = (
        np.abs(
            (1 - c0) * df["t"]
            - tm * (df["CumPercent"] - c0)
        )
        /
        np.sqrt(
            (1 - c0) ** 2
            + tm ** 2
        )
    )

    awakening_position = int(
        df["Distance"]
        .to_numpy()
        .argmax()
    )

    awakening_year = int(
        df.loc[
            awakening_position,
            "Year"
        ]
    )

    publication_year = int(
        df.loc[0, "Year"]
    )

    sleep_length = (
        awakening_year
        - publication_year
    )

    if awakening_position > 0:

        sleep_depth = df.loc[
            awakening_position - 1,
            "CumPercent"
        ]

    else:

        sleep_depth = 0

    return {
        "Bcp": float(bcp),
        "AwakeningYear": awakening_year,
        "SleepLength": int(sleep_length),
        "SleepDepth": float(sleep_depth),
        "TotalCitations": int(total_citations)
    }


# ==================================================
# Main Analysis Function
# ==================================================

def run_duwu(
        input_file,
        output_file):

    wos = pd.read_excel(
        input_file,
        sheet_name="MasterData"
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

    paper_number = 1

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
    wos = wos.drop(
        columns=["SortTitle"]
    )    
    for _, row in wos.iterrows():

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

        result = calculate_bcp(
            citation_df
        )

        pid = paper_number

        results.append({

            "Paper Number":
            pid,

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

            "Bcp":
            result["Bcp"],

            "Awakening Year":
            result["AwakeningYear"],

            "Sleep Length":
            result["SleepLength"],

            "Sleep Depth":
            result["SleepDepth"]

        })

        history_row = {

            "Paper Number":
            pid,

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

        paper_number += 1

    results_df = pd.DataFrame(
        results
    )

    results_df = (
        results_df
        .sort_values(
            "Bcp",
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
            sheet_name="Bcp_Summary",
            index=False
        )

        history_df.to_excel(
            writer,
            sheet_name="Citation_History",
            index=False
        )

    return len(results_df)


# ==================================================
# Standalone test
# ==================================================

if __name__ == "__main__":

    count = run_duwu(

        "../outputs/master_dataset.xlsx",

        "../outputs/DuWu_results.xlsx"

    )

    print(
        f"Processed {count} papers"
    )
