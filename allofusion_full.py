# -*- coding: utf-8 -*-
"""Complete AlloFusion inference on 9TPG with Keras-to-PyTorch weight mapping"""

import os, pickle, numpy as np, torch, torch.nn as nn
import h5py

base = r"C:\Users\c00jsw00\Downloads\allo_shared"
cnn_weights = os.path.join(base, "all.h5")
seq_file = os.path.join(base, "9tpg_A_seq.txt")
out_dir = os.path.join(base, "results")
os.makedirs(out_dir, exist_ok=True)

# Load sequence
seq = open(seq_file).read().strip()
print(f"Sequence length: {len(seq)}")

# ========== 1. ProtT5 Embeddings ==========
from transformers import T5Tokenizer, T5EncoderModel

prot_t5_dir = os.path.join(base, "prot_t5")
print("Loading ProtT5-XL...")
tokenizer = T5Tokenizer.from_pretrained(prot_t5_dir, legacy=False)
model = T5EncoderModel.from_pretrained(prot_t5_dir)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device).eval()

# Load fine-tuned head (LoRA)
ckpt = torch.load(os.path.join(prot_t5_dir, "PT5_diversity_finetuned.pth"), map_location=device)
print(f"Loaded fine-tuned head ({len(ckpt)} keys)")

def get_embeddings(sequence):
    spaced = " ".join(list(sequence))
    inputs = tokenizer(spaced, return_tensors="pt", add_special_tokens=True, padding=True)
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)
    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, output_hidden_states=True)
    hidden = outputs.hidden_states[-1].cpu().numpy()[0]
    residue_emb = hidden[1:-1]
    if residue_emb.shape[0] != len(sequence):
        if residue_emb.shape[0] > len(sequence):
            residue_emb = residue_emb[:len(sequence)]
        else:
            pad = np.zeros((len(sequence) - residue_emb.shape[0], residue_emb.shape[1]))
            residue_emb = np.vstack([residue_emb, pad])
    return residue_emb

print("Computing embeddings...")
emb = get_embeddings(seq)
print(f"Embedding shape: {emb.shape}")

# ========== 2. Feature Construction (zero PSSM/bio) ==========
pssm_dim, bio_dim = 20, 3
pssm_zeros = np.zeros((len(seq), pssm_dim))
bio_zeros = np.zeros((len(seq), bio_dim))
features = np.concatenate([emb, pssm_zeros, bio_zeros], axis=1)
print(f"Feature shape: {features.shape}")

# ========== 3. Scaler ==========
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

# ========== 4. CNN Model + Weight Loading ==========
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

cnn = CNN_Model(X_test.shape[1])

# Load Keras weights
print("Loading CNN weights from Keras HDF5...")
with h5py.File(cnn_weights, 'r') as f:
    mw = f['model_weights']
    
    # Conv1: (3, 1, 32) -> (32, 1, 3)
    k = np.transpose(np.array(mw['conv1d/conv1d/kernel:0']), (2, 1, 0))
    b = np.array(mw['conv1d/conv1d/bias:0'])
    cnn.conv1.weight.data = torch.from_numpy(k).float()
    cnn.conv1.bias.data = torch.from_numpy(b).float()
    
    # BN1
    cnn.bn1.weight.data = torch.from_numpy(np.array(mw['batch_normalization/batch_normalization/gamma:0'])).float()
    cnn.bn1.bias.data = torch.from_numpy(np.array(mw['batch_normalization/batch_normalization/beta:0'])).float()
    cnn.bn1.running_mean = torch.from_numpy(np.array(mw['batch_normalization/batch_normalization/moving_mean:0'])).float()
    cnn.bn1.running_var = torch.from_numpy(np.array(mw['batch_normalization/batch_normalization/moving_variance:0'])).float()
    
    # Conv2: (3, 32, 128) -> (128, 32, 3)
    k = np.transpose(np.array(mw['conv1d_1/conv1d_1/kernel:0']), (2, 1, 0))
    b = np.array(mw['conv1d_1/conv1d_1/bias:0'])
    cnn.conv2.weight.data = torch.from_numpy(k).float()
    cnn.conv2.bias.data = torch.from_numpy(b).float()
    
    # BN2
    cnn.bn2.weight.data = torch.from_numpy(np.array(mw['batch_normalization_1/batch_normalization_1/gamma:0'])).float()
    cnn.bn2.bias.data = torch.from_numpy(np.array(mw['batch_normalization_1/batch_normalization_1/beta:0'])).float()
    cnn.bn2.running_mean = torch.from_numpy(np.array(mw['batch_normalization_1/batch_normalization_1/moving_mean:0'])).float()
    cnn.bn2.running_var = torch.from_numpy(np.array(mw['batch_normalization_1/batch_normalization_1/moving_variance:0'])).float()
    
    # Conv3: (5, 128, 32) -> (32, 128, 5)
    k = np.transpose(np.array(mw['conv1d_2/conv1d_2/kernel:0']), (2, 1, 0))
    b = np.array(mw['conv1d_2/conv1d_2/bias:0'])
    cnn.conv3.weight.data = torch.from_numpy(k).float()
    cnn.conv3.bias.data = torch.from_numpy(b).float()
    
    # BN3
    cnn.bn3.weight.data = torch.from_numpy(np.array(mw['batch_normalization_2/batch_normalization_2/gamma:0'])).float()
    cnn.bn3.bias.data = torch.from_numpy(np.array(mw['batch_normalization_2/batch_normalization_2/beta:0'])).float()
    cnn.bn3.running_mean = torch.from_numpy(np.array(mw['batch_normalization_2/batch_normalization_2/moving_mean:0'])).float()
    cnn.bn3.running_var = torch.from_numpy(np.array(mw['batch_normalization_2/batch_normalization_2/moving_variance:0'])).float()
    
    # Conv4: (3, 32, 32) -> (32, 32, 3)
    k = np.transpose(np.array(mw['conv1d_3/conv1d_3/kernel:0']), (2, 1, 0))
    b = np.array(mw['conv1d_3/conv1d_3/bias:0'])
    cnn.conv4.weight.data = torch.from_numpy(k).float()
    cnn.conv4.bias.data = torch.from_numpy(b).float()
    
    # BN4
    cnn.bn4.weight.data = torch.from_numpy(np.array(mw['batch_normalization_3/batch_normalization_3/gamma:0'])).float()
    cnn.bn4.bias.data = torch.from_numpy(np.array(mw['batch_normalization_3/batch_normalization_3/beta:0'])).float()
    cnn.bn4.running_mean = torch.from_numpy(np.array(mw['batch_normalization_3/batch_normalization_3/moving_mean:0'])).float()
    cnn.bn4.running_var = torch.from_numpy(np.array(mw['batch_normalization_3/batch_normalization_3/moving_variance:0'])).float()
    
    # Dense layers
    # Keras: dense/kernel: (33504, 128) -> PyTorch: (128, 33504)
    cnn.dense1.weight.data = torch.from_numpy(np.array(mw['dense/dense/kernel:0']).T).float()
    cnn.dense1.bias.data = torch.from_numpy(np.array(mw['dense/dense/bias:0'])).float()
    
    cnn.dense2.weight.data = torch.from_numpy(np.array(mw['dense_1/dense_1/kernel:0']).T).float()
    cnn.dense2.bias.data = torch.from_numpy(np.array(mw['dense_1/dense_1/bias:0'])).float()
    
    cnn.dense3.weight.data = torch.from_numpy(np.array(mw['dense_2/dense_2/kernel:0']).T).float()
    cnn.dense3.bias.data = torch.from_numpy(np.array(mw['dense_2/dense_2/bias:0'])).float()

print("All weights loaded!")

# ========== 5. Inference ==========
cnn = cnn.to(device).eval()

# Input: [batch=181 residues, channels=1, length=1047 features]
X = torch.from_numpy(X_test).float().unsqueeze(1).to(device)  # [181, 1, 1047]
print(f"Input shape: {X.shape}")

with torch.no_grad():
    probs = cnn(X).cpu().numpy().flatten()  # [181]

print(f"Output shape: {probs.shape}")
print(f"Prob range: {probs.min():.6f} - {probs.max():.6f}")

# Save per-residue probabilities
out_file = os.path.join(out_dir, "9tpg_allofusion_probs.txt")
np.savetxt(out_file, probs, fmt="%.6f")
print(f"Saved per-residue probabilities to {out_file}")

# Identify predicted allosteric residues (prob > 0.5)
pred_res = [i+1 for i, p in enumerate(probs) if p > 0.5]  # 1-indexed
print(f"Predicted allosteric residues (prob>0.5): {len(pred_res)}")
if pred_res:
    print(f"  Residues: {pred_res[:20]}{'...' if len(pred_res)>20 else ''}")

# Save prediction in AlloFusion format
with open(os.path.join(out_dir, "9tpg_allosteric_residues.txt"), "w") as f:
    f.write("AlloFusion Allosteric Site Forming Residues:\n")
    f.write("Residues: ( Chain A and resid " + ",".join(map(str, pred_res)) + " )")

# Also save raw probabilities with residue indices
with open(os.path.join(out_dir, "9tpg_allofusion_detailed.txt"), "w") as f:
    f.write("Residue\tProbability\n")
    for i, p in enumerate(probs):
        f.write(f"{i+1}\t{p:.6f}\n")

print(f"Done. Results in {out_dir}")