# 官方 DeepAllo 對 9TPG 的本地盲測 — 最終結果

**日期:** 2026-09-02
**目標:** 在本機(GPU 機器)從源碼編譯 FPocket + 用官方 DeepAllo 權重,
對 2026 新結構 9TPG(ZIKV NS2B-NS3 + R-(+)-IRBM-Z-1)做**真正的**
第三方盲測,為報告的 Pocket-5 提供獨立背書(或反證)。

## 結論(誠實版)

**官方 DeepAllo 對 9TPG 的所有 16 個 FPocket 口袋都給出極低分
(0.0128–0.0183,與背景噪声同級),沒有任何口袋被標記為別構位點。**

這**不是**管線錯誤 — 已用 1MC0 陽性對照驗證。這是**真實生物學**:
R-(+)-IRBM-Z-1 結合在 ZIKV NS2B-NS3 的**活性位點(蛋白酶切割位點)**,
9TPG 這個結晶複合體中**沒有已知的別構位點**,DeepAllo 正確地找不到。

## 管線驗證(1MC0 陽性對照)— 決定性

D24 benchmark 中 1MC0 有**已知的別構位點殘基**(ground truth):
`426, 452, 456, 457, 458, 459, 480, 481, 484, 495, 512`(11 個)。

用**完全相同**的管線(同一腳本、同一模型、同一 AutoGluon ensemble)跑 1MC0:

| 排名 | 口袋 | 概率 | 命中 ground-truth 殘基 |
|---|---|---|---|
| **Top-1** | pocket1 | **0.8436** | **11/11 全中** = 恰好就是那 11 個別構殘基 |
| Top-2 | pocket2 | 0.8401 | 6/11 |
| Top-3 | pocket3 | 0.8393 | 3/11 |
| 其餘 26 個 | — | ~0.0124 | 0 |

- Top-1 口袋 = **11/11 完全匹配** ground-truth 別構位點。
- 別構口袋概率 0.84 vs 背景 0.012 — **70 倍的訊號分離**。

→ 管線 100% 正確:序列對齊、FPocket 口袋偵測、ProtBERT forward、
pocket-token 平均、AutoGluon 打分、排序全部驗證通過。

## 9TPG 實際結果(可重現,兩次運行 bit-identical)

| 排名 | FPocket 口袋 | 概率 | 殘基(pdb_seq_num) |
|---|---|---|---|
| 1 | pocket1 | 0.0183 | 1116, 1125, 1126, 1127, 1128, 1129 |
| 2 | pocket2 | 0.0167 | 1157, 1159, 1160, 1161 |
| 3 | pocket3 | 0.0149 | 56,57,58,60,62, 1098,1105,1106,1107,1108 |
| 4–16 | — | 0.0128–0.0143 | (其餘 13 個,全在背景範圍) |

**16 個口袋全在 0.013–0.018,無一分數明顯脫離背景。**
對比 1MC0 陽性(0.84 vs 0.012),9TPG 的「最高分」0.018 只比背景
0.012 高 1.5 倍 — 統計上等同噪声。

## 對報告 Pocket-5 的意涵(誠實)

報告宣稱的 Pocket-5(殘基 173–186,report 中的別構位點候選)**在
官方 DeepAllo 盲測中未被獨立識別** — DeepAllo 對 9TPG 根本沒有
給出任何高置信的別構預測。

**誠實寫法(建議放進修訂稿 Limitations):**
> 我們用官方 DeepAllo(MoaazK/deepallo, FPocket + ProtBERT +
> AutoGluon)對 2026 結構 9TPG(ZIKV NS2B-NS3 + R-(+)-IRBM-Z-1)
> 做了第三方盲測。模型對全部 16 個 FPocket 口袋都給出低別構概率
> (0.013–0.018,與背景同級),未識別出任何高置信別構位點。作為
> 陽性對照,同一管線在 D24 benchmark 的 1MC0 上把已知別構位點
> (11 個殘基)以 0.84 的概率排為 Top-1,11/11 完全命中。9TPG 的
> 結果符合其已知藥理學:R-(+)-IRBM-Z-1 是活性位點(蛋白酶)抑制劑,
> 該複合體中沒有已知別構位點。因此,報告中將 9TPG 視為別構預測
> 成功的案例是**不成立的**;我們應把它重新定位為「模型在缺乏別構
> 位點的結構上正確地不給出別構預測」的陰性/邊界案例,或從別構
> 命中聲明中移除。

## 技術附錄:本機如何做到

1. **FPocket 從源碼編譯成原生 Windows 執行檔**(本機 MSYS2/MinGW GCC 16.2):
   - 修 makefile:`ARCH=LINUXAMD64→WIN64`、`libmolfile_plugin.a→.lib`、
     去 `-pg`。
   - 補 MSVC 安全 cookie stub(`__security_cookie` 等 3 個符號)讓
     MinGW 能 link 官方預編譯的 `libmolfile_plugin.lib`。
   - 補 mmcif 插件符號 stub(`molfile_pdbxplugin_init/register`)。
   - 修 POSIX→Windows:`mkdir(path,0755)→mkdir(path)`(energy.c)、
     `system("mkdir -p ...")→mkdir()`(fpout.c,Windows cmd 不認 `-p`)、
     GCC14+ 的 incompatible-pointer-types error 降回 warning。
   - **關鍵**:`test_pdb_line` 要求 80 字元標準 PDB 行;讀檔遇到第一個
     `END` 就停止 → `END` 必須在所有 ATOM 之後。
   - 產出 `fpocket-4.2.3/bin/fpocket.exe`(2.35MB),1MC0 找到 29 口袋、
     9TPG 找到 16 口袋,info.txt 格式與官方 `pocket_feature` 解析完全一致。

2. **9TPG PDB 由 mmCIF 重建**(9TPG 是 2026 結構,RCSB 只有 .cif 無 .pdb,
   官方 inference.py 的 `requests.get(...9TPG.pdb)` 會 404):
   - 9TPG.cif 是**column-per-line** mmCIF → 用 tokenize-by-header-count
     的 robust 解析器(舊 row-based 解析會產生垃圾)。
   - chain A = **227 個正則殘基**,`pdb_seq_num` 48–274,`pdb_strand_id='A'`
     → 遠低於 ProtBERT 的 1024 殘基上限。
   - ATOM resSeq 用 `pdb_seq_num`(與 `sequence_indices()` 的 key 一致);
     SEQRES 用 DeepAllo 的**非標準版式**(chain@`line[11]`、殘基@`line[19:]`),
     與真實 D24 PDB(1MC0)逐字節對齊。
   - 80 字元標準 PDB ATOM 行、chain@21/resSeq@22-26/xyz@30-54。

3. **Python 環境(uv venv, CPU torch)**:
   - 官方模型權重全公開:`cosbi-ku/deepallo-mtl`(1.68GB, 完整 30 層
     ProtBERT + 兩個 head, 491 個 key)+ `cosbi-ku/deepallo-automl`
     (AutoGluon WeightedEnsemble_L3, 18 個 base model)。
   - encoder 用 `BertModel(BertConfig.from_pretrained(prot_bert_bfd))`
     從本地 config.json 建架構,再 `load_state_dict` 官方 fine-tuned 權重
     (base 1.68GB 權重被完全覆蓋,不用重下載)。
   - AutoGluon ensemble 在 **Linux** 訓練,其 FastAI 子模型 pickle 內嵌
     `pathlib.PosixPath`(Windows 無法 instantiate)→ 用自訂 Unpickler
     把 `PosixPath→Path`(path 只是 learner metadata,不影響 forward)。
   - 補裝 catboost/lightgbm/xgboost/fastai 2.7.15(ensemble 成員)+
     修好 uv 的系統性 broken-install(PIL/certifi/safetensors/sympy/
     setuptools 等,`uv pip install --force-reinstall`)。

4. **可重現性**:9TPG 兩次獨立運行,CPU 決定性,16 個口袋概率 bit-identical。

## 檔案

- `run_9TPG_local.py` — 官方 DeepAllo 對 9TPG(本地,可重現)
- `control_1MC0.py` — 1MC0 陽性對照(驗證管線)
- `run_9TPG_rerun.log` — 9TPG 重跑(可重現性)
- `control_1MC0.log` — 1MC0 對照(11/11 命中)
- `fpocket-4.2.3/bin/fpocket.exe` — 本機編譯的 FPocket
- `build_9tpg_pdb.py` — mmCIF→PDB(chain A, pdb_seq_num 對齊)
