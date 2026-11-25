**Sleeping Beauty Analyzer**

**User Manual**

**Version: v1_stable**

**TL;DR**

This app flags candidate Sleeping Beauty papers using four methods.
Being \"flagged\" does not prove that a paper is genuinely notable.
Before you cite or report any result, check: (1) its absolute Bcp/B
score, not just its rank within your dataset, (2) its total citation
count, and (3) how many methods agree (Consistency_Count). Full guidance
in Section 5, but read the box below first.

**🚨 Before You Trust Any Flagged Paper: 3 Checks**

1.  Is the score high in absolute terms: not just relative to this
    dataset? If every paper in your dataset has a low or negative Bcp/B,
    the \"top 10%\" is still computed and returned, but it\'s the
    least-irrelevant of an irrelevant batch, not a real finding.

2.  Is Total Citations reasonable? A high score paired with only a
    handful of total citations is not a compelling Sleeping Beauty. Bcp
    and B are continuous, threshold-free scores, so they can be \"high\"
    even when a paper has barely been cited at all.

3.  Does Consistency_Count = 2 or 3? A paper flagged by only one method
    is weaker evidence than one multiple independent methods agree on.

If a paper fails all three checks, treat it as noise, not a discovery.
(See Section 5 for full detail on each.)

**1. Introduction**

The Sleeping Beauty Analyzer is a desktop application for identifying
and comparing \"Sleeping Beauty\" publications: papers that are uncited
for a period of time before suddenly attracting a surge of citations.
The app implements three independent, published detection methods, plus
one extended variant, and lets you visually compare their results on the
same citation trajectory.

Methods implemented:

  -------------------------------------------------------------------------
  **Method**   **What it measures**
  ------------ ------------------------------------------------------------
  Du & Wu      Continuous \"Bcp\" score based on deviation from a
  (2018)       straight-line citation accumulation curve, a modified method
               of Ke et al. (2015)

  Ke et al.    Continuous \"Beauty Coefficient\" (B) score, similarly based
  (2015)       on citation curve shape

  van Raan     Categorical Yes/No classification using fixed sleep-length
  (2004)       windows (s = 5--10 years)

  van Raan     A variant of van Raan (2004), extending sleep-length windows
  Extended     beyond the original 5--10 year range, to detect
               longer-dormancy Sleeping Beauties the original method cannot
               see by construction
  -------------------------------------------------------------------------

**⚠️** Bcp and B have no built-in threshold. Both scores are continuous.
There is no fixed cutoff above which a paper \"is\" a Sleeping Beauty.
This means a high-scoring paper can still have very low total citations.
Always check Total Citations alongside any score (see the 3-check box
above, and Section 5).



**2. Installation & Launching**

**macOS (one version for Intel and one version for Apple Silicon)**

1.  Locate SleepingBeautyAnalyzer.app (provided as a .zip --- unzip it
    first if needed).

2.  Double-click to launch

3.  If macOS blocks the app as being from an unidentified developer, the
    exact steps depend on your macOS version:

    - **Older macOS (Monterey and earlier):** Right-click the app →
      **Open** → click **Open** again in the confirmation popup.

    - **Newer macOS (Sequoia and later):** The right-click method may
      not show an \"Open\" option. Instead: go to **System Settings →
      Privacy & Security**, scroll to the **Security** section, and
      click **Open Anyway** next to the blocked-app message. Confirm
      when prompted.

4.  This is only required the first time you open the app.

**Windows**

1.  Locate SleepingBeautyAnalyzer.exe.

2.  Double-click to launch.

3.  If Windows shows \"Windows protected your PC\" (SmartScreen): click
    **More info** → **Run anyway**. Only required the first time.

**3. Main Window Overview**

The main window is divided into 3 button rows, a file list, a statistics
panel, and a status bar.



  -----------------------------------------------------------------------
  **Row**    **Buttons**
  ---------- ------------------------------------------------------------
  Row 1      Add WoS Citation Report Files · Add Scopus Citation Overview
             Files ·\
             Merge and Clean Dataset · Reset Loaded Files

  Row 2      Run Du & Wu (2018) · Run Ke et al. (2015) · Run van Raan
             (2004) ·\
             Compare All Methods

  Row 3      Generate Trajectory Figures · Run van Raan Extended · Open
             Output Folder
  -----------------------------------------------------------------------

All generated files are saved automatically to:\
\~/Desktop/SleepingBeautyProject/SleepingBeautyAnalyzer/outputs/

(\~ = your home folder, e.g. C:\\Users\\YourName\\ on Windows or
/Users/YourName/ on Mac)

**\**

**4. Step-by-Step Workflow (The Walk-through)**

**Step 1 --- Add Citation Files**

**From Web of Science:**

1.  Click **Add WoS Citation Report Files**.

2.  Select one or more .xlsx/.xls Citation Report exports.

3.  Selected files appear in the list box below.

**Alternatively, from Scopus:**

1.  Click **Add Scopus Citation Overview Files**.

2.  Select one or more .csv Citation Overview exports.

3.  If any paper\'s publication year falls before the start of your
    chosen Scopus date range, and its pre-range citation count can\'t be
    verified as zero, you\'ll be prompted to choose: keep only papers
    within the visible range, keep only papers with a verified-zero
    pre-range count, or skip the affected file(s). See Section 5 for why
    this matters.



**⚠️ Do not mix WoS and Scopus files in the same dataset.** The two
databases use different source coverage, indexing rules, and so on.
Their citation counts are not directly comparable. The app blocks this
automatically: if WoS files are already loaded, \"Add Scopus\" is
disabled, and vice versa. Click **Reset Loaded Files** to switch
sources.

**Tip:** You can select multiple files at once. They\'ll be merged
together in the next step.

**\**

**Step 2 --- Merge and Clean Dataset**

Click **Merge and Clean Dataset**. The app will combine all selected
files, remove duplicates (matched by DOI, or by Title + Publication
Year), and save the result as master_dataset.xlsx. A summary popup and
the stats panel report records imported, duplicates removed, and final
record count. The app\'s statistics panel also updates live.



**⚠️ This step must be completed before running any analysis method.**

**⚠️ Always re-run ALL analyses after any new Merge.** 1 Paper Numbers
are assigned alphabetically by title, independently, each time you run
any analysis method. As long as every analysis is run against the *same*
master_dataset.xlsx, Paper Numbers stay correctly aligned across all
result files. But if you click **Reset Loaded Files**, re-merge with a
different set of input files, and then *don\'t* re-run every analysis
again, old result files become stale: their Paper Numbers may no longer
match the new dataset. **Always re-run every analysis method after any
new Merge**, even if you only changed part of your input files.

**\**

**Step 3 --- Run Analysis Methods**

Each method button works the same way: click it, watch the status bar,
and a completion popup confirms the output file and paper count.


  ---------------------------------------------------------
  **Button**                 **Output file**
  -------------------------- ------------------------------
  Run Du & Wu (2018)         DuWu_results.xlsx

  Run Ke et al. (2015)       Ke_results.xlsx

  Run van Raan (2004)        VanRaan_results.xlsx

  Run van Raan Extended      VanRaanExtended_results.xlsx
  ---------------------------------------------------------

**Running van Raan Extended (Optional):** You\'ll be prompted for a
maximum sleep length (max_s, 10--60 years, default 30). The original
method always tests s = 5--10; Extended raises the upper bound so
longer-dormancy papers can be detected. Each result includes a flag for
whether the paper has enough citation history to be fairly evaluated at
your chosen max_s. A \"No\" on a recently published paper may just mean
\"too young to tell,\" which may become a Sleeping Beauty in the future.
This is a deliberate research variant, not the literal van Raan (2004)
definition: use the original button if you need results matching the
original method.

**\**

**Step 4 --- Compare All Methods**

Click **Compare All Methods**. Requires

- DuWu_results.xlsx,

- Ke_results.xlsx, and

- VanRaan_results.xlsx

to already exist. You\'ll be prompted for a threshold percentage (e.g.,
10 = top 10% by Bcp and by B). VanRaanExtended_results.xlsx is included
automatically if present. The completion popup confirms either way.

**🚨 Reminder:** the top N% you choose is always relative to *your own
dataset*. Check Section 5 before treating any flagged paper as a
confirmed finding.

**Output:** Comparison_results.xlsx --- a Comparison sheet with every
method\'s scores plus Consistency_Count (0--3), and a Notes sheet with
interpretation guidance.

**\**

**Step 5 --- Generate Trajectory Figures**

Click **Generate Trajectory Figures**, enter one or more Paper Numbers
(comma-separated). Requires the same three result files as Step 4;
Extended is included automatically if present. One .png per paper is
saved to outputs/figures/.

**Reading a figure:**

- **Legend labels** list every method involved in an agreement line
  (e.g., \"Du & Wu (2018) & Ke et al. (2015) agree\"); 3+ method
  combinations wrap onto two lines.

- **Colors** are fixed per unique method-combination, consistent across
  every figure.

- **Total Citations** is shown in the title alongside each score. See
  the 3-check box at the top of this manual for why this number matters
  as much as the scores themselves.

- **X-axis starts at 1**. In other words, the first data point that
  plots the annual citation collected within the year of publication is
  denoted as Year 1 (consistent with Citation History in the Excel
  outputs).



**\**

**5. Interpreting Results Across Methods**

**van Raan (2004): limited sleep-length window.** Only tests s = 5--10
years. A \"No\" means \"no qualifying awakening found in a 5--10 year
window\". Does not mean that the paper never had delayed recognition.

**van Raan Extended: a deliberate variant, not the original method.**
Widens the search range to detect longer dormancy. A match of s=10 under
*both* the original and Extended methods is usually the same underlying
match found twice (Extended\'s range fully contains the original\'s).
The two only diverge when the true match lies beyond s=10.

**Self-Citations are not excluded.** Both van Raan methods, as
originally defined, exclude self-citations from sleep depth (c_s) and
awakening intensity (c_a). WoS Citation Reports only provide total
citations, with no self-citation breakdown. So this tool computes both
from totals, a documented deviation that may run slightly higher than
the literature-faithful calculation. (Note: Scopus export allows
exclusion of self-citations.)

**Consistency_Count reflects method *families*, not raw method count.**
The three families are Du & Wu, Ke et al., and van Raan (original or
extended, combined). So, van Raan\'s two variants agree only with each
other and never inflate the count past what a genuine cross-method
agreement would show.

**\"Overall Rank\" tiebreaking is not finely meaningful.** Papers are
primarily ranked by Consistency_Count. Within a tied group, ties are
broken using Du & Wu\'s rank alone. Ke et al.\'s B score is not used as
a secondary tiebreaker. Treat fine-grained ordering *within* a tied
Consistency_Count group as a largely arbitrary sort artifact, not a
precise measure of which paper is \"more\" Sleeping-Beauty-like. For
that, compare the individual Bcp and B scores directly.

**Scopus imports may exclude some papers**. Scopus Citation Overview
export has a maximum 25-year date range. Citations before that range are
lumped into one \<N total, not broken out by year. If that pre-range
total can\'t be verified as zero, the paper\'s full citation history
can\'t be reliably reconstructed. The app then prompts you to decide how
to handle such papers at import time (keep only papers within the
visible range, keep only papers with a verified-zero pre-range count, or
skip the affected file). This safeguard does not apply to WoS imports,
since WoS Citation Reports export individual year columns going back to
each paper\'s publication year with no equivalent aggregation.

**\**

**6. Output File Reference**

  -------------------------------------------------------------------------------------
  **File**                               **Produced By**      **Key Sheets**
  -------------------------------------- -------------------- -------------------------
  master_dataset.xlsx                    Merge and Clean      MasterData, ImportLog
                                         Dataset              

  DuWu_results.xlsx                      Run Du & Wu (2018)   Bcp_Summary,
                                                              Citation_History

  Ke_results.xlsx                        Run Ke et al. (2015) Ke_Summary,
                                                              Citation_History

  VanRaan_results.xlsx                   Run van Raan (2004)  VanRaan_Summary,
                                                              VanRaan_AllMatches,
                                                              Citation_History, Notes

  VanRaanExtended_results.xlsx           Run van Raan         VanRaanExt_Summary,
                                         Extended             VanRaanExt_AllMatches,
                                                              Citation_History, Notes

  Comparison_results.xlsx                Compare All Methods  Comparison, Notes

  figures/P\<N\>\_MethodComparison.png   Generate Trajectory  ---
                                         Figures              
  -------------------------------------------------------------------------------------

All files are saved to:\
\~/Desktop/SleepingBeautyProject/SleepingBeautyAnalyzer/outputs/

Click **Open Output Folder** at any time to jump directly to this
location in your file browser.

**\**

**7. Troubleshooting**

  ---------------------------------------------------------------------------
  **Problem**             **Likely Cause**      **Solution**
  ----------------------- --------------------- -----------------------------
  \"master_dataset.xlsx   Merge step not yet    Run **Merge and Clean
  not found\" error       run                   Dataset** first

  \"The following result  One or more of the    Run Du & Wu, Ke et al., and
  files are missing\"     three core methods    van Raan (2004) first ---
  when comparing          hasn\'t been run yet  Extended is optional

  A paper\'s \"No\"       Paper\'s true         Check the trajectory figure
  classification under    dormancy exceeds the  and Du&Wu/Ke results;
  van Raan surprises you  tested sleep-length   consider running van Raan
                          range                 Extended with a higher max_s

  A flagged paper seems   Score may be \"high\" See the 3-Check box at the
  like a                  only relative to a    top of this manual and
  weak/questionable       weak dataset, or      Section 5
  finding                 total citations may   
                          be very low           

  App won\'t open on      Standard Gatekeeper   **Older macOS (Monterey and
  macOS (\"unidentified   warning for unsigned  earlier):** Right-click →
  developer\")            apps                  Open → Open again (one-time).
                                                **Newer macOS (Sequoia and
                                                later):** Go to System
                                                Settings → Privacy & Security
                                                → click \"Open Anyway\" next
                                                to the blocked-app message,
                                                then confirm when prompted
                                                (one-time)

  App won\'t open on      Standard SmartScreen  Click \"More info\" → \"Run
  Windows (\"Windows      warning for unsigned  anyway\" (one-time)
  protected your PC\")    apps                  

  Mixing WoS and Scopus   Intentional safeguard Click Reset Loaded Files to
  files is blocked        --- the two           switch sources entirely
                          databases\' citation  
                          counts aren\'t        
                          comparable            
  ---------------------------------------------------------------------------

**\**

**8. Version Information**

**This manual describes:** Sleeping Beauty Analyzer v1_stable

**Methods included:**

- Du & Wu (2018) --- Bcp score

- Ke et al. (2015) --- Beauty Coefficient (B)

- van Raan (2004) --- original published definition, s = 5--10 years

- van Raan Extended --- user-configurable variant, s = 5 to your chosen
  maximum (10--60 years)

**References:**

Du, J., & Wu, Y. (2018). A parameter-free index for identifying
under-cited sleeping beauties in science. *Scientometrics*, *116*(2),
959-971.

Ke, Q., Ferrara, E., Radicchi, F., & Flammini, A. (2015). Defining and
identifying sleeping beauties in science. *Proceedings of the National
Academy of Sciences of the United States of America*, *112*(24),
7426-7431.

Van Raan, A. F. (2004). Sleeping beauties in science. *Scientometrics*,
*59*(3), 467-472.
