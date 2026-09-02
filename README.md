# Allosteric Site Prediction Repository

## Completed Work (2026)

### 9TPG Official DeepAllo Blind Test
- **Status**: ✅ Completed
- **Method**: FPocket 4.2.3 (native Windows MinGW/GCC 16.2) → PDB reconstruction from RCSB mmCIF → Official DeepAllo inference pipeline (MTL checkpoint + AutoGluon ensemble)
- **Results**: All 16 FPocket pockets probability 0.0128–0.0183 (background level), no allosteric site predicted
- **Key validation**: 1MC0 positive control — pipeline perfectly recovered known allosteric site (11/11 residues, probability 0.844, 70× signal/background separation)
- **Conclusion**: 9TPG result is genuine biology — R-(+)-IRBM-Z-1 binds the ZIKV NS2B-NS3 active (protease) site, not a distal allosteric pocket. The model correctly identifies absence of a distal allosteric site.

### Manuscript Revision (JPA Journal)
- **Status**: ✅ Completed
- **Changes**: 
  - Position-level → pocket-level prediction with residue-level feature extraction
  - Docking discussion reframed as protocol validation at known Pocket 5
  - **New Limitations section**: Three caveats including 9TPG as boundary case of absent distal allosteric pocket
  - Full statistical transparency (AUPRC/AUROC, 5-fold CV)

### D24 Benchmark Results
- **DeepAllo**: 22/24 DCC ✓, AlloFusion 22/24, PASSer 18/24, allositePro 12/22
- **STINGAllo**: hit=5/23, F1=0.090

### FPocket Windows Compilation
- **Method**: MinGW GCC 16.2.0 (MSYS2) native `fpocket.exe`
- **Fixes**: MSVC safety cookie stub, mmcif plugin symbol stub, `mkdir()` POSIX→Windows port, 80-char standard PDB lines, END position after all ATOM records

### Repository Structure
- `allo_bench/`: All pipeline scripts, models, data, and logs
- `openclaw-peptide-admet/`: Peptide ADMET foundation model benchmark (separate project)
- `openclaw-peptide-admet/master`: Manuscript `peptide_admet_manuscript_jcim.md` with Route 9 (TabPFN v2 + KPGT) complete

## Key Files
- `修訂稿_Abstract_Methods.md`: Revised Abstract + Methods with Limitations
- `9TPG_官方DeepAllo盲測_最終結果.md`: Complete 9TPG blind test results + technical appendices
- `run_9TPG_local.py`: Fully local DeepAllo inference (mirrors `inference.py`)
- `control_1MC0.py`: 1MC0 positive control validation script

## Workflow
1. FPocket pocket detection → PDB reconstruction → ProtBERT feature extraction → AutoGluon ensemble → Pocket probability ranking
2. All steps validated on 1MC0 (11/11 Top-1 hit) before blind application to 9TPG
3. 9TPG negative result honestly reported as boundary case — not a pipeline failure

---
Report generated from `c00jsw00/openclaw-peptide-admet` project. For details see the `allo_bench` directory.