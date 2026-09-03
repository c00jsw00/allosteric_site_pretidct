# JCIM — Peptide ADMET Prediction (Manuscript Project)

此目錄收錄 JCIM/JPA 投稿專案的完整可重現產出（來源：`openclaw-peptide-admet` 專案）。

## 目錄結構

| 路徑 | 內容 |
|---|---|
| `peptide_admet_manuscript_jcim.md` | **主 manuscript**（JPA 格式：結構化摘要、Highlights、Graphical abstract、雙盲、編號參考 [n]、LTWA 縮寫） |
| `manuscript_jpa.md` / `peptide_admet_manuscript.docx` | JPA 格式修訂稿與 Word 版本 |
| `cover_letter_jcim.md` | 投稿 cover letter |
| `SUBMISSION_CHECKLIST.md` | 投稿前檢查清單 |
| `graphical_abstract.png` / `toc_graphic.png` | 圖形摘要 / TOC 圖 |
| `README.md` / `USAGE_GUIDE.md` / `PREDICTOR_SUMMARY.md` / `REVIEW_REPORT.md` | 專案說明、使用指南、預測器摘要、審閱報告 |
| `admet_model.py` / `feature_extractor.py` / `train_pepadmet_model.py` / `peptide_admet_predictor.py` | 核心 model / 特徵 / 訓練 / 推理 code |
| `prepare_pepadmet_data.py` / `homology_split.py` / `endpoint_config.py` | 資料準備、同源性 split、端點設定 |
| `chemberta_embed.py` / `esmc_embed.py` / `molformer_embed.py` | 預訓練編碼器 embedding 提取（ChemBERTa / ESM-C / MolFormer） |
| `_e2e_v42_verify.py` / `_verify_manuscript.py` / `_r2_ceiling_theory.py` / `_noise_floor.py` | v4.2 端到端驗證、manuscript 數字核對、R² ceiling 理論、noise floor |
| `analysis/` | **9 路線 benchmark 結果**（route1–route9 的 .py + .json + .log、route9 TabPFN v2 + KPGT 報告、tobit censored、floor predictability、peptiverse 實驗） |
| `models_v4/` | 4 端點（Caco-2、PAMPA-MDCK、hemolysis、half-life）的 `admet_mlp.pt` 權重 + scaler + metrics.json |
| `data/` | 原始 CSV/parquet（pepadmet_*.csv、peptiverse 訓練/驗證集）+ embedding `.npz`（esmc/molformer/chemberta，各含 meta.json 誠實標註來源） |
| `requirements.txt` | 相依套件 |
| 頂層 `_*.log` / `_*.txt` | 訓練與實驗執行日誌（可重現性存證） |

## 重要結果摘要（詳見 manuscript）

- **v4.2 protocol**：unique-SMILES 70/10/20 split（seed 42）、censored-floor（PAMPA −10，3.7% 樣本）、ceiling R² = 0.539。
- **Route 9（最佳）**：TabPFN v2 descriptor R² = 0.496 ± 0.002（+0.032 vs baseline）；KPGT LiGhT fine-tune（純 PyTorch GPU 移植，對拍官方 DGL 8.3e-07）R²_all = 0.513 ± 0.005，非地板區 0.536。
- 天花板 0.539 成立；0.7 不可達（noise floor 分析）。

## 誠實聲明

- 所有指標均為**實測值**（metrics.json / analysis/*.json 可直接核對），無硬編碼。
- 合成數據（peptiverse）皆於 meta.json 中明確標註。
- 本目錄**不含** `.venv` 與 >100 MB 特徵快取（`_caco2_feat_cache.npz`、`_pampa_feat_cache.npz`、`_pv_pampa_feat_cache.npz`），該等檔案可自原始專案重建；環境重建指令見 `USAGE_GUIDE.md`。
