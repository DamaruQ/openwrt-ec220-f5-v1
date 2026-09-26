from pathlib import Path
from dataclasses import dataclass, field
import struct, subprocess, hashlib, json, shutil, os

W = Path(os.environ.get('EC220_BUILD_WORK', 'work_ec220_final')).resolve()
RC2 = Path(os.environ.get('EC220_RC2', W/'rc2.bin')).resolve()
STOCK = Path(os.environ.get(
    'EC220_STOCK_TFTP',
    W/'tp_recovery_EC220-F5_V1_STOCK.bin',
)).resolve()
ROOTFS = Path(os.environ.get('EC220_ROOTFS', W/'final_rootfs.squashfs')).resolve()
IB = Path(os.environ.get('OPENWRT_IMAGEBUILDER', W/'imagebuilder')).resolve()
FWTOOL = Path(os.environ.get(
    'OPENWRT_FWTOOL',
    IB/'staging_dir/host/bin/fwtool',
)).resolve()

OUT_TFTP = W/'tp_recovery_EC220-F5_V1_OpenWrt_25.12.5_FINAL.bin'
OUT_FW = W/'openwrt-25.12.5-ramips-mt76x8-tplink_ec220-f5-v1-squashfs-firmware.bin'
OUT_SYS = W/'openwrt-25.12.5-ramips-mt76x8-tplink_ec220-f5-v1-squashfs-sysupgrade.bin'
OUT_REPORT = W/'EC220-F5_OpenWrt_25.12.5_FINAL_REPORT.txt'
OUT_AUDIT = W/'EC220-F5_OpenWrt_25.12.5_FINAL_DTB_AUDIT.txt'
OUT_SUMS = W/'EC220-F5_OpenWrt_25.12.5_FINAL_SHA256SUMS.txt'
WORK = W/'final_kernel_work'; WORK.mkdir(parents=True, exist_ok=True)

FW_SIZE=0x7A0000
TFTP_PREFIX=0x20000
ROOTFS_REL=0x210000
KERNEL_FLASH_ABS=0x20000
ROOTFS_FLASH_ABS=0x230000
FLASH_FW_END=0x7C0000
ROOTFS_PART_SIZE=0x590000
BLOCK=0x10000


def sha256(b:bytes): return hashlib.sha256(b).hexdigest()
def sha_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()
def align(x,a): return (x+a-1)&~(a-1)
def p32(v): return struct.pack('>I',v)
def cells(*v): return b''.join(p32(x) for x in v)
def cstr(s): return s.encode()+b'\0'
def cstrs(*ss): return b''.join(cstr(s) for s in ss)

@dataclass
class Node:
    name:str
    props:list=field(default_factory=list)
    children:list=field(default_factory=list)
    def get(self,k):
        for n,v in self.props:
            if n==k: return v
        return None
    def set(self,k,v):
        for i,(n,old) in enumerate(self.props):
            if n==k:
                self.props[i]=(k,v); return
        self.props.append((k,v))
    def child(self,name):
        for c in self.children:
            if c.name==name: return c
        return None

class FDT:
    BEGIN_NODE=1; END_NODE=2; PROP=3; NOP=4; END=9
    def __init__(self,root,memrsv,version=17,last_comp=16,boot_cpuid=0):
        self.root=root; self.memrsv=memrsv; self.version=version; self.last_comp=last_comp; self.boot_cpuid=boot_cpuid
    @classmethod
    def parse(cls,blob):
        if len(blob)<40: raise ValueError('short DTB')
        magic,total,os_,ostr,omr,ver,last,boot,ss,szs=struct.unpack_from('>10I',blob,0)
        if magic!=0xd00dfeed or total>len(blob): raise ValueError('bad DTB header')
        strings=blob[ostr:ostr+ss]
        def propname(off):
            e=strings.find(b'\0',off)
            if e<0: raise ValueError('bad string offset')
            return strings[off:e].decode('ascii')
        q=omr
        while True:
            a,s=struct.unpack_from('>QQ',blob,q); q+=16
            if a==0 and s==0: break
        memrsv=blob[omr:q]
        pos=os_; end=os_+szs; stack=[]; root=None
        while pos<end:
            tok=struct.unpack_from('>I',blob,pos)[0]; pos+=4
            if tok==cls.BEGIN_NODE:
                e=blob.find(b'\0',pos,end)
                name=blob[pos:e].decode('ascii','replace'); pos=align(e+1,4)
                n=Node(name)
                if stack: stack[-1].children.append(n)
                else: root=n
                stack.append(n)
            elif tok==cls.END_NODE:
                stack.pop()
            elif tok==cls.PROP:
                ln,no=struct.unpack_from('>II',blob,pos); pos+=8
                val=blob[pos:pos+ln]; pos=align(pos+ln,4)
                stack[-1].props.append((propname(no),val))
            elif tok==cls.NOP:
                pass
            elif tok==cls.END:
                break
            else: raise ValueError(f'unknown token {tok}')
        if root is None or stack: raise ValueError('malformed DTB')
        return cls(root,memrsv,ver,last,boot)
    def find(self,path):
        if path=='/': return self.root
        n=self.root
        for part in [x for x in path.split('/') if x]:
            n=n.child(part)
            if n is None: return None
        return n
    def to_bytes(self):
        names=[]; seen=set()
        def gather(n):
            for k,_ in n.props:
                if k not in seen: seen.add(k); names.append(k)
            for c in n.children: gather(c)
        gather(self.root)
        strings=bytearray(); noff={}
        for s in names:
            noff[s]=len(strings); strings += s.encode()+b'\0'
        st=bytearray()
        def u32(v): st.extend(struct.pack('>I',v))
        def emit(n):
            u32(self.BEGIN_NODE); st.extend(n.name.encode()+b'\0')
            while len(st)%4: st.append(0)
            for k,v in n.props:
                u32(self.PROP); u32(len(v)); u32(noff[k]); st.extend(v)
                while len(st)%4: st.append(0)
            for c in n.children: emit(c)
            u32(self.END_NODE)
        emit(self.root); u32(self.END)
        off_mem=40
        off_struct=align(off_mem+len(self.memrsv),8)
        pad1=b'\0'*(off_struct-(off_mem+len(self.memrsv)))
        off_strings=align(off_struct+len(st),4)
        pad2=b'\0'*(off_strings-(off_struct+len(st)))
        total=off_strings+len(strings)
        hdr=struct.pack('>10I',0xd00dfeed,total,off_struct,off_strings,off_mem,self.version,self.last_comp,self.boot_cpuid,len(strings),len(st))
        return hdr+self.memrsv+pad1+bytes(st)+pad2+bytes(strings)

# Inputs
rc2=RC2.read_bytes(); stock=STOCK.read_bytes(); rootfs=ROOTFS.read_bytes()
assert len(rc2)==0x7C0000
assert len(stock)==0x7C0000
assert rootfs[:4]==b'hsqs'
rootfs_used=struct.unpack_from('<Q',rootfs,40)[0]
assert rootfs_used==len(rootfs)
assert len(rootfs)<ROOTFS_PART_SIZE
stock_inner=bytearray(stock[0x20000:0x20200])
assert stock_inner[:4]==bytes.fromhex('03000003')
assert stock_inner[0x40:0x54]==b'\0'*0x14

# Extract tested RC2 kernel
rc2fw=rc2[TFTP_PREFIX:]
rc2h=rc2fw[:0x200]
ko=int.from_bytes(rc2h[0x74:0x78],'little'); kl=int.from_bytes(rc2h[0x78:0x7c],'little')
ro=int.from_bytes(rc2h[0x7c:0x80],'little')
assert ko==0x200 and ro==ROOTFS_REL
kernel_lzma=rc2fw[ko:ko+kl]
lzp=WORK/'kernel.rc2.lzma'; rawp=WORK/'kernel.rc2.raw'
lzp.write_bytes(kernel_lzma)
with open(rawp,'wb') as f: subprocess.run(['xz','--format=lzma','-dc',str(lzp)],check=True,stdout=f)
raw=rawp.read_bytes()
# Locate appended DTB
cand=[]; pos=0
while True:
    i=raw.find(bytes.fromhex('d00dfeed'),pos)
    if i<0: break
    if i+8<=len(raw):
        sz=struct.unpack_from('>I',raw,i+4)[0]
        if sz>=40 and i+sz==len(raw): cand.append((i,sz))
    pos=i+1
assert len(cand)==1,cand
dtb_off,old_dtb_len=cand[0]
fdt=FDT.parse(raw[dtb_off:])
# Native identity. No C50 alias remains in compatible.
fdt.root.set('compatible',cstrs('tplink,ec220-f5-v1','mediatek,mt7628an-soc'))
fdt.root.set('model',cstr('TP-Link EC220-F5 v1'))
# Verify the already-tested RC2 hardware DT state remains unchanged.
flash_path='/palmbus@10000000/spi@b00/flash@0'
parts_path=flash_path+'/partitions'
flash=fdt.find(flash_path); assert flash
assert struct.unpack('>I',flash.get('spi-max-frequency'))[0]==40000000
expected=[
 ('partition@0','boot',0x000000,0x020000),
 ('partition@20000','kernel',0x020000,0x210000),
 ('partition@230000','rootfs',0x230000,0x590000),
 ('partition@7c0000','config',0x7c0000,0x010000),
 ('partition@7d0000','rom',0x7d0000,0x010000),
 ('partition@7e0000','romfile',0x7e0000,0x010000),
 ('partition@7f0000','radio',0x7f0000,0x010000),
]
parts=fdt.find(parts_path); assert parts
actual=[]
for c in parts.children:
    reg=c.get('reg'); label=(c.get('label') or b'').rstrip(b'\0').decode()
    if reg and len(reg)==8:
        actual.append((c.name,label,*struct.unpack('>II',reg)))
assert actual==expected,(actual,expected)
# NVMEM exact refs
assert struct.unpack('>II',fdt.find(parts_path+'/partition@7d0000/nvmem-layout/macaddr@f100').get('reg'))==(0xf100,6)
assert struct.unpack('>II',fdt.find(parts_path+'/partition@7f0000/nvmem-layout/eeprom@0').get('reg'))==(0,0x400)
assert struct.unpack('>II',fdt.find(parts_path+'/partition@7f0000/nvmem-layout/eeprom@8000').get('reg'))==(0x8000,0x4da8)
new_dtb=fdt.to_bytes()
# Roundtrip identity
rf=FDT.parse(new_dtb)
assert rf.root.get('compatible').split(b'\0')[:2]==[b'tplink,ec220-f5-v1',b'mediatek,mt7628an-soc']
assert rf.root.get('model').rstrip(b'\0')==b'TP-Link EC220-F5 v1'
new_raw=raw[:dtb_off]+new_dtb
newrawp=WORK/'kernel.final.raw'; newrawp.write_bytes(new_raw)
# Recompress with stock-native LZMA properties.
tmp=WORK/'kernel.final.tmp.lzma'; final_lz=WORK/'kernel.final.lzma'
with open(tmp,'wb') as f:
    subprocess.run(['xz','--format=lzma','--lzma1=dict=8MiB,lc=3,lp=0,pb=2,mode=normal,nice=273,mf=bt4','-c',str(newrawp)],check=True,stdout=f)
k=bytearray(tmp.read_bytes())
assert k[:5]==bytes.fromhex('5d00008000')
k[5:13]=len(new_raw).to_bytes(8,'little')
new_kernel=bytes(k); final_lz.write_bytes(new_kernel)
ver=WORK/'kernel.final.verify.raw'
with open(ver,'wb') as f: subprocess.run(['xz','--format=lzma','-dc',str(final_lz)],check=True,stdout=f)
assert ver.read_bytes()==new_raw
assert 0x200+len(new_kernel)<=ROOTFS_REL

# Assemble native EC220 firmware payload.
fw=bytearray(b'\xff'*FW_SIZE)
h=bytearray(stock_inner)
h[0x68:0x6c]=(0x80000000).to_bytes(4,'little')
h[0x6c:0x70]=(0x80000000).to_bytes(4,'little')
h[0x70:0x74]=FW_SIZE.to_bytes(4,'little')
h[0x74:0x78]=(0x200).to_bytes(4,'little')
h[0x78:0x7c]=len(new_kernel).to_bytes(4,'little')
h[0x7c:0x80]=ROOTFS_REL.to_bytes(4,'little')
h[0x80:0x84]=align(len(rootfs),0x1000).to_bytes(4,'little')
h[0x84:0x88]=(0).to_bytes(4,'little')
h[0x88:0x8c]=(0).to_bytes(4,'little')
assert h[:4]==bytes.fromhex('03000003') and h[0x40:0x54]==b'\0'*0x14
fw[:0x200]=h
fw[0x200:0x200+len(new_kernel)]=new_kernel
fw[ROOTFS_REL:ROOTFS_REL+len(rootfs)]=rootfs
# JFFS2 EOF at 4KiB and eraseblock (64KiB) alignment after SquashFS.
markers=[]
for a in (0x1000,0x10000):
    p=align(ROOTFS_REL+len(rootfs),a)
    if p+4<FW_SIZE and p not in markers:
        fw[p:p+4]=b'\xde\xad\xc0\xde'; markers.append(p)
OUT_FW.write_bytes(fw)
OUT_TFTP.write_bytes(b'\0'*TFTP_PREFIX+fw)
assert OUT_TFTP.stat().st_size==0x7C0000

# Sysupgrade: exact native 0x7a0000 payload + standard OpenWrt fwtool metadata.
shutil.copy2(OUT_FW,OUT_SYS)
meta={
 'metadata_version':'1.1',
 'compat_version':'1.0',
 'supported_devices':['tplink,ec220-f5-v1'],
 'version':{
   'dist':'OpenWrt','version':'25.12.5','revision':'r33051-f5dae5ece4',
   'target':'ramips/mt76x8','board':'tplink_ec220-f5-v1'
 }
}
metap=W/'ec220_final.meta.json'; metap.write_text(json.dumps(meta,separators=(',',':'))+'\n')
subprocess.run([str(FWTOOL),'-I',str(metap),str(OUT_SYS)],check=True)
# Validate fwtool metadata and stripped payload equality.
meta_out=W/'ec220_final.meta.extracted.json'
subprocess.run([str(FWTOOL),'-q','-i',str(meta_out),str(OUT_SYS)],check=True)
assert json.loads(meta_out.read_text())==meta
stripped=W/'ec220_final.sysupgrade.stripped'
with open(stripped,'wb') as f:
    subprocess.run([str(FWTOOL),'-q','-T','-i','/dev/null',str(OUT_SYS)],check=True,stdout=f)
assert stripped.read_bytes()==bytes(fw)
stripped.unlink(); meta_out.unlink(); metap.unlink()

# Deep final checks
final=OUT_TFTP.read_bytes(); assert final[:TFTP_PREFIX]==b'\0'*TFTP_PREFIX
body=final[TFTP_PREFIX:]; assert body==bytes(fw)
assert body[ROOTFS_REL:ROOTFS_REL+4]==b'hsqs'
assert struct.unpack_from('<Q',body,ROOTFS_REL+40)[0]==len(rootfs)
assert all(body[p:p+4]==b'\xde\xad\xc0\xde' for p in markers)
# final DTB from flashed kernel
x=WORK/'final.extract.lzma'; y=WORK/'final.extract.raw'
x.write_bytes(body[0x200:0x200+len(new_kernel)])
with open(y,'wb') as f: subprocess.run(['xz','--format=lzma','-dc',str(x)],check=True,stdout=f)
fraw=y.read_bytes(); ffdt=FDT.parse(fraw[dtb_off:])
assert ffdt.root.get('compatible').split(b'\0')[:2]==[b'tplink,ec220-f5-v1',b'mediatek,mt7628an-soc']
assert struct.unpack('>I',ffdt.find(flash_path).get('spi-max-frequency'))[0]==40000000

# Report/audit
margin=ROOTFS_REL-(0x200+len(new_kernel))
spare=ROOTFS_PART_SIZE-len(rootfs)
report=f'''TP-Link EC220-F5 v1 — OpenWrt 25.12.5 FINAL native build

STATUS
  Native board identity: tplink,ec220-f5-v1
  OpenWrt: 25.12.5 r33051-f5dae5ece4, ramips/mt76x8
  SPI NOR: 40,000,000 Hz (validated on RC2 hardware tests)
  Kernel/DT hardware state is inherited from the tested RC2 and only board identity/model are changed.
  Rootfs is the tested 25.12.5 RC2 rootfs with native EC220 board.d + sysupgrade support added.

INPUTS
  RC2 TFTP SHA256: {sha_file(RC2)}
  Stock TFTP SHA256: {sha_file(STOCK)}
  Final rootfs SquashFS SHA256: {sha_file(ROOTFS)}
  Final rootfs bytes_used: {len(rootfs)} (0x{len(rootfs):X})

NATIVE IDENTITY
  model: TP-Link EC220-F5 v1
  compatible: tplink,ec220-f5-v1; mediatek,mt7628an-soc
  expected board_name: tplink,ec220-f5-v1

FLASH LAYOUT
  boot    0x000000..0x01FFFF  size 0x020000 read-only
  kernel  0x020000..0x22FFFF  size 0x210000
  rootfs  0x230000..0x7BFFFF  size 0x590000
  config  0x7C0000..0x7CFFFF  size 0x010000
  rom     0x7D0000..0x7DFFFF  size 0x010000
  romfile 0x7E0000..0x7EFFFF  size 0x010000
  radio   0x7F0000..0x7FFFFF  size 0x010000

NVMEM
  MAC: rom + 0xF100, size 6
  2.4 GHz EEPROM: radio + 0x0000, size 0x400
  5 GHz EEPROM: radio + 0x8000, size 0x4DA8

KERNEL
  RC2 compressed kernel: {len(kernel_lzma)} bytes SHA256 {sha256(kernel_lzma)}
  FINAL compressed kernel: {len(new_kernel)} bytes SHA256 {sha256(new_kernel)}
  LZMA properties: {new_kernel[:5].hex()} (dict 8 MiB, lc=3, lp=0, pb=2)
  compressed-kernel margin before fixed rootfs: 0x{margin:X} ({margin} bytes)
  appended DTB offset: 0x{dtb_off:X}

ROOTFS
  SquashFS bytes_used: {len(rootfs)} (0x{len(rootfs):X})
  rootfs partition spare before JFFS2 overlay use: {spare} bytes (~{spare/1024/1024:.2f} MiB)
  JFFS EOF markers, firmware-relative: {', '.join(f'0x{x:X}' for x in markers)}
  Native userspace additions: board.d LAN/WAN + LEDs, EC220 platform sysupgrade, ASU auto-check suppression if package exists.

OUTPUTS
  TFTP recovery/install:
    {OUT_TFTP.name}
    size {OUT_TFTP.stat().st_size} (0x{OUT_TFTP.stat().st_size:X})
    SHA256 {sha_file(OUT_TFTP)}
  Native sysupgrade (use only after FINAL/native EC220 is already booted):
    {OUT_SYS.name}
    size {OUT_SYS.stat().st_size}
    SHA256 {sha_file(OUT_SYS)}
    fwtool supported_devices: tplink,ec220-f5-v1
  Raw native firmware payload (build/recovery artifact; do not flash manually):
    {OUT_FW.name}
    size {OUT_FW.stat().st_size} (0x{OUT_FW.stat().st_size:X})
    SHA256 {sha_file(OUT_FW)}

UPGRADE DESIGN
  Initial RC2 -> FINAL transition MUST use EC220 TFTP recovery, because RC2 reports board_name tplink,archer-c50-v6.
  After FINAL boots, normal sysupgrade image validation matches tplink,ec220-f5-v1.
  EC220 sysupgrade writes exactly 33 x 64KiB blocks to kernel and 89 x 64KiB blocks to rootfs; fwtool metadata is outside those blocks and is never written.
  With config preservation, mtd -j injects sysupgrade.tgz at the 64KiB-aligned JFFS EOF marker in rootfs.

SAFETY BOUNDARIES
  TFTP image is exactly 0x7C0000 = 0x20000 ignored prefix + 0x7A0000 firmware payload.
  Known EC220 U-Boot recovery command writes only flash 0x020000..0x7BFFFF.
  U-Boot 0x000000..0x01FFFF and per-device config/rom/romfile/radio 0x7C0000..0x7FFFFF are not contained in the TFTP write payload.
  Stock recovery remains the fallback.
'''
OUT_REPORT.write_text(report)

aud=['EC220-F5 v1 OpenWrt 25.12.5 FINAL DTB AUDIT','',
     'Root identity:',
     '  model = "TP-Link EC220-F5 v1"',
     '  compatible = "tplink,ec220-f5-v1", "mediatek,mt7628an-soc"',
     '  board_name expected = tplink,ec220-f5-v1',
     '  spi-max-frequency = 40000000 Hz','',
     'Fixed flash partitions:']
for name,label,start,size in expected:
    aud.append(f'  {name:20s} label={label:8s} start=0x{start:06X} size=0x{size:06X} end=0x{start+size:06X}')
aud += ['', 'NVMEM:', '  MAC rom+0xF100 size=6', '  2.4GHz radio+0x0000 size=0x400', '  5GHz radio+0x8000 size=0x4DA8', '',
        f'RC2 appended DTB: offset 0x{dtb_off:X}, size 0x{old_dtb_len:X}',
        f'FINAL appended DTB: offset 0x{dtb_off:X}, size 0x{len(new_dtb):X}']
OUT_AUDIT.write_text('\n'.join(aud)+'\n')

files=[OUT_TFTP,OUT_SYS,OUT_FW,OUT_REPORT,OUT_AUDIT,Path(__file__)]
OUT_SUMS.write_text(''.join(f'{sha_file(p)}  {p.name}\n' for p in files))
print(report)
print('SHA256SUMS:\n'+OUT_SUMS.read_text())
