#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gc
import torch
import torch.nn as nn
import requests
import glob
import os
import math
import numpy as np
import argparse
import pandas as pd
from transformers import AutoModel, BertTokenizer
from autogluon.tabular import TabularDataset, TabularPredictor
from huggingface_hub import hf_hub_download

from utils.extract_sequence import extract_sequence
from utils.pocket_feature import pocket_feature
from utils.sequence_indices import sequence_indices
from utils.pocket_coordinates import pocket_coordinates

def predict_with_custom_automl(pdb_id, chain_id, custom_automl_path, local_pdb_path=None, use_pretrained_mtl=True):
    print(f"=== 使用自訓練 AutoML 模型預測 PDB {pdb_id} 鏈 {chain_id} ===")

    # 獲取當前執行目錄
    current_dir = os.getcwd()
    
    base_url = "https://files.rcsb.org/download"

    pdb_path = os.path.join(current_dir, f"{pdb_id}.pdb")
    pocket_path = os.path.join(current_dir, f"{pdb_id}_out")

    # 1. 獲取 PDB 文件
    if local_pdb_path and os.path.exists(local_pdb_path):
        print(f"使用本地 PDB 文件: {local_pdb_path}")
        if os.path.abspath(local_pdb_path) != os.path.abspath(pdb_path):
            import shutil
            shutil.copy2(local_pdb_path, pdb_path)
        else:
            print("本地文件已在正確位置，無需複製")
    elif not os.path.exists(pdb_path):
        print(f"下載 PDB 文件: {pdb_id}")
        response = requests.get(f"{base_url}/{pdb_id}.pdb")
        if response.status_code == 200:
            with open(pdb_path, "wb") as file:
                file.write(response.content)
            print(f"✓ PDB 文件下載成功")
        else:
            raise Exception(f"下載 PDB 文件失敗: HTTP {response.status_code}")

    # 2. 提取序列 - 增加更多的調試信息
    print("開始提取序列...")
    sequence = None
    try:
        sequence = extract_sequence(pdb_path, chain_id)
        print(f"自動提取序列長度: {len(sequence)}")
        if len(sequence) == 0:
            sequence = None
    except Exception as e:
        print(f"自動序列提取失敗: {e}")
        sequence = None

    # 如果自動提取失敗，使用手動提取
    if sequence is None or len(sequence) == 0:
        print("使用手動序列提取...")
        sequence = manual_extract_sequence(pdb_path, chain_id)
        print(f"手動提取序列長度: {len(sequence)}")
        
    if len(sequence) == 0:
        raise Exception("無法從 PDB 文件中提取序列，序列長度為 0")
        
    print(f"最終序列長度: {len(sequence)}")
    print(f"序列前20個殘基: {''.join(sequence[:20])}")

    # 3. 提取口袋 - 直接在當前目錄執行
    print("提取蛋白質口袋...")
    
    # 檢查是否已經存在口袋輸出
    if not os.path.exists(pocket_path):
        # 執行 fpocket
        print(f"執行 fpocket: fpocket -f {pdb_path} -k {chain_id}")
        fpocket_result = os.system(f"fpocket -f {pdb_path} -k {chain_id}")
        if fpocket_result != 0:
            raise Exception("fpocket 執行失敗")
        
        # 確認口袋目錄已建立
        if not os.path.exists(pocket_path):
            # 有時 fpocket 會使用不同的命名方式
            alt_pocket_path = os.path.join(current_dir, f"{os.path.basename(pdb_path).split('.')[0]}_out")
            if os.path.exists(alt_pocket_path):
                pocket_path = alt_pocket_path
                print(f"使用替代口袋目錄: {pocket_path}")
            else:
                raise Exception(f"fpocket 執行後未產生預期的口袋目錄: {pocket_path}")
    
    print(f"口袋目錄: {pocket_path}")

    # 4. 處理口袋數據
    pocket_pdb_dir = os.path.join(pocket_path, "pockets")
    if not os.path.exists(pocket_pdb_dir):
        raise Exception(f"口袋 PDB 目錄不存在: {pocket_pdb_dir}")
        
    pocket_names = glob.glob(f"{pocket_pdb_dir}/*.pdb")
    pocket_names = sorted(pocket_names, key=lambda x: int(os.path.basename(x).split("pocket")[-1].split("_")[0]))

    print(f"發現 {len(pocket_names)} 個口袋")
    
    if len(pocket_names) == 0:
        raise Exception("未找到任何口袋文件")

    # 5. 提取口袋特徵
    pockets_info_file = os.path.join(pocket_path, f"{pdb_id}_info.txt")
    if not os.path.exists(pockets_info_file):
        raise Exception(f"口袋資訊文件不存在: {pockets_info_file}")
    
    pockets_feats = pocket_feature(pockets_info_file)
    selected_idxs = []
    pocket_residue_indices = []

    for idx, pocket_name in enumerate(pocket_names):
        with open(pocket_name, "r") as f:
            pocket = f.readlines()

        poc_cnt = 0
        residue_indices = set()

        for line in pocket:
            if line[:4] == "ATOM":
                poc_cnt += 1
                residue_index = line[22:26].strip()
                residue_indices.add(residue_index)

        if poc_cnt > 0:
            selected_idxs.append(idx)
            pocket_residue_indices.append(list(residue_indices))
            print(f"口袋 {idx+1}: {poc_cnt} 個原子, {len(residue_indices)} 個殘基")

    if len(selected_idxs) == 0:
        raise Exception("所有口袋都沒有原子數據")

    pocket_features = [pockets_feats[idx] for idx in selected_idxs]
    
    # 6. 提取序列索引
    seq_indices = None
    try:
        seq_indices = sequence_indices(pdb_id, chain_id)
        print(f"自動提取序列索引數量: {len(seq_indices)}")
    except Exception as e:
        print(f"自動序列索引提取失敗: {e}")
        print("使用手動序列索引提取...")
        seq_indices = manual_sequence_indices(pdb_path, chain_id)
        print(f"手動提取序列索引數量: {len(seq_indices)}")

    # 7. 載入 MTL 模型
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    os.makedirs(os.path.join(current_dir, "models", "deepallo"), exist_ok=True)

    if use_pretrained_mtl:
        print("下載預訓練 MTL 模型...")
        try:
            model_path = hf_hub_download(
                repo_id="cosbi-ku/deepallo-mtl",
                filename="prot-bert-deepallo-mtl.bin",
                local_dir=os.path.join(current_dir, "models", "deepallo"),
            )
        except Exception as e:
            raise Exception(f"下載預訓練 MTL 模型失敗: {e}")
    else:
        model_path = os.path.join(current_dir, "models", "deepallo", "prot-bert-deepallo-mtl.bin")
        if not os.path.exists(model_path):
            raise Exception(f"找不到自定義 MTL 模型: {model_path}")

    class MultiTaskModel(nn.Module):
        def __init__(self, model_name, num_labels_task1, num_labels_task2):
            super(MultiTaskModel, self).__init__()
            self.encoder = AutoModel.from_pretrained(model_name)
            self.head1 = nn.Linear(self.encoder.config.hidden_size, num_labels_task1)
            self.head2 = nn.Linear(self.encoder.config.hidden_size, num_labels_task2)

        def forward(self, input1=None, input2=None):
            output1, output2 = None, None
            encoder_output1, encoder_output2 = None, None

            if input1 is not None:
                encoder_output1 = self.encoder(**input1).last_hidden_state
                output1 = self.head1(encoder_output1)

            if input2 is not None:
                encoder_output2 = self.encoder(**input2).last_hidden_state
                output2 = self.head2(encoder_output2)

            return (output1, output2), (encoder_output1, encoder_output2)

    tokenizer = BertTokenizer.from_pretrained("Rostlab/prot_bert_bfd", do_lower_case=False)
    model = MultiTaskModel("Rostlab/prot_bert_bfd", 2, 3)
    state_dict = torch.load(model_path, map_location=device)
    model.load_state_dict(state_dict)
    model = model.to(device)
    model = model.eval()

    # 8. 提取特徵
    print("提取序列特徵...")
    poc_res_emb = []

    with torch.no_grad():
        seq = " ".join(sequence)
        encoding = tokenizer.batch_encode_plus(
            [seq], add_special_tokens=True, padding="max_length", max_length=1024, truncation=True
        )
        input_ids = torch.tensor(encoding["input_ids"]).to(device)
        attention_mask = torch.tensor(encoding["attention_mask"]).to(device)
        inputs = {"input_ids": input_ids, "attention_mask": attention_mask}
        _, (last_hidden_state, _) = model(input1=inputs)
        embedding = last_hidden_state.cpu().numpy()

        seq_len = (attention_mask[0] == 1).sum()
        token_emb = embedding[0][1 : seq_len - 1]
        print(f"提取到的 token embedding 數量: {len(token_emb)}")

        for i in range(len(pocket_residue_indices)):
            cur_poc_emb = []
            for idx in pocket_residue_indices[i]:
                try:
                    if idx in seq_indices and seq_indices[idx] < len(token_emb):
                        token = token_emb[seq_indices[idx]]
                        cur_poc_emb.append(token)
                except Exception as e:
                    print(f"警告: 無法處理殘基索引 {idx}: {e}")
                    pass

            if len(cur_poc_emb) > 0:
                poc_res_emb.append(cur_poc_emb)
            else:
                poc_res_emb.append([])

    del model
    torch.cuda.empty_cache()
    gc.collect()

    # 9. 準備測試數據
    pocket_coord = pocket_coordinates(
        pdb_path, pocket_pdb_dir, pdb_id, chain_id, pocket_residue_indices
    )

    X_Test = []
    valid_pockets = []

    for i in range(min(len(poc_res_emb), len(pocket_coord))):
        if len(poc_res_emb[i]) > 0 and len(pocket_coord[i]) > 0:
            seq_emb = np.array(poc_res_emb[i]).mean(axis=0)
            poc = pocket_features[i]
            X_Test.append(np.concatenate((seq_emb, poc)))
            valid_pockets.append(i)

    if len(X_Test) == 0:
        raise Exception("沒有有效的測試數據可以處理")

    X_Test = np.array(X_Test)
    print(f"測試數據形狀: {X_Test.shape}")

    # 10. 載入自己的 AutoML 模型並預測
    print(f"載入自訓練 AutoML 模型: {custom_automl_path}")

    if not os.path.exists(custom_automl_path):
        raise Exception(f"找不到 AutoML 模型: {custom_automl_path}")

    test_data = TabularDataset(X_Test)
    test_data.columns = [str(i) for i in range(1, X_Test.shape[1] + 1)]

    predictor = TabularPredictor.load(custom_automl_path)
    y_pred = predictor.predict_proba(test_data)

    if hasattr(y_pred, 'to_numpy'):
        if len(y_pred.columns) == 2:
            y_pred_probs = y_pred.to_numpy()[:, 1]
        else:
            y_pred_probs = y_pred.to_numpy().flatten()
    else:
        y_pred_probs = y_pred

    # 11. 整理結果
    results = []
    for i, prob in enumerate(y_pred_probs):
        pocket_idx = valid_pockets[i]
        results.append({
            'pocket_id': pocket_idx + 1,
            'probability': float(prob),
            'residue_count': len(pocket_residue_indices[pocket_idx]),
            'residue_indices': sorted(pocket_residue_indices[pocket_idx], key=lambda x: int(x)),
            'pocket_file': pocket_names[pocket_idx] if pocket_idx < len(pocket_names) else None
        })

    results.sort(key=lambda x: x['probability'], reverse=True)
    return results

def manual_extract_sequence(pdb_path, chain_id):
    """手動從 PDB 文件提取序列"""
    sequence = []
    prev_residue_num = None
    
    print(f"手動提取序列 - PDB文件: {pdb_path}, 鏈ID: {chain_id}")
    
    try:
        with open(pdb_path, 'r') as f:
            for line_num, line in enumerate(f):
                if line.startswith('ATOM') and len(line) > 21 and line[21] == chain_id:
                    residue_num = line[22:26].strip()
                    residue_name = line[17:20].strip()
                    
                    # 只在新的殘基時添加
                    if residue_num != prev_residue_num:
                        # 轉換三字母代碼為單字母代碼
                        single_letter = three_to_one.get(residue_name, 'X')
                        sequence.append(single_letter)
                        prev_residue_num = residue_num
                        
                        # 調試信息（只顯示前幾個）
                        if len(sequence) <= 5:
                            print(f"  行 {line_num+1}: 殘基 {residue_num} ({residue_name} -> {single_letter})")
    except Exception as e:
        raise Exception(f"讀取 PDB 文件失敗: {e}")
    
    print(f"手動提取完成，共找到 {len(sequence)} 個殘基")
    return sequence

def manual_sequence_indices(pdb_path, chain_id):
    """手動從 PDB 文件提取序列索引映射"""
    seq_indices = {}
    residue_counter = 0
    prev_residue_num = None
    
    print(f"手動提取序列索引 - PDB文件: {pdb_path}, 鏈ID: {chain_id}")
    
    try:
        with open(pdb_path, 'r') as f:
            for line in f:
                if line.startswith('ATOM') and len(line) > 21 and line[21] == chain_id:
                    residue_num = line[22:26].strip()
                    
                    # 只在新的殘基時計數
                    if residue_num != prev_residue_num:
                        seq_indices[residue_num] = residue_counter
                        residue_counter += 1
                        prev_residue_num = residue_num
    except Exception as e:
        raise Exception(f"讀取 PDB 文件失敗: {e}")
    
    print(f"手動索引提取完成，共映射 {len(seq_indices)} 個殘基")
    return seq_indices

# 氨基酸三字母代碼到單字母代碼的映射
three_to_one = {
    'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C',
    'GLU': 'E', 'GLN': 'Q', 'GLY': 'G', 'HIS': 'H', 'ILE': 'I',
    'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F', 'PRO': 'P',
    'SER': 'S', 'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V'
}

def main():
    parser = argparse.ArgumentParser(description="預測 PDB 異構調節口袋")
    parser.add_argument("pdb_id", type=str, nargs='?', default=None, help="PDB ID")
    parser.add_argument("chain_id", type=str, nargs='?', default=None, help="Chain ID")
    parser.add_argument("--model_path", type=str, required=True, help="自訓練 AutoML 模型路徑")
    parser.add_argument("--local_pdb", type=str, help="本地 PDB 檔案路徑（可選）")
    parser.add_argument("--use_pretrained_mtl", action="store_true", help="是否使用預訓練 MTL 模型")
    parser.add_argument("--output", type=str, default="prediction_results.csv", help="輸出結果檔案名稱")

    args = parser.parse_args()

    # 處理本地 PDB 文件的情況
    if args.local_pdb:
        if args.pdb_id is None:
            # 從文件名提取 pdb_id
            pdb_id = os.path.basename(args.local_pdb).split('.')[0]
            args.pdb_id = pdb_id
            print(f"從本地文件名提取 PDB ID: {args.pdb_id}")
        if args.chain_id is None:
            args.chain_id = "A"  # 默認鏈 ID
            print(f"使用默認鏈 ID: {args.chain_id}")
    else:
        if args.pdb_id is None or args.chain_id is None:
            raise Exception("必須提供 PDB ID 和 Chain ID，或者提供 --local_pdb 參數")

    try:
        results = predict_with_custom_automl(
            pdb_id=args.pdb_id,
            chain_id=args.chain_id,
            custom_automl_path=args.model_path,
            local_pdb_path=args.local_pdb,
            use_pretrained_mtl=args.use_pretrained_mtl
        )

        # 將結果儲存到當前執行目錄
        output_path = os.path.join(os.getcwd(), args.output)
        df = pd.DataFrame(results)
        df.to_csv(output_path, index=False)
        print(f"預測結果已儲存至: {output_path}")
        
        # 顯示前幾個結果
        print("\n前5個預測結果:")
        for i, result in enumerate(results[:5]):
            print(f"  {i+1}. 口袋 {result['pocket_id']}: 概率 {result['probability']:.4f}, "
                  f"殘基數量 {result['residue_count']}")

    except Exception as e:
        print(f"預測失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

