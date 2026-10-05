"""Verify every published runtime file against exact accepted product bytes."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1]
m=json.loads((root/'DELIVERY-MANIFEST.json').read_text())
for item in m['runtime_byte_equal_files']:
 p=root/item['path']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'], str(p)
print(f"PASS: {len(m['runtime_byte_equal_files'])} runtime files match accepted product {m['product_sha']}")
