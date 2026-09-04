# -*- coding: utf-8 -*-
"""Minimal AlloFusion inference on 9TPG using only ProtT5 embeddings + CNN head.
Skips PSSM (needs BLAST) and bio features (needs ProDy) - uses zero vectors as placeholder.
"""

import os, pickle, numpy as np, torch, torch.nn as nn
from transformers import T5Tokenizer, T5EncoderModel

# Paths
base = r"C:\Users\c00jsw00\Downloads\allo_shared"
prot_t5_dir = os.path.join(base, "prot_t5")
cnn_weights = os.path.join(base, "all.h5")
seq_file = os.path.join(base, "9tpg_A_seq.txt")
out_dir = os.path.join(base, "results")
os.makedirs(out_dir, exist_ok=True)

# Load sequence
seq = open(seq_file).read().strip()
print(f"Sequence length: {len(seq)}")
print(f"Sequence: {seq[:60]}...")

# Load ProtT5-XL (base model) + fine-tuned head
print("Loading ProtT5-XL...")
tokenizer = T5Tokenizer.from_pretrained(prot_t5_dir, legacy=False)
model = T5EncoderModel.from_pretrained(prot_t5_dir)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device).eval()
print(f"Device: {device}")

# Load fine-tuned head weights (LoRA + classifier)
print("Loading fine-tuned head...")
ckpt = torch.load(os.path.join(prot_t5_dir, "PT5_diversity_finetuned.pth"), map_location=device)
print(f"Checkpoint keys: {list(ckpt.keys())[:10]}... (total {len(ckpt)} keys)")

# Create tokenizer+model pipeline for embeddings
def get_embeddings(sequence):
    """Get per-residue embeddings from ProtT5-XL"""
    spaced = " ".join(list(sequence))
    inputs = tokenizer(spaced, return_tensors="pt", add_special_tokens=True, padding=True)
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)
    
    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, output_hidden_states=True)
    hidden = outputs.hidden_states[-1].cpu().numpy()[0]
    residue_emb = hidden[1:-1]  # skip <pad> and </s>
    return residue_emb

print("Computing embeddings...")
emb = get_embeddings(seq)
print(f"Embedding shape: {emb.shape}")

# Build feature vector: concat(emb, pssm_zeros, bio_zeros)
# Fix: embedding might be 180 instead of 181 due to tokenizer
# Pad or trim to match sequence length
if emb.shape[0] != len(seq):
    print(f"Warning: emb has {emb.shape[0]} residues, seq has {len(seq)}. Adjusting...")
    if emb.shape[0] > len(seq):
        emb = emb[:len(seq)]
    else:
        # Pad with zeros
        pad = np.zeros((len(seq) - emb.shape[0], emb.shape[1]))
        emb = np.vstack([emb, pad])
    print(f"Adjusted embedding shape: {emb.shape}")

# Build feature vector: concat(emb, pssm_zeros, bio_zeros)
pssm_dim = 20
bio_dim = 3
feat_dim = 1024 + pssm_dim + bio_dim

pssm_zeros = np.zeros((len(seq), pssm_dim))
bio_zeros = np.zeros((len(seq), bio_dim))

features = np.concatenate([emb, pssm_zeros, bio_zeros], axis=1)
print(f"Feature shape: {features.shape}")

# StandardScaler fitted on training data
print("Loading training data for scaler...")
train0 = pickle.load(open(os.path.join(base, "features_data", "diversity", "train_dataset_0.pkl"), "rb"))
train1 = pickle.load(open(os.path.join(base, "features_data", "diversity", "train_dataset_1.pkl"), "rb"))

all_train_feats = []
for ds in [train0, train1]:
    if isinstance(ds, dict):
        feats = ds.get("features", [])
    else:
        import pandas as pd
        ds = pd.DataFrame.from_dict(ds)
        feats = ds["features"].tolist()
    all_train_feats.extend(feats)

all_train = np.vstack(all_train_feats)
print(f"Training features shape: {all_train.shape}")

from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
scaler.fit(all_train)

X_test = scaler.transform(features)
print(f"Scaled test shape: {X_test.shape}")

# CNN model (from prediced.py)
class CNN_Model(nn.Module):
    def __init__(self, feat_shape):
        super().__init__()
        self.conv1 = nn.Conv1d(1, 32, 3, padding='same')
        self.bn1 = nn.BatchNorm1d(32)
        self.drop1 = nn.Dropout(0.2)
        self.conv2 = nn.Conv1d(32, 128, 3, padding='same')
        self.bn2 = nn.BatchNorm1d(128)
        self.drop2 = nn.Dropout(0.3)
        self.conv3 = nn.Conv1d(128, 32, 5, padding='same')
        self.bn3 = nn.BatchNorm1d(32)
        self.drop3 = nn.Dropout(0.2)
        self.conv4 = nn.Conv1d(32, 32, 3, padding='same')
        self.bn4 = nn.BatchNorm1d(32)
        self.drop4 = nn.Dropout(0.3)
        self.flatten = nn.Flatten()
        self.dense1 = nn.Linear(feat_shape * 32, 128)
        self.dense2 = nn.Linear(128, 32)
        self.dense3 = nn.Linear(32, 1)
        
    def forward(self, x):
        x = torch.relu(self.bn1(self.conv1(x)))
        x = self.drop1(x)
        x = torch.relu(self.bn2(self.conv2(x)))
        x = self.drop2(x)
        x = torch.relu(self.bn3(self.conv3(x)))
        x = self.drop3(x)
        x = torch.relu(self.bn4(self.conv4(x)))
        x = self.drop4(x)
        x = self.flatten(x)
        x = torch.relu(self.dense1(x))
        x = torch.relu(self.dense2(x))
        x = torch.sigmoid(self.dense3(x))
        return x

cnn = CNN_Model(feat_dim)

# Load CNN weights from all.h5 (Keras HDF5)
print("Loading CNN weights...")
import h5py
with h5py.File(cnn_weights, 'r') as f:
    print("HDF5 keys:", list(f.keys()))
    for k in f.keys():
        print(f"  {k}: {type(f[k])}")
        if hasattr(f[k], 'keys'):
            for k2 in f[k].keys():
                print(f"    {k2}: {f[k][k2].shape if hasattr(f[k][k2], 'shape') else type(f[k][k2])}")