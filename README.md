# Sleeping Beauty Analyzer

A desktop application for identifying and comparing "Sleeping Beauty" 
publications — papers that receive little to no attention for a period 
of time before suddenly attracting a surge of citations.

The tool implements three independent, published Sleeping Beauty 
detection methods, plus one extended variant, and lets users visually 
compare results across methods on the same citation trajectory.

## Methods Implemented

| Method | What it measures |
|---|---|
| Du & Wu (2018) | Continuous "Bcp" score based on deviation from a straight-line citation accumulation curve, a modified method of Ke et al. (2015) |
| Ke et al. (2015) | Continuous "Beauty Coefficient" (B) score, based on citation curve shape |
| van Raan (2004) | Categorical Yes/No classification using fixed sleep-length windows (s = 5–10 years) |
| van Raan Extended | A variant of van Raan (2004) extending the sleep-length window beyond 5–10 years, to detect longer-dormancy Sleeping Beauties the original method cannot see by construction |

## ⚠️ Before Trusting Any Flagged Result

Being "flagged" as a Sleeping Beauty is not automatic proof of a genuine 
finding. Before citing or reporting any result, check:
1. Is the score high in **absolute** terms, not just relative rank within your dataset?
2. Is **Total Citations** reasonable — not just a high score on a barely-cited paper?
3. Does **Consistency_Count** = 2 or 3 (multiple methods agreeing)?

Full guidance in the [User Manual](./User_Manual.md), Section 5.

## Download

Pre-built, ready-to-run applications are available on the 
[Releases](../../releases) page for:
- macOS (Apple Silicon)
- macOS (Intel)
- Windows (x86-64)

No Python installation is required to use these pre-built versions.

## Quick Start

1. Download the appropriate build for your OS from Releases.
2. Launch the app (see Installation Notes below for first-launch security prompts).
3. Add citation data: either Web of Science Citation Report exports 
   (`.xlsx`) or Scopus Citation Overview exports (`.csv`). **Do not mix 
   both sources in the same dataset** — see the manual for why.
4. Click **Merge and Clean Dataset**.
5. Run any combination of the four analysis methods.
6. Optionally, run **Compare All Methods** to cross-check results, and 
   **Generate Trajectory Figures** to visualize individual papers.

## Installation Notes

**macOS:** If blocked as "from an unidentified developer":
- Older macOS (Monterey and earlier): right-click the app → Open → Open again.
- Newer macOS (Sequoia and later): System Settings → Privacy & Security → "Open Anyway."

One-time step either way.

**Windows:** If blocked by SmartScreen, click "More info" → "Run anyway." One-time step.

## Full Documentation

See [`User_Manual.md`](./User_Manual.md) for the complete user manual, 
including the full step-by-step workflow, interpretation caveats 
(self-citation handling, sleep-length window limitations, 
Consistency_Count semantics), troubleshooting, and output file reference.

## Output Files

| File | Produced By |
|---|---|
| `master_dataset.xlsx` | Merge and Clean Dataset |
| `DuWu_results.xlsx` | Run Du & Wu (2018) |
| `Ke_results.xlsx` | Run Ke et al. (2015) |
| `VanRaan_results.xlsx` | Run van Raan (2004) |
| `VanRaanExtended_results.xlsx` | Run van Raan Extended |
| `Comparison_results.xlsx` | Compare All Methods |
| `figures/P<N>_MethodComparison.png` | Generate Trajectory Figures |

## Citing This Software

If you use this tool in your research, please cite:

> *(Citation to be added once the accompanying SoftwareX article is 
> published.)*

## References

- Du, J., & Wu, Y. (2018). A parameter-free index for identifying 
  under-cited sleeping beauties in science. *Scientometrics*, 116(2), 
  959–971.
- Ke, Q., Ferrara, E., Radicchi, F., & Flammini, A. (2015). Defining 
  and identifying sleeping beauties in science. *PNAS*, 112(24), 
  7426–7431.
- Van Raan, A. F. (2004). Sleeping beauties in science. *Scientometrics*, 
  59(3), 467–472.

## License

This project is licensed under the MIT License — see `LICENSE.txt` for details.

## Support

Questions or issues: *(your support email)*, or open an issue on this repository.
