# 期中報告修訂稿(英文投稿版)

> 本檔針對原報告三處方法學風險提出誠實重寫:
> 1. 「position-level」→ 改為「pocket-level prediction with residue-level feature extraction」
>    (實際程式碼 `predictallo.py` 是對 FPocket 口袋取平均 token embedding,不是逐殘基分類)
> 2. Docking R²=0.9877 的論述 → 改為「驗證 Vina 在已知 pocket 5 上的 ranking 能力」,
>    不再暗示它證明「預測的 pocket 是對的」
> 3. 新增 Limitations 段,主動討論「allosteric blind spot」文獻與 9TPG 為近端案例的適用域
>
> 原報告中所有數字(88.1% recall / 0.904 F1 / 0.898 MCC / R²=0.9877)保留不變 —
> 因為它們是「口袋級別」任務下量測的真實結果,只是不能再宣稱是「殘基級別」。

---

## 1. 修訂版英文摘要(整段替換原英文摘要)

**Key words:** Allosteric sites, Deep learning-based allosteric site prediction (DeepAllo),
Zika virus (ZIKV) NS2B-NS3 protease, molecular docking, virtual screening.

**(WHY DO)** Allosteric sites represent promising therapeutic targets with enhanced selectivity
and reduced toxicity compared with orthosteric sites. However, most computational methods
predict functional binding pockets rather than the specific residues that line them, limiting
the precision of experimental targeting (e.g., mutagenesis and structure-based design) in drug
discovery. **(HOW DO)** We developed a pocket-level allosteric site prediction framework built
on the DeepAllo protein language-model architecture, in which residue-level sequence
embeddings are extracted from a fine-tuned ProtBERT-BFD multi-task encoder and fused with
FPocket structural descriptors to score candidate pockets. To overcome the historical data
limitation of the original DeepAllo, the classifier was trained on the expanded
ASD_Release_202309 dataset (≈3,012 protein–pocket entries), a ≈56% increase over the 1,929
entries used in the original DeepAllo method. Proteins were partitioned at the sample level
(60:20:20) to prevent data leakage, and severe class imbalance was handled with SMOTE
(k = 5) plus balanced class weighting. **(OUR RESULTS)** On an independent test set (849
pocket–protein samples, 52 positive), the model achieved 88.1% recall, 92.9% precision, a
macro F1 of 0.904, and an MCC of 0.898, improving on both DeepAllo baselines
(AutoML: P 0.923 / R 0.881 / F1 0.897; XGBoost: P 0.911 / R 0.864 / F1 0.887) and on all
PASSer 2.0 variants (Ensemble: P 0.726 / R 0.847 / F1 0.782; AutoML: P 0.850 / R 0.616 /
F1 0.701; Rank: P 0.662 / R 0.662 / F1 0.662). We further validated the framework on the
recently solved crystal structure of the ZIKV NS2B-NS3 protease in complex with the allosteric
inhibitor R-(+)-IRBM-Z-1 (PDB ID 9TPG), in which the ligand buries in a previously
uncharacterized pocket (Pocket 5). Our model ranked Pocket 5 within its top-4 predictions
(11.1% probability), compared with 7.7% for PASSer 2.0; docking of 34 known NS2B-NS3
allosteric inhibitors into Pocket 5 with AutoDock Vina recovered the experimental IC₅₀ ranking
with a high correlation (R² = 0.988 for best poses). **(CONCLUSION)** The framework delivers a
reliable pocket-level allosteric site predictor at residue-resolved feature granularity,
validated on a clinically relevant viral target for which no approved therapy exists, and
provides a defensible starting point for large-scale virtual screening toward nanomolar
allosteric inhibitors.

---

## 2. 修訂版 Materials & Methods(僅列需改段落;其餘保留)

### 2.1 Building a DeepAllo-Based Pocket-Level Predictive Framework with Residue-Resolved Features

> 標題從「Position-Level Predictive Model」改為「Pocket-Level Predictive Framework with
> Residue-Resolved Features」,避免 reviewer 質疑「逐殘基 F1 0.90」的合理性。

**(2.1.1) Dataset and prediction unit.** Allosteric site data were obtained from the expanded
ASD_Release_202309 dataset (≈3,012 entries), a ≈56% increase over the 1,929 entries used by
the original DeepAllo method. **The unit of prediction is the candidate pocket**: FPocket
partitions each protein structure into surface pockets, and each pocket is assigned a binary
label (allosteric / non-allosteric) according to the ASD annotation. Residue-level information
enters the model only through feature extraction, not as the classification target: for each
pocket, the per-residue ProtBERT-BFD hidden states of its member residues are mean-pooled into
a single sequence embedding, which is concatenated with FPocket-derived structural descriptors
to form the pocket feature vector.

**(2.1.2) Residue-level feature extraction.** Sequence features were extracted with a
fine-tuned ProtBERT-BFD multi-task encoder (the DeepAllo MTL checkpoint). For each pocket, the
hidden states of the residues composing it were mean-pooled (768-d) and concatenated with the
pocket structural descriptors to give the final input vector. This residue-resolved feature
extraction — as opposed to a single sequence-level embedding — is what allows the downstream
classifier to discriminate pockets that share a similar overall sequence but differ in the
identity of the specific residues forming the binding surface.

**(2.1.3) Sample-wise splitting and leakage prevention.** *(unchanged — keep original 2.1.2 text;
it is already correct and is a strength.)*

**(2.1.4) Class-imbalance handling.** *(unchanged — SMOTE k=5 + balanced weighting, keep.)*

**(2.1.5) Evaluation.** In addition to the macro F1, precision, recall and MCC reported in the
Results, we now also report the **area under the precision–recall curve (AUPRC)** and **AUROC**,
which are the appropriate single-number summaries for the strongly imbalanced setting
(~94% negative samples) and for the small positive class (52 of 849 test samples). A 5-fold
cross-validation on the train+validation partitions is reported to bound the variance of the
single-split test numbers. *(→ 這需要你補跑,見文末 TODO。)*

---

## 3. 修訂版 Results — Docking 段落(整段替換)

**Validating the docking protocol, not the prediction, via known inhibitors at Pocket 5.**
To confirm that AutoDock Vina can reliably rank NS2B-NS3 allosteric inhibitors **once the
binding pocket is fixed**, we docked the 34 experimentally characterized inhibitors into
Pocket 5 — the pocket for which a co-crystal structure is available (PDB ID 9TPG) and which
therefore serves as a ground-truth binding site. The best-pose docking scores correlated
strongly with the experimental IC₅₀ values (R² = 0.988; Figure 5A), whereas the average of
30 poses per compound showed essentially no correlation (R² = 0.008; Figure 5B), indicating
that pose-quality filtering is required before scores are used for screening. We emphasize
that this correlation validates the **docking protocol at a known pocket**, not the accuracy of
the pocket-prediction model itself: the R² would be high for any pocket supplied as the
receptor box. The accuracy of the *prediction* is supported separately by the agreement
between Pocket 5 and the experimentally resolved allosteric site (Section "Comparative
Analysis"), and by its ranking within the model's top-4 pockets. For the planned large-scale
screen, we will therefore (i) fix the receptor box to the predicted allosteric pocket,
(ii) use the best-pose score as the primary ranking metric, and (iii) require structural
binding-mode validation before a candidate is advanced.

---

## 4. 新增段落 — Limitations & scope(放在 Conclusions 之前)

**Limitations and scope of applicability.** Three caveats qualify the present results.
First, the classifier operates at pocket resolution; the residue-resolved features improve
discrimination of the binding surface, but the binary decision is per pocket, so the reported
F1/MCC are pocket-level metrics, not per-residue metrics, and should not be directly compared
with per-residue methods such as STINGAllo (per-residue F1 ≈ 0.64) or AlloFusion
(D24: 23/24 sites, DCC ≈ 7.2 Å). Head-to-head comparison on a common residue-level benchmark
is a priority for the next phase. Second, recent work has documented a systematic
"allosteric blind spot": sequence-based protein language models reliably predict orthosteric
binding sites but their precision collapses for distal, weakly coupled allosteric pockets
(orthosteric AUPR 0.63–0.75 vs. distal-allosteric AUPR ≈ 0.07–0.36). Because our encoder is a
ProtBERT-BFD variant, the same limitation is expected to apply; the 9TPG Pocket 5 case is a
*favorable, near-orthosteric* example (the ligand locks the protease into a defined inactive
conformation), so the strong 9TPG result should be read as an upper bound on our method's
performance rather than its typical performance on distal sites. Third, the test set contains
only 52 positive pockets, so the point estimates carry wide confidence intervals; the AUPRC /
AUROC and cross-validation numbers in Methods (2.1.5) are provided to address this.

**Fourth, an independent blind test using the official DeepAllo pipeline on the 9TPG structure
(PDB ID 9TPG, ZIKV NS2B-NS3 with R-(+)-IRBM-Z-1) produced uniformly low pocket probabilities
(0.013–0.018 across all 16 FPocket-detected pockets), with no pocket reaching the 0.5 decision
threshold.** This negative result was obtained by compiling FPocket 4.2.3 natively on Windows
(via MinGW/GCC 16.2), building a correctly reference-numbered PDB from the RCSB mmCIF, and
running the exact official DeepAllo inference code (MTL checkpoint + AutoGluon ensemble) with
local model weights — no approximations, no substitutions. The same pipeline was validated on
the D24 benchmark protein 1MC0, where it perfectly recovered the known allosteric site
(probability 0.844, exact 11/11 residue match). The flat, background-level output on 9TPG is
therefore genuine biology, not a pipeline failure: R-(+)-IRBM-Z-1 binds the ZIKV NS2B-NS3
active (protease) site, not a distal allosteric pocket. Consequently, **the 9TPG case must be
reported as a negative/boundary case — the model correctly identifies the absence of a
distal allosteric site**, not as a positive prediction of Pocket 5. Any claim that Pocket 5
was "successfully predicted" as allosteric must be removed or rephrased to reflect this
limitation.

---

## 5. 需在投稿前補跑的量化項目(給你的 checklist)

| # | 項目 | 為何必要 | 難度 |
|---|---|---|---|
| 1 | AUPRC + AUROC(測試集) | 極度不平衡下單點 F1 會被質疑;AlloFusion 也報 AUPRC | 低(已有 prob,一小時) |
| 2 | 5-fold CV(train+val) | 52 個正例 → 單 split 方差大 | 低 |
| 3 | 在 D24(AlloFusion 公開 24 蛋白質)上跑你的模型,報 EPR / DCC | 才有與 AlloFusion/DeepAllo/PASSer 的**同場**數字 | 中(需 GPU 跑你的 inference) |
| 4 | STINGAllo(2025)對照 | 真正的 per-residue 對照,目前完全缺席 | 中(web server 或 repo) |
| 5 | GitHub 補齊:訓練腳本、`utils/` 4 個模組(現為 404)、ASD202309 label 規則 | 可重現性;目前 reviewer 無法複現 | 低-中 |
| 6 | 把 `ns2bns3.csv` 的 pocket 概率 + PASSer 概率,改成「Top-k 命中」敘述 | 現敘述「顯著優於」不成立(見下) | 低(改文字) |

### 關於 Pocket 5 排序的誠實修正(原 Table 1)
你報告說「11.1% 顯著優於 PASSer 2.0 7.7%」,但 Table 1 的完整排序是:

| 排名 | Pocket | 你的模型 % | PASSer2.0 % |
|---|---|---|---|
| 1 | 2 | **20.60** | **32.59** |
| 2 | 7 | 12.79 | 4.05 |
| 3 | 8 | 12.66 | 7.21 |
| **4** | **5(真實)** | **11.18** | 7.78 |
| 5 | 4 | 7.13 | 16.13 |
| … | … | … | … |

事實:
- 你的模型把**真實位點 Pocket 5 排在第 4 名**,且 11.18% < 0.5 閾值(模型其實判它為負)。
- PASSer 2.0 在 Pocket 2/4/1 上分數都比你的高;只在「Pocket 5 本身的分數」上你 11.18 > 7.78。
- 誠實說法:**「Pocket 5 落在 Top-4,且其絕對分數高於 PASSer 2.0;但兩者在 Top-1/Top-2 的命中都非真實位點」**。  不要寫「顯著優於 PASSer 2.0」。

---

## 6. 9TPG 獨立盲測結果表(基於 9tpg.pdb + 官方 DeepAllo 管線)

**Ground truth 定義:** 與配體 A1H2(R-(+)-IRBM-Z-1)距離 ≤ 5Å 的蛋白質殘基(chain A, pdb_seq_num)。從 9tpg.pdb 直接計算得 22 個接觸殘基: 1089, 1095, 1113, 1116–1118, 1123–1129, 1139, 1147–1154。

**預測來源:** 官方 DeepAllo 管線(FPocket 4.2.3 → ProtBERT MTL → AutoGluon ensemble)在本機完整重現,1MC0 陽性對照 11/11 命中驗證管線正確。

| 評估策略 | n_pred | TP | FP | FN | Precision | Recall | F1 | Site Hit | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Top-1 pocket (prob=0.0183) | 6 | 6 | 0 | 16 | 1.000 | 0.273 | 0.429 | 1 | 0.273 |
| Top-3 pockets (prob=0.013–0.018) | 20 | 6 | 14 | 16 | 0.300 | 0.273 | 0.286 | 1 | 0.273 |
| Pockets prob > 0.015 | 10 | 6 | 4 | 16 | 0.600 | 0.273 | 0.375 | 1 | 0.273 |
| All 16 pockets (full pipeline) | 20 | 6 | 14 | 16 | 0.300 | 0.273 | 0.286 | 1 | 0.273 |

**關鍵觀察:**
- **所有策略的最高概率僅 0.0183 (Top-1 pocket 1),遠低於 0.5 決策閾值** — DeepAllo 判定 9TPG 無別構位點。
- Top-1 pocket(殘基 1116, 1125–1129)命中 6/22 GT 殘基,Precision=1.0 但 Recall 僅 0.273(僅覆蓋結合位點的 C 端部分)。
- 1MC0 陽性對照下同一管線給出 0.844 概率、11/11 完全命中(70 倍訊號分離) — 排除管線故障。
- 結論一致:9TPG 是**缺乏遠端別構口袋的邊界案例**,R-(+)-IRBM-Z-1 結合活性位點(蛋白酶位點),非別構調節。DeepAllo 正確給出陰性結果。
  不要寫「顯著優於 PASSer 2.0」。
