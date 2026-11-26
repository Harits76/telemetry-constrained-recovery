"""Restore hash-checked integer truth data for fast numerical replay."""
from pathlib import Path
import csv,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
audit={r['Case']:r['TruthSHA256'] for r in csv.DictReader((ROOT/'results/all_Truth_Audit.csv').open())}
tab=np.load(ROOT/'data/full_truth.npz',allow_pickle=False)
expected={p.stem for p in (ROOT/'cases').glob('*/*.json')}
assert set(tab.files)==set(audit)==expected
(ROOT/'work').mkdir(exist_ok=True)
for name in sorted(expected):
    values=tab[name];assert values.shape==(1<<20,)
    data=values.astype('<i4').tobytes();assert hashlib.sha256(data).hexdigest()==audit[name]
    (ROOT/'work'/f'{name}.bin').write_bytes(data)
print('Restored48 hash-checked full-state tables. Remove work/*.bin to rebuild all integer flows.')
