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

20.206028059124946611['88', '89', '90', '91', '106', '111', '122', '123', '124', '125', '130']70.1279400140047073410['90', '91', '92', '101', '117', '118', '119', '121', '122', '123']80.1265914142131805411['85', '86', '87', '105', '106', '107', '163', '203', '205', '209', '211']50.1118428409099578910['190', '191', '193', '195', '196', '197', '200', '215', '216', '217']40.07133895215['138', '139', '141', '148', '150', '152', '185', '188', '211', '212', '213', '214', '217', '218', '220']90.0598259617['115', '120', '132', '133', '134', '135', '142']30.05960328110['89', '91', '94', '98', '99', '100', '167', '168', '169', '170']10.05899803311['157', '158', '159', '160', '161', '175', '177', '205', '206', '207', '209']100.0305801760405302059['154', '156', '157', '177', '178', '179', '180', '187', '221']60.0110417502000927938['153', '154', '155', '158', '159', '206', '207', '208']110.0060242927['107', '108', '150', '151', '152', '210', '211']
