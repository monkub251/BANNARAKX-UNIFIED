# BANNARAKX UNIFIED

หนึ่งโปรแกรม สองโหมด · One app, two completely separate modes

| ปุ่ม | โหมด | ใช้อะไร |
|---|---|---|
| **UNLIMITED** | ไม้ (bat) | สคริปต์ต้นฉบับ `originals/unlimited/BANNARAKX_ULTIMATE.ps1` รันตามเดิม (`-Auto -NoReboot`) |
| **PRO** | มีด (knife) | ชั้น **SAFE + MAX** ที่เขียนในโปรแกรมนี้ (เฉพาะ Pro) · `BANNARAKX PRO.exe` ต้นฉบับ **ไม่ได้แถมมา** (ใส่เองได้ ดูด้านล่าง) |
| **RESET** | – | เลือกคืนค่าเดิม **ทีละโหมด** |

## วิธีใช้ (ผู้ใช้)
1. เปิด `BANNARAKX_UNIFIED.exe` (ขอสิทธิ์ Admin อัตโนมัติ) — เก็บโฟลเดอร์ `originals` ไว้ข้างกัน exe
2. กดการ์ด **UNLIMITED** หรือ **PRO** → อ่านรายการ → **Apply**
3. เสร็จแล้วรีสตาร์ทเครื่องเอง (โปรแกรมไม่รีสตาร์ทให้)
4. จะกลับค่าเดิม: **RESET** → เลือกโหมด
5. ถ้าอีกโหมดยังเปิดอยู่ โปรแกรมจะขอ Reset โหมดนั้นก่อน เพื่อไม่ให้ค่าทับกัน

## ความปลอดภัย
- ไฟล์ต้นฉบับถูกตรวจ SHA-256 (`originals/MANIFEST.json`) ทุกครั้ง — ถูกแก้ = ไม่รัน
- **ไม่มี** การปิด Defender / Firewall / Windows Update / mitigation ใด ๆ ในโค้ดของโปรแกรมนี้
  (ตัวเลือก `07_OPTIONAL_SECURITY_OFF.reg` ถูกลบออกจากชุด Unlimited แล้ว)
- build นี้ **ไม่มีไฟล์ไบนารีของคนอื่น** (มีแค่ซอร์ส, สคริปต์ Unlimited และรูปโลโก้) — ตัด `BANNARAKX PRO.exe` ออกเพราะ VirusTotal ฟ้อง 2/64
- ถ้าจะใส่ PRO.exe เอง: วางที่ `originals/pro/BANNARAKX PRO.exe` แล้วรัน `python tools/make_manifest.py` (ไม่อยู่ใน manifest = ไม่รัน) ⚠ ตัวนั้นมีตัวเลือก "Security mitigations off" — **อย่ากด**
- ชั้น MAX ทุกค่าถูกสำรองก่อนแก้ → อ่านกลับยืนยัน → Reset คืนค่าแล้วอ่านกลับยืนยันอีกรอบ
  ถ้าคืนไม่ครบ จะ **ไม่รายงานว่าสำเร็จ** และเก็บ backup ไว้ให้ลองใหม่
- Unlimited: การ Reset ยืนยันจากที่สคริปต์ต้นฉบับเก็บ backup เข้าคลัง (`ultimate_backup.restored.*.json`)

## ที่เก็บข้อมูล (แยกกัน)
| โหมด | ไฟล์ |
|---|---|
| Unlimited | `C:\ProgramData\BannarakxNetForge\ultimate_backup.json` (ของสคริปต์ต้นฉบับ — เราอ่านอย่างเดียว) |
| Pro (MAX) | `C:\ProgramData\BannarakxUnified\pro_snapshot.json` |
| Log | `C:\ProgramData\BannarakxUnified\unified.log` |

## Build เป็น .exe (นักพัฒนา)
สร้าง Windows `.exe` ต้อง build บน Windows (หรือ GitHub Actions):
- ดับเบิลคลิก `scripts\BUILD_EXE.bat` → ได้ `dist\BANNARAKX_UNIFIED\BANNARAKX_UNIFIED.exe` + โฟลเดอร์ `originals`
- หรือ push ขึ้น GitHub แล้วดู Actions → artifact `BANNARAKX_UNIFIED` (`.github/workflows/build.yml`)
- รันจากซอร์ส: `scripts\RUN_FROM_SOURCE.bat` · ลองหน้าตาแบบไม่แตะเครื่อง: `python run.py --demo`
- เทสต์: `pip install -r requirements-dev.txt && python -m pytest -q tests`
- ถ้าตั้งใจเปลี่ยนไฟล์ใน `originals/` ให้รัน `python tools/make_manifest.py` เพื่อสร้าง manifest ใหม่

## โครงสร้าง
```
src/bannarakx_unified/
  mode_unlimited.py   รันสคริปต์ต้นฉบับ + ตรวจผลจาก backup ของมัน
  mode_pro.py         ชั้น MAX: snapshot → apply → verify → reset → verify
  tweaks_pro.py       รายการค่าของ Pro (SAFE / MAX) พร้อมเหตุผล และหัวข้อสเปก 4.1–4.9
  regbackend.py power.py integrity.py paths.py common.py services.py
  ui/ theme.py matrix.py widgets.py window.py
originals/unlimited/  สคริปต์ต้นฉบับ (ห้ามแก้) + MANIFEST.json
tests/                15 เทสต์ของตรรกะ apply/reset/แยกโหมด/integrity
```

## แผนที่ฟีเจอร์ 4.1–4.9 → การตั้งค่า (ชั้น Pro)
4.1 ควบคุม/หมุนง่าย: Mouse 1:1, key repeat, foreground priority · 4.2 ลื่นขึ้น: Game Mode, timer, MMCSS ·
4.3 หลบง่าย: Mouse 1:1 · 4.4 ความนิ่งตอนโดนกด: foreground priority · 4.5 คลิกไว: key repeat, no pop-ups, priority ·
4.6 ใช้ของฮีลไว: key repeat, no pop-ups · 4.7 ภาพลื่น: Game DVR off, MMCSS · 4.8 FPS นิ่ง: Game Mode, timer, power plan, network ·
4.9 ความรู้สึกเครื่องแรง: priority, MMCSS, High Performance
ทั้งหมดทำภายในขีดจำกัดของฮาร์ดแวร์จริง ไม่แก้กลไกเกม ไม่แตะไฟล์เกม
