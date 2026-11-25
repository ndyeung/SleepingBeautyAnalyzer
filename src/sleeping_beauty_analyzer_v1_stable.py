import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
from tkinter import simpledialog
import pandas as pd
import re
import sys
import os
import subprocess

from source.duwu import run_duwu
from source.ke import run_ke
from source.vanraan import run_vanraan
from source.vanraan_extended import run_vanraan_extended
from source.compare import run_comparison
from source.trajectory_plot import generate_trajectory_figures


# ==================================================
# Module-level helper functions (Scopus import)
# ==================================================
def _find_scopus_header_row_index(raw_df, search_rows=12):
    """
    Scans the first few rows for the one containing BOTH a '<N' and
    a '>M' marker - this is the year-header row, regardless of whether
    it lands on row 6, 7, or 8 depending on Scopus export settings
    (e.g., self-citation exclusion shifts row positions by one).
    """
    for i in range(min(search_rows, len(raw_df))):
        row = raw_df.iloc[i].astype(str).str.strip()
        has_lt = row.str.startswith("<").any()
        has_gt = row.str.startswith(">").any()
        if has_lt and has_gt:
            return i
    return None

def _parse_scopus_header_row(raw_df, header_row_index):
    """
    Parses the year-header row at the given (dynamically detected) index.
    Columns before the first '<' marker are blank/metadata placeholders.
    Column at and after the '<' marker contains: '<N', individual years,
    'Subtotal', '>M', 'Total' - in that fixed order.
    Returns: dict mapping column index -> label, plus parsed N and M.
    """
    header_row = raw_df.iloc[header_row_index]
    col_map = {}
    lower_n = None
    upper_m = None
    for idx in range(len(header_row)):
        val = str(header_row[idx]).strip()
        if val.startswith("<"):
            try:
                lower_n = int(re.sub(r"[^0-9]", "", val))
                col_map[idx] = f"<{lower_n}"
            except ValueError:
                pass
        elif val.startswith(">"):
            try:
                upper_m = int(re.sub(r"[^0-9]", "", val))
                col_map[idx] = f">{upper_m}"
            except ValueError:
                pass
        elif val.lower() == "subtotal":
            col_map[idx] = "Subtotal"
        elif val.lower() == "total":
            col_map[idx] = "Total"
        else:
            # Handle both "2001" (int string) and "2001.0" (float string)
            try:
                year_int = int(float(val))
                if 1950 <= year_int <= 2100:
                    col_map[idx] = str(year_int)
            except (ValueError, TypeError):
                pass
    if lower_n is None or upper_m is None:
        raise ValueError(
            "Could not find '<N' or '>M' markers in the detected header row "
            "of the Scopus export. The file structure may not match the "
            "expected format."
        )
    return col_map, lower_n, upper_m


def _passes_lower_n_zero_check(value):
    """
    Returns True only if the '<N' cell is explicitly numeric and equal to 0.
    Blank/NaN is treated as 'cannot verify' and therefore fails this check
    (paper gets excluded under the 'keep <N=0 only' option), rather than
    being assumed to be 0.
    """
    if pd.isna(value):
        return False
    numeric_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric_value):
        return False
    return numeric_value == 0

def convert_scopus_dataframe(raw_df, source_name):
    """
    Converts a raw Scopus Citation Overview CSV (read with header=None)
    into a WoS-shaped DataFrame, plus a boolean mask marking rows that
    have unverifiable pre-range citation counts (the '<N' problem rows).

    Returns: (converted_df, problem_rows_mask, lower_n)
    """
    # ------------------------------------------------
    # Step 1: Find year-header row dynamically
    # ------------------------------------------------
    header_row_index = _find_scopus_header_row_index(raw_df)
    if header_row_index is None:
        raise ValueError(
            f"Could not locate the year-header row ('<N' / '>M' markers) "
            f"anywhere in the first 12 rows of '{source_name}'. "
            "The file structure may not match the expected Scopus "
            "Citation Overview export format."
        )

    col_map, lower_n, upper_m = _parse_scopus_header_row(
        raw_df, header_row_index
    )

    # ------------------------------------------------
    # Step 2: Find sub-header row dynamically
    # Scan forward from year-header row until we find
    # a row containing "Publication Year" as a cell.
    # This skips the totals row that sits between them.
    # ------------------------------------------------
    sub_header_row_index = None
    for i in range(header_row_index + 1, min(header_row_index + 5, len(raw_df))):
        row_vals = raw_df.iloc[i].astype(str).str.strip().str.lower()
        if row_vals.str.contains("publication year").any():
            sub_header_row_index = i
            break

    if sub_header_row_index is None:
        raise ValueError(
            f"Could not locate the sub-header row ('Publication Year', "
            f"'Document Title', etc.) in '{source_name}'. "
            "The file structure may not match the expected Scopus "
            "Citation Overview export format."
        )

    # ------------------------------------------------
    # Step 3: Data starts immediately after sub-header
    # ------------------------------------------------
    data_start_index = sub_header_row_index + 1
    data = raw_df.iloc[data_start_index:].reset_index(drop=True)

    # ------------------------------------------------
    # Step 4: Build rename dict from col_map (year cols)
    # plus sub-header row text (metadata cols A-F)
    # ------------------------------------------------
    sub_header_row = raw_df.iloc[sub_header_row_index]
    rename_dict = dict(col_map)
    for idx in range(len(sub_header_row)):
        label = str(sub_header_row[idx]).strip()
        if label and label.lower() != "nan" and idx not in rename_dict:
            rename_dict[idx] = label

    data = data.rename(columns=rename_dict)

    # ------------------------------------------------
    # Step 5: Deduplicate column names (safety net)
    # ------------------------------------------------
    cols = pd.Series(data.columns)
    for dup in cols[cols.duplicated()].unique():
        dup_indices = cols[cols == dup].index.tolist()
        for i, idx in enumerate(dup_indices):
            if i != 0:
                cols[idx] = f"{dup}_{i}"
    data.columns = cols

    # ------------------------------------------------
    # Step 6: Normalize column names to WoS-style
    # ------------------------------------------------
    if "Document Title" in data.columns:
        data["Title"] = data["Document Title"]
    if "Journal Title" in data.columns:
        data["Source Title"] = data["Journal Title"]
    data["__source_file"] = source_name

    if "Publication Year" not in data.columns:
        raise ValueError(
            f"Could not find a 'Publication Year' column in '{source_name}' "
            "after parsing. Please check the file matches the expected "
            "Scopus Citation Overview format."
        )

    data["Publication Year"] = pd.to_numeric(
        data["Publication Year"], errors="coerce"
    )

    # ------------------------------------------------
    # Step 7: Drop rows with no Publication Year
    # (catches any stray blank/summary rows at bottom)
    # ------------------------------------------------
    data = data[data["Publication Year"].notna()].reset_index(drop=True)

    # ------------------------------------------------
    # Step 8: <N exclusion check
    # ------------------------------------------------
    lower_n_col = f"<{lower_n}"
    if lower_n_col in data.columns:
        lower_n_values = data[lower_n_col]
    else:
        lower_n_values = pd.Series([None] * len(data), index=data.index)

    too_old = data["Publication Year"] < lower_n
    verified_zero = lower_n_values.apply(_passes_lower_n_zero_check)
    problem_rows = too_old & ~verified_zero

    # ------------------------------------------------
    # Step 9: Drop Scopus-specific aggregate columns
    # not needed downstream
    # ------------------------------------------------
    drop_cols = [
        c for c in data.columns
        if str(c).startswith("<") or str(c).startswith(">")
        or c in ("Subtotal", "Total")
    ]
    data = data.drop(columns=drop_cols, errors="ignore")

    # ------------------------------------------------
    # Step 9b: Normalize year column names to integers
    # (matching WoS export convention) - needed so Step 10
    # below can correctly identify existing year columns
    # via isinstance(c, int), and so int/string year labels
    # don't create duplicate columns when later merged with
    # WoS data.
    # ------------------------------------------------
    new_cols = []
    for col in data.columns:
        try:
            year_int = int(str(col))
            if 1950 <= year_int <= 2100:
                new_cols.append(year_int)
            else:
                new_cols.append(col)
        except (ValueError, TypeError):
            new_cols.append(col)
    data.columns = new_cols

    return data, problem_rows, lower_n

def insert_missing_prerange_years(data, lower_n):
    """
    Inserts explicit zero-citation columns for every year between
    each surviving paper's publication year and lower_n (exclusive).
    Must only be called AFTER exclusion filtering, so that
    min_pub_year reflects only papers that actually remain in the
    final dataset - not papers that were later removed.
    """
    if len(data) == 0:
        return data
    min_pub_year = int(data["Publication Year"].min())
    for year in range(min_pub_year, lower_n):
        if year not in data.columns:
            data[year] = 0
    year_cols_existing = sorted(
        [c for c in data.columns if isinstance(c, int)]
    )
    non_year_cols = [c for c in data.columns if not isinstance(c, int)]
    return data[non_year_cols + year_cols_existing]

class SleepingBeautyAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title(
            "Sleeping Beauty Analyzer v1_stable"
        )
        self.root.geometry("1500x700")
        self.root.minsize(1300, 650)

        # Unified storage: each entry is a dict with keys
        # "label" (string shown in listbox) and "df" (DataFrame, WoS-shaped)
        self.loaded_dataframes = []
        self.build_gui()

    # =====================================================
    # GUI
    # =====================================================
    def build_gui(self):
        title = tk.Label(
            self.root,
            text="Sleeping Beauty Analyzer v1_stable",
            font=("Arial", 18, "bold")
        )
        title.pack(pady=10)

        frame_buttons_row1 = tk.Frame(self.root)
        frame_buttons_row1.pack(pady=5)
        tk.Button(
            frame_buttons_row1,
            text="Add WoS Citation Report Files",
            command=self.add_wos_files,
            width=28
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            frame_buttons_row1,
            text="Add Scopus Citation Overview Files",
            command=self.add_scopus_files,
            width=30
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            frame_buttons_row1,
            text="Merge and Clean Dataset",
            command=self.merge_files,
            width=25
        ).pack(side=tk.LEFT, padx=5)


        tk.Button(
            frame_buttons_row1,
            text="Reset Loaded Files",
            command=self.reset_loaded_files,
            width=20
        ).pack(side=tk.LEFT, padx=5)

        frame_buttons_row2 = tk.Frame(self.root)
        frame_buttons_row2.pack(pady=5)
        tk.Button(
            frame_buttons_row2,
            text="Run Du & Wu (2018)",
            command=self.run_duwu_analysis,
            width=25
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            frame_buttons_row2,
            text="Run Ke et al. (2015)",
            command=self.run_ke_analysis,
            width=25
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            frame_buttons_row2,
            text="Run van Raan (2004)",
            command=self.run_vanraan_analysis,
            width=25
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            frame_buttons_row2,
            text="Compare All Methods",
            command=self.run_comparison_analysis,
            width=25
        ).pack(side=tk.LEFT, padx=5)

        frame_buttons_row3 = tk.Frame(self.root)
        frame_buttons_row3.pack(pady=5)
        tk.Button(
            frame_buttons_row3,
            text="Generate Trajectory Figures",
            command=self.generate_figures,
            width=25
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            frame_buttons_row3,
            text="Run van Raan Extended",
            command=self.run_vanraan_extended_analysis,
            width=25
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            frame_buttons_row3,
            text="Open Output Folder",
            command=self.open_output_folder,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        self.file_listbox = tk.Listbox(
            self.root,
            width=120,
            height=18
        )
        self.file_listbox.pack(
            padx=10,
            pady=10,
            fill=tk.BOTH,
            expand=True
        )

        stats_frame = tk.Frame(self.root)
        stats_frame.pack(pady=5)
        self.files_label = tk.Label(
            stats_frame,
            text="Files Loaded: 0"
        )
        self.files_label.pack(anchor="w")
        self.records_label = tk.Label(
            stats_frame,
            text="Records Imported: -"
        )
        self.records_label.pack(anchor="w")
        self.duplicates_label = tk.Label(
            stats_frame,
            text="Duplicates Removed: -"
        )
        self.duplicates_label.pack(anchor="w")
        self.final_label = tk.Label(
            stats_frame,
            text="Final Records: -"
        )
        self.final_label.pack(anchor="w")
        self.status_label = tk.Label(
            self.root,
            text="Status: Ready",
            fg="blue"
        )
        self.status_label.pack(pady=10)

    def _refresh_file_listbox(self):
        self.file_listbox.delete(0, tk.END)
        for entry in self.loaded_dataframes:
            self.file_listbox.insert(tk.END, entry["label"])
        self.files_label.config(
            text=f"Files Loaded: {len(self.loaded_dataframes)}"
        )

    def reset_loaded_files(self):
        if not self.loaded_dataframes:
            return
        confirm = messagebox.askyesno(
            "Reset Loaded Files",
            f"This will clear all {len(self.loaded_dataframes)} loaded file(s) "
            "from memory. This does NOT delete any files already saved to disk "
            "(e.g., master_dataset.xlsx).\n\nContinue?"
        )
        if not confirm:
            return
        self.loaded_dataframes = []
        self._refresh_file_listbox()
        self.records_label.config(text="Records Imported: -")
        self.duplicates_label.config(text="Duplicates Removed: -")
        self.final_label.config(text="Final Records: -")
        self.status_label.config(text="Status: Ready", fg="blue")

    # =====================================================
    # Add WoS Files
    # =====================================================
    def add_wos_files(self):
        # Check for Scopus files already loaded
        has_scopus = any(
            entry.get("source_path", "").endswith(".csv")
            for entry in self.loaded_dataframes
        )
        if has_scopus:
            messagebox.showerror(
                "Mixed Sources Not Allowed",
                "Scopus files are already loaded.\n\n"
                "WoS and Scopus citation counts are not directly comparable "
                "(different database coverage, indexing rules, and self-citation "
                "handling). Mixing them in the same dataset would produce "
                "unreliable results.\n\n"
                "Please click 'Reset Loaded Files' first if you want to "
                "switch to WoS files."
            )
            return
        files = filedialog.askopenfilenames(
            title="Select Web of Science Citation Report Files",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if not files:
            return
        try:
            already_loaded = {
                entry.get("source_path") for entry in self.loaded_dataframes
            }
            skipped = []
            for f in files:
                if f in already_loaded:
                    skipped.append(Path(f).name)
                    continue
                
                df = pd.read_excel(f, skiprows=10)
                self.loaded_dataframes.append({
                    "label": f"[WoS] {f}",
                    "df": df,
                    "source_path": f
                })
            self._refresh_file_listbox()
            if skipped:
                messagebox.showinfo(
                    "Duplicate Files Skipped",
                    "Already loaded, skipped:\n\n" + "\n".join(skipped)
                )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_scopus_files(self):
        # Check for WoS files already loaded
        has_wos = any(
            entry.get("source_path", "").endswith((".xlsx", ".xls"))
            for entry in self.loaded_dataframes
        )
        if has_wos:
            messagebox.showerror(
                "Mixed Sources Not Allowed",
                "WoS files are already loaded.\n\n"
                "WoS and Scopus citation counts are not directly comparable "
                "(different database coverage, indexing rules, and self-citation "
                "handling). Mixing them in the same dataset would produce "
                "unreliable results.\n\n"
                "Please click 'Reset Loaded Files' first if you want to "
                "switch to Scopus files."
            )
            return
        files = filedialog.askopenfilenames(
            title="Select Scopus Citation Overview Export Files (.csv)",
            filetypes=[("CSV files", "*.csv")]
        )
        if not files:
            return
        try:
            already_loaded = {
                entry.get("source_path") for entry in self.loaded_dataframes
            }
            skipped = []
            file_results = []
            for f in files:
                if f in already_loaded:
                    skipped.append(Path(f).name)
                    continue
                try:
                    raw_df = pd.read_csv(f, header=None)
                except Exception as csv_error:
                    raise ValueError(
                        f"Could not read '{Path(f).name}' as a CSV file.\n\n"
                        f"This usually means the file is corrupted, is not a "
                        f"valid Scopus Citation Overview export, or was saved "
                        f"in an unexpected format.\n\n"
                        f"Technical details: {csv_error}"
                    )
                converted_df, problem_rows, lower_n = convert_scopus_dataframe(
                    raw_df, source_name=Path(f).name
                )
                file_results.append({
                    "file": f,
                    "converted_df": converted_df,
                    "problem_rows": problem_rows,
                    "lower_n": lower_n
                })
            total_problems = sum(r["problem_rows"].sum() for r in file_results)
            choice = None
            if total_problems > 0:
                n_files_affected = sum(
                    1 for r in file_results if r["problem_rows"].any()
                )
                choice = messagebox.askyesnocancel(
                    "Pre-Range Citations Detected",
                    f"Across {n_files_affected} file(s), {total_problems} paper(s) "
                    "were published before the earliest year shown in their "
                    "respective Scopus export range, with unverifiable "
                    "(non-zero or blank) pre-range citation counts.\n\n"
                    "This choice will apply to ALL affected files in this batch.\n\n"
                    "Click YES to keep only papers published WITHIN each file's "
                    "visible range.\n"
                    "Click NO to keep only papers with a verified ZERO in the "
                    "pre-range bucket.\n"
                    "Click CANCEL to skip ALL affected files in this batch "
                    "(unaffected files will still be added)."
                )
            for r in file_results:
                converted_df = r["converted_df"]
                problem_rows = r["problem_rows"]
                lower_n = r["lower_n"]
                f = r["file"]
                if problem_rows.any():
                    if choice is None:
                        continue
                    elif choice is True:
                        keep_mask = converted_df["Publication Year"] >= lower_n
                    else:
                        keep_mask = ~problem_rows
                    excluded_df = converted_df[~keep_mask].copy()
                    kept_df = converted_df[keep_mask].copy()
                else:
                    excluded_df = converted_df.iloc[0:0].copy()
                    kept_df = converted_df.copy()
                kept_df = insert_missing_prerange_years(kept_df, lower_n)
                entry = {
                    "label": f"[Scopus] {f} "
                             f"(kept {len(kept_df)}, excluded {len(excluded_df)})",
                    "df": kept_df,
                    "source_path": f
                }
                if len(excluded_df) > 0:
                    entry["excluded_df"] = excluded_df
                self.loaded_dataframes.append(entry)
            self._refresh_file_listbox()
            if skipped:
                messagebox.showinfo(
                    "Duplicate Files Skipped",
                    "Already loaded, skipped:\n\n" + "\n".join(skipped)
                )
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    # =====================================================
    # Merge Logic
    # =====================================================
    def merge_files(self):
        if len(self.loaded_dataframes) == 0:
            messagebox.showwarning(
                "No Files",
                "Please add one or more files first."
            )
            return
        try:
            all_frames = [entry["df"] for entry in self.loaded_dataframes]
            import_count = sum(len(df) for df in all_frames)

            merged = pd.concat(all_frames, ignore_index=True)
            before = len(merged)

            # =================================================
            # Deduplicate
            # =================================================
            if "DOI" in merged.columns:
                has_doi = merged[merged["DOI"].notna()]
                no_doi = merged[merged["DOI"].isna()]
                has_doi = has_doi.drop_duplicates(subset=["DOI"])
                if "Title" in no_doi.columns and "Publication Year" in no_doi.columns:
                    no_doi = no_doi.drop_duplicates(
                        subset=["Title", "Publication Year"]
                    )
                merged = pd.concat([has_doi, no_doi], ignore_index=True)
            elif "Title" in merged.columns and "Publication Year" in merged.columns:
                merged = merged.drop_duplicates(
                    subset=["Title", "Publication Year"]
                )

            after = len(merged)
            duplicates_removed = before - after

            output_folder = (
                Path.home() / "Desktop" / "SleepingBeautyProject"
                / "SleepingBeautyAnalyzer" / "outputs"
            )
            output_folder.mkdir(parents=True, exist_ok=True)
            output_file = output_folder / "master_dataset.xlsx"

            # ================================================
            # Import log - built directly from already-loaded
            # DataFrames, no re-reading from disk needed
            # ================================================
            log_rows = [
                {"File": entry["label"], "Records": len(entry["df"])}
                for entry in self.loaded_dataframes
            ]
            log_df = pd.DataFrame(log_rows)

            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                merged.to_excel(writer, sheet_name="MasterData", index=False)
                log_df.to_excel(writer, sheet_name="ImportLog", index=False)

                all_excluded = [
                    entry["excluded_df"] for entry in self.loaded_dataframes
                    if "excluded_df" in entry
                ]
                if all_excluded:
                    excluded_combined = pd.concat(all_excluded, ignore_index=True)
                    excluded_combined.to_excel(
                        writer, sheet_name="Excluded_Scopus_Papers", index=False
                    )

            self.records_label.config(text=f"Records Imported: {import_count}")
            self.duplicates_label.config(
                text=f"Duplicates Removed: {duplicates_removed}"
            )
            self.final_label.config(text=f"Final Records: {len(merged)}")
            self.status_label.config(text="Status: Completed", fg="green")

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            messagebox.showinfo(
                "Completed",
                f"master_dataset.xlsx updated successfully\n\n"
                f"Timestamp: {timestamp}\n"
                f"Records Imported: {import_count}\n"
                f"Duplicates Removed: {duplicates_removed}\n"
                f"Final Records: {len(merged)}\n\n"
                f"Output:\n{output_file}"
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # Du & Wu Analysis
    # =====================================================
    def run_duwu_analysis(self):
        try:
            output_folder = (
                Path.home() / "Desktop" / "SleepingBeautyProject"
                / "SleepingBeautyAnalyzer" / "outputs"
            )
            input_file = output_folder / "master_dataset.xlsx"
            if not input_file.exists():
                messagebox.showerror(
                    "Error",
                    "master_dataset.xlsx not found.\n\n"
                    "Please run Merge and Clean Dataset first."
                )
                return
            output_file = output_folder / "DuWu_results.xlsx"
            self.status_label.config(
                text="Status: Running Du & Wu analysis...", fg="orange"
            )
            self.root.update()
            count = run_duwu(input_file, output_file)
            self.status_label.config(
                text="Status: Du & Wu analysis completed", fg="green"
            )
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            messagebox.showinfo(
                "Completed",
                f"DuWu_results.xlsx updated successfully\n\n"
                f"Timestamp: {timestamp}\n"
                f"Papers Processed: {count}\n\n"
                f"Output:\n{output_file}"
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # Ke et al. (2015)
    # =====================================================
    def run_ke_analysis(self):
        try:
            output_folder = (
                Path.home() / "Desktop" / "SleepingBeautyProject"
                / "SleepingBeautyAnalyzer" / "outputs"
            )
            input_file = output_folder / "master_dataset.xlsx"
            if not input_file.exists():
                messagebox.showerror(
                    "Error",
                    "master_dataset.xlsx not found.\n\n"
                    "Please run Merge and Clean Dataset first."
                )
                return
            output_file = output_folder / "Ke_results.xlsx"
            self.status_label.config(
                text="Status: Running Ke et al. (2015)...", fg="orange"
            )
            self.root.update()
            count = run_ke(input_file, output_file)
            self.status_label.config(
                text="Status: Ke et al. analysis completed", fg="green"
            )
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            messagebox.showinfo(
                "Completed",
                f"Ke_results.xlsx updated successfully\n\n"
                f"Timestamp: {timestamp}\n"
                f"Papers Processed: {count}\n\n"
                f"Output:\n{output_file}"
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # Van Raan (2004)
    # =====================================================
    def run_vanraan_analysis(self):
        try:
            output_folder = (
                Path.home() / "Desktop" / "SleepingBeautyProject"
                / "SleepingBeautyAnalyzer" / "outputs"
            )
            input_file = output_folder / "master_dataset.xlsx"
            if not input_file.exists():
                messagebox.showerror(
                    "Error",
                    "master_dataset.xlsx not found.\n\n"
                    "Please run Merge and Clean Dataset first."
                )
                return
            output_file = output_folder / "VanRaan_results.xlsx"
            self.status_label.config(
                text="Status: Running van Raan (2004)...", fg="orange"
            )
            self.root.update()
            count = run_vanraan(input_file, output_file)
            self.status_label.config(
                text="Status: van Raan analysis completed", fg="green"
            )
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            messagebox.showinfo(
                "Completed",
                f"VanRaan_results.xlsx updated successfully\n\n"
                f"Timestamp: {timestamp}\n"
                f"Papers Processed: {count}\n\n"
                f"Output:\n{output_file}"
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # Van Raan EXTENDED (not the original 2004 method)
    # =====================================================
    def run_vanraan_extended_analysis(self):
        try:
            output_folder = (
                Path.home() / "Desktop" / "SleepingBeautyProject"
                / "SleepingBeautyAnalyzer" / "outputs"
            )
            input_file = output_folder / "master_dataset.xlsx"
            if not input_file.exists():
                messagebox.showerror(
                    "Error",
                    "master_dataset.xlsx not found.\n\n"
                    "Please run Merge and Clean Dataset first."
                )
                return
            max_s = simpledialog.askinteger(
                "Van Raan Extended - Max Sleep Length",
                "Enter the maximum sleep length (in years) to test.\n\n"
                "The original van Raan (2004) method only tests s = 5 to 10.\n"
                "This extended version lets you test a wider range, e.g. s = 5 to 30.\n\n"
                "Enter the upper bound (max_s):",
                initialvalue=30,
                minvalue=10,
                maxvalue=60
            )
            if max_s is None:
                return
            output_file = output_folder / "VanRaanExtended_results.xlsx"
            self.status_label.config(
                text=f"Status: Running van Raan Extended (s=5-{max_s})...",
                fg="orange"
            )
            self.root.update()
            count = run_vanraan_extended(
                input_file, output_file, min_s=5, max_s=max_s
            )
            self.status_label.config(
                text="Status: van Raan Extended analysis completed", fg="green"
            )
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            messagebox.showinfo(
                "Completed",
                f"VanRaanExtended_results.xlsx updated successfully\n\n"
                f"Timestamp: {timestamp}\n"
                f"Sleep Length Range Tested: s = 5 to {max_s}\n"
                f"Papers Processed: {count}\n\n"
                f"Output:\n{output_file}"
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # Cross-Method Comparison
    # =====================================================
    def run_comparison_analysis(self):
        try:
            output_folder = (
                Path.home() / "Desktop" / "SleepingBeautyProject"
                / "SleepingBeautyAnalyzer" / "outputs"
            )
            bcp_file = output_folder / "DuWu_results.xlsx"
            ke_file = output_folder / "Ke_results.xlsx"
            vanraan_file = output_folder / "VanRaan_results.xlsx"
            vanraan_extended_file = output_folder / "VanRaanExtended_results.xlsx"

            missing = [
                f.name for f in [bcp_file, ke_file, vanraan_file]
                if not f.exists()
            ]
            if missing:
                messagebox.showerror(
                    "Error",
                    "The following result files are missing:\n\n"
                    + "\n".join(missing)
                    + "\n\nPlease run all three analyses "
                    "(Du & Wu, Ke et al., van Raan) first."
                )
                return

            has_extended = vanraan_extended_file.exists()
            output_file = output_folder / "Comparison_results.xlsx"
            self.status_label.config(
                text="Status: Running cross-method comparison...", fg="orange"
            )
            self.root.update()

            threshold = simpledialog.askfloat(
                "Comparison Threshold",
                "Enter top percentage for Bcp and B\n\n"
                "Examples:\n"
                "10 = top 10%\n"
                "1 = top 1%\n"
                "0.1 = top 0.1%",
                initialvalue=10
            )
            if threshold is None:
                return
            if threshold <= 0 or threshold > 100:
                messagebox.showerror(
                    "Error", "Please enter a value between 0 and 100."
                )
                return
            top_fraction = threshold / 100

            count = run_comparison(
                bcp_file,
                ke_file,
                vanraan_file,
                output_file,
                top_fraction=top_fraction,
                vanraan_extended_file=(
                    vanraan_extended_file if has_extended else None
                )
            )
            self.status_label.config(
                text="Status: Comparison completed", fg="green"
            )
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            extended_note = (
                "van Raan Extended results: INCLUDED"
                if has_extended else
                "van Raan Extended results: not found, skipped"
            )
            messagebox.showinfo(
                "Completed",
                f"Comparison_results.xlsx updated successfully\n\n"
                f"Timestamp: {timestamp}\n"
                f"Papers Compared: {count}\n"
                f"{extended_note}\n\n"
                f"Output:\n{output_file}"
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # Generate Trajectory Figures
    # =====================================================
    def generate_figures(self):
        ids = simpledialog.askstring(
            "Trajectory Figures",
            "Enter Paper Numbers separated by commas\n\nExample:\n2143,263,2894"
        )
        if not ids:
            return
        paper_numbers = [
            int(x.strip()) for x in ids.split(",") if x.strip()
        ]
        output_folder = (
            Path.home() / "Desktop" / "SleepingBeautyProject"
            / "SleepingBeautyAnalyzer" / "outputs" / "figures"
        )
        base_folder = (
            Path.home() / "Desktop" / "SleepingBeautyProject"
            / "SleepingBeautyAnalyzer" / "outputs"
        )
        required_files = [
            "DuWu_results.xlsx", "Ke_results.xlsx", "VanRaan_results.xlsx"
        ]
        missing = [
            f for f in required_files if not (base_folder / f).exists()
        ]
        if missing:
            messagebox.showerror(
                "Error", "Missing files:\n\n" + "\n".join(missing)
            )
            return

        vanraan_extended_path = base_folder / "VanRaanExtended_results.xlsx"
        count = generate_trajectory_figures(
            paper_numbers,
            base_folder / "DuWu_results.xlsx",
            base_folder / "Ke_results.xlsx",
            base_folder / "VanRaan_results.xlsx",
            output_folder,
            vanraan_extended_file=(
                vanraan_extended_path if vanraan_extended_path.exists() else None
            )
        )
        messagebox.showinfo(
            "Completed",
            f"{count} figure(s) generated.\n\nSaved to:\n{output_folder}"
        )
        self.status_label.config(
            text=f"Status: Generated {count} figure(s)", fg="green"
        )

    # =====================================================
    # Open Output Folder
    # =====================================================
    def open_output_folder(self):
        folder = (
            Path.home() / "Desktop" / "SleepingBeautyProject"
            / "SleepingBeautyAnalyzer" / "outputs"
        )
        folder.mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(folder)])
        else:
            subprocess.run(["xdg-open", str(folder)])


# =========================================================
# Launch
# =========================================================
root = tk.Tk()
app = SleepingBeautyAnalyzer(root)
root.mainloop()
