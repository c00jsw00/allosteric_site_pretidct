# Allosteric Site Predictor

A computational tool for predicting allosteric binding sites in proteases.

## Model Weights

Before running the predictions, please download the pre-trained model weights from the link below:
* [Download Model Weights (Google Drive)](https://drive.google.com/drive/folders/12Bc0sAMHMfufchIPJHSxfxdOIDEZairn?usp=sharing)

## Usage

You can run the prediction by specifying the model path, the target PDB file, and the desired output filename. 

Here is an example command:

```bash
python predictallo.py \
  --model_path /path/to/ag-20250812_114407 \
  --local_pdb ns2bns3.pdb \
  --output ns2bns3.csv

