#!/usr/bin/env python3
from pathlib import Path
import hashlib, lzma, struct, sys

ROOT = Path(__file__).resolve().parents[1]
TFTP = ROOT / 'firmware' / 'tp_recovery_EC220-F5_V1_OpenWrt_25.12.5_FINAL.bin'
SYS = ROOT / 'firmware' / 'openwrt-25.12.5-ramips-mt76x8-tplink_ec220-f5-v1-squashfs-sysupgrade.bin'
EXPECT = {
    TFTP.name: ('aba00e64fa0a668ccd4e2ef80d17916deb043cd3b3af50113e1cd84b9b926076', 8126464),
    SYS.name: ('7dd3179b39caa5ef6d3a56e106aecfdfe27bb46a2546bfaa4f07ee7373d38682', 7995643),
}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ok(cond, msg):
    if not cond:
        print('FAIL:', msg)
        sys.exit(1)
    print('PASS:', msg)

for p, (h, size) in [(TFTP, EXPECT[TFTP.name]), (SYS, EXPECT[SYS.name])]:
    ok(p.exists(), f'{p.name} exists')
    ok(p.stat().st_size == size, f'{p.name} size = {size}')
    ok(sha(p) == h, f'{p.name} SHA256')

t = TFTP.read_bytes()
s = SYS.read_bytes()
ok(t[:0x20000] == b'\x00' * 0x20000, 'TFTP prefix is 0x20000 zero bytes')
payload = t[0x20000:]
ok(len(payload) == 0x7a0000, 'TFTP flash payload is 0x7A0000 bytes')
ok(s[:0x7a0000] == payload, 'sysupgrade payload matches TFTP flash payload')
ok(payload[:4] == bytes.fromhex('03000003'), 'EC220 firmware header magic')
ok(int.from_bytes(payload[0x70:0x74], 'little') == 0x7a0000, 'header firmware size')
ok(int.from_bytes(payload[0x74:0x78], 'little') == 0x200, 'header kernel offset')
kl = int.from_bytes(payload[0x78:0x7c], 'little')
ok(int.from_bytes(payload[0x7c:0x80], 'little') == 0x210000, 'header rootfs offset')
root = payload[0x210000:]
ok(root[:4] == b'hsqs', 'SquashFS rootfs magic')
used = struct.unpack_from('<Q', root, 40)[0]
ok(used <= 0x590000, f'SquashFS bytes_used 0x{used:X} fits rootfs partition')
kernel = payload[0x200:0x200+kl]
ok(len(kernel) >= 13, 'LZMA kernel header is present')
prop = kernel[0]
lc = prop % 9
remainder = prop // 9
lp = remainder % 5
pb = remainder // 5
dictionary = int.from_bytes(kernel[1:5], 'little')
decoder = lzma.LZMADecompressor(
    format=lzma.FORMAT_RAW,
    filters=[{
        'id': lzma.FILTER_LZMA1,
        'dict_size': dictionary,
        'lc': lc,
        'lp': lp,
        'pb': pb,
    }],
)
raw = decoder.decompress(kernel[13:])
ok(decoder.eof, 'LZMA kernel stream reaches EOF')
ok(not decoder.unused_data, 'LZMA kernel has no trailing data')
# appended DTB must end exactly with the decompressed kernel
hits=[]
pos=0
while True:
    i=raw.find(bytes.fromhex('d00dfeed'), pos)
    if i < 0: break
    if i+8 <= len(raw):
        sz=struct.unpack_from('>I', raw, i+4)[0]
        if sz >= 40 and i+sz == len(raw): hits.append((i,sz))
    pos=i+1
ok(len(hits)==1, 'one appended DTB ending at kernel EOF')
dtb=raw[hits[0][0]:]
ok(b'tplink,ec220-f5-v1\x00' in dtb, 'DTB contains native EC220 compatible')
ok(b'TP-Link EC220-F5 v1\x00' in dtb, 'DTB contains EC220 model')
ok(struct.pack('>I', 40000000) in dtb, 'DTB contains 40 MHz SPI frequency')
print('\nRelease verification complete: all checks passed.')
