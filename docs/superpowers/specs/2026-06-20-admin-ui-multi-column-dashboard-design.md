# Multi-Column Dashboard — Admin UI ปรับใหม่

## ที่มา

Admin UI เดิมมี sidebar ทางซ้าย 3 ปุ่ม (Providers, Model Config, Messaging) ให้กดสลับไปมา
ทำให้ "ใช้งานยาก" เพราะอยากเห็นพร็อพเพอร์ตี้ทั้ง 3 กลุ่มพร้อมกัน ไม่ต้องสลับหน้ากลับไปกลับมา

## สิ่งที่จะเปลี่ยน

### 1. Layout

**จาก:** `.app-shell { grid-template-columns: 268px minmax(0, 1fr) }` + 3 views ที่ `hidden` สลับกัน
**เป็น:** layout ที่เอาทุกอย่างมาแสดงบนหน้าเดียว ใช้ CSS grid จัด 3 columns

```
┌─ Top Bar (brand ฝั่งซ้าย + โลโก้ FC) ────────┐
├──────────────────────────────────────────────┤
│ Provider Status Cards (full-width, เท่าเดิม)  │
├────────────┬────────────────┬────────────────┤
│ PROVIDERS  │ MODEL CONFIG   │ MESSAGING      │
│ · Providers│ · Models       │ · Platform     │
│ · Runtime  │ · Thinking     │ · Voice        │
│            │ · Web Tools    │                │
├────────────┴────────────────┴────────────────┤
│ Action Bar (เท่าเดิม)                        │
└──────────────────────────────────────────────┘
```

### 2. HTML changes (`index.html`)

- เปลี่ยน `<aside class="sidebar">` + topbar (`<header class="topbar">`) → `<header class="topbar compact">`
- เอา `<nav id="sectionNav">` ออก (ไม่ต้อง sidebar nav แล้ว)
- เปิด `hidden` ของทุก admin-view (`view-model_config`, `view-messaging`) → ไม่มี hidden แล้ว
- เอา `<h2 id="pageTitle">` ออก (ไม่ต้องเปลี่ยน title เพราะไม่มี view switching)
- topbar ใหม่มี brand ฝั่งซ้าย + "Admin" หรือ subtitle

### 3. CSS changes (`admin.css`)

- `.app-shell`: เปลี่ยนจาก 2-col grid → 1-col (sidebar หาย)
- `.sidebar` → เอาออก, `.topbar` → compact layout
- `.admin-views`: จาก `display: grid; gap: 18px` → `display: grid; grid-template-columns: repeat(3, 1fr)`
- `.admin-view`: เอา `[hidden] { display: none }` ออก
- responsive breakpoints:
  - `≥ 1100px`: 3 columns
  - `700px - 1100px`: 2 columns (column แรกกินพื้นที่ `2fr`, column 2-3 เป็น `1fr`)
  - `< 700px`: 1 column
- `.action-bar`: เปลี่ยน `left: 268px` → `left: 0` (sidebar หาย)
- Provider strip: ปรับ padding ให้เข้ากับ layout ใหม่

### 4. JS changes (`admin.js`)

- **ลบ:** `renderNav()`, `setActiveView()`, `VIEW_GROUPS`, `state.activeView`
- **เปลี่ยน:** `load()` → ไม่เรียก `renderNav()` ไม่ต้อง `setActiveView()`
- **คงไว้:** `renderProviders()`, `renderSections()`, field logic, validate/apply, provider test, dirty state
- `renderSections()`: ไม่ต้อง filter ตาม VIEW_GROUPS แล้ว — render ทุก section ที่ backend ส่งมา
  หรือถ้าจะคง VIEW_GROUPS logic ไว้, render แต่ละ group เป็น column แทน

### 5. สิ่งที่ไม่เปลี่ยน

| ส่วน | คงเดิม |
|------|--------|
| Backend (`admin_config.py`, `admin_routes.py`) | Zero touch |
| Field rendering (`renderField`, `inputForField`) | Zero touch |
| Provider cards (`renderProviders`, `testProvider`) | Zero touch |
| Validate + Apply logic | Zero touch |
| Dirty state | Zero touch |
| Advanced toggle | Zero touch |

## Responsive

| Breakpoint | Columns | Note |
|------------|---------|------|
| ≥ 1100px | 3 | แต่ละ column กว้าง `1fr` เท่ากัน |
| 700-1100px | 2 | Providers column กิน `2fr`, model+messaging ไป column 2 |
| < 700px | 1 | stack แนวตั้งทั้งหมด |

## Verification

1. เปิด `/admin` → ต้องเห็นทุก settings section พร้อมกันโดยไม่ต้องกดสลับ
2. Provider strip, settings sections, action bar ทำงานปกติ
3. Validate + Apply ใช้งานได้เหมือนเดิม
4. responsive: resize browser ดู 3 ขนาดจอ
5. Mobile (< 700px): ทุกอย่าง stack แนวตั้ง ใช้งานได้

## ไฟล์ที่เปลี่ยน

- `api/admin_static/index.html`
- `api/admin_static/admin.css`
- `api/admin_static/admin.js`

(3 ไฟล์, ไม่แตะ backend)
