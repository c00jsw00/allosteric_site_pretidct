import math
import sys

pdb_path = r'C:\Users\c00jsw00\Downloads\9tpg.pdb'
ligand = []
protein = []

with open(pdb_path) as f:
    for line in f:
        if line.startswith('HETATM') and 'A1H2' in line:
            ligand.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
        elif line.startswith('ATOM  '):
            protein.append((int(line[22:26]), line[17:20].strip(), line[21], float(line[30:38]), float(line[38:46]), float(line[46:54])))

print(f'Ligand atoms: {len(ligand)}, Protein atoms: {len(protein)}')

contact = set()
for rseq, rname, chain, px, py, pz in protein:
    for lx, ly, lz in ligand:
        if ((px-lx)**2 + (py-ly)**2 + (pz-lz)**2) <= 25:
            contact.add((rseq, rname))
            break

for r, n in sorted(contact):
    print(f'{n} A {r}')
print(f'Total contact residues: {len(contact)}')

# Ranges
if contact:
    sorted_res = sorted(contact, key=lambda x: x[0])
    ranges = []
    start = sorted_res[0][0]
    prev = start
    for r, n in sorted_res[1:]:
        if r == prev + 1:
            prev = r
        else:
            ranges.append((start, prev))
            start = r
            prev = r
    ranges.append((start, prev))
    print(f'Contact ranges: {ranges}')