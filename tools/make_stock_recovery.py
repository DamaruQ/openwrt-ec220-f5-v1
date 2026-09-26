#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, sys

EXPECTED_SIZE = 0x7C0200
OUT_SIZE = 0x7C0000
TESTED_SHA = 'd95860cda001c4dbc483800dfb07c8c3e3ff939642237b3b57d88c3181fa8629'

ap=argparse.ArgumentParser(description='Create EC220-F5 V1 TFTP stock recovery by removing the first 0x200 bytes from a TP-Link OEM up_boot image.')
ap.add_argument('oem_bin', type=Path)
ap.add_argument('-o','--output', type=Path, default=Path('tp_recovery_EC220-F5_V1_STOCK.bin'))
a=ap.parse_args()
b=a.oem_bin.read_bytes()
if len(b) != EXPECTED_SIZE:
    sys.exit(f'Unexpected OEM file size: {len(b)}; expected {EXPECTED_SIZE} (0x{EXPECTED_SIZE:X})')
out=b[0x200:]
if len(out) != OUT_SIZE:
    sys.exit('Internal size check failed')
if out[0x20000:0x20004] != bytes.fromhex('03000003'):
    sys.exit('Expected EC220 firmware header magic not found at recovery offset 0x20000')
a.output.write_bytes(out)
h=hashlib.sha256(out).hexdigest()
print(f'Wrote: {a.output}')
print(f'Size: {len(out)} (0x{len(out):X})')
print(f'SHA256: {h}')
if h == TESTED_SHA:
    print('Matches the stock recovery image validated during development.')
else:
    print('WARNING: checksum differs from the stock recovery image validated during development.')
