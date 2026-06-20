# Admin UI Redesign — Modern & Minimal

**Date:** 2026-06-20
**Status:** Approved for implementation
**Approach:** Clean Architecture (restructured HTML layout + CSS rewrite + JS sidebar)

## Motivation

The current admin UI works but feels heavy — card backgrounds, thick borders, warm brown tones, no navigational structure. A redesign to a modern, minimal visual language (Linear/Vercel + Apple-style) improves scanning, reduces visual noise, and adds a sidebar navigation for quick section access.

## Scope

All changes are confined to `api/admin_static/` — three files:

- `index.html` — layout restructure (add sidebar `<nav>`, adjust main)
- `admin.css` — rewrite ~70% (design tokens, sidebar, form refinements, responsive)
- `admin.js` — add ~80 lines (search filter, scroll spy, active nav tracking)

No new files. No new dependencies. No dashboard charts/KPIs.

## Layout

```
┌──────────┬──────────────────────────────────────────┐
│ SIDEBAR  │  MAIN CONTENT                            │
│ 240px    │  1fr                                      │
│ sticky   │  overflow-y: auto                         │
│ 100vh    │  padding: 32px 40px                       │
├──────────┼──────────────────────────────────────────┤
│          │  Provider Grid (minimal cards)            │
│ 🔍 ค้นหา  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│          │  │ NIM  │ │ DS   │ │ OLL  │ │ ...  │   │
│          │  └──────┘ └──────┘ └──────┘ └──────┘   │
│ ⚙️ Config │                                          │
│  ├─ Provi│  ───────────────────────────────────────  │
│  └─ Runt│  Providers Section                         │
│ 🖥️ Models│  field │ field │ field                    │
│  ├─ Mode│  field │ field                             │
│  ├─ Thin│                                          │
│  └─ Web │  ───────────────────────────────────────  │
│ 💬 Messag│  Models Section                           │
│  ├─ Mess│  ...                                      │
│  └─ Voic│                                          │
│ 🛠️ Diag. │  [Validate] [Apply]                       │
│  ├─ Diag │  (fixed bottom)                          │
│  └─ Smok │                                          │
└──────────┴──────────────────────────────────────────┘
```

- Sidebar: `position: sticky; top: 0; height: 100vh; overflow-y: auto`
- Layout divider: `border-right: 1px solid var(--line)` on sidebar
- Main: normal flow, embedded in a CSS Grid row with sidebar

## Sidebar Navigation

**Groups** (collapsible via `<details>/<summary>`):

| Group | Sections | Icon |
|---|---|---|
| Configuration | providers, runtime | ⚙️ |
| Models | models, thinking, web_tools | 🖥️ |
| Messaging | messaging, voice | 💬 |
| Diagnostics | diagnostics, smoke | 🛠️ |

- Nav items: `13px`, `font-weight: 500`, `color: var(--muted)`, `padding: 6px 12px`, `border-radius: 6px`
- Active nav: `color: var(--accent)`, `background: rgba(47,185,132,0.08)`
- Hover: `color: var(--text)`, `background: rgba(255,255,255,0.04)`
- Click → `element.scrollIntoView({ behavior: 'smooth' })` + set active class
- Group header: `11px`, `700 weight`, `color: var(--muted)`, uppercase
- Search (top of sidebar): narrow input with 🔍 icon, `border-radius: 6px`

**Search behavior:**
- Filters sidebar nav items to matching sections
- Scrolls to first matching section on Enter/selection
- Clears on Escape
- "No results" text when empty

## Visual Design Tokens

### Color Palette

| Token | Old | New | Rationale |
|---|---|---|---|
| `--bg` | `#11100e` | `#0c0c0d` | Cooler, deeper base |
| `--panel` | `#1a1815` | `#111113` | Near-black elevation |
| `--line` | `#373129` | `#1f1f23` | Much thinner separation |
| `--line-strong` | `#4d4439` | `#2b2b30` | Slightly stronger |
| `--text` | `#f3eee7` | Keep | Already good |
| `--muted` | `#aaa197` | `#8b8b95` | Cooler gray |
| `--accent` | `#2fb984` | Keep | Brand green stays |
| `--input` | `#12110f` | Remove | Transparent inputs |

### Typography

| Element | Size | Weight | Color |
|---|---|---|---|
| Section heading | 15px | 700 | `--text` |
| Section description | 12px | 400 | `--muted` |
| Field label | 13px | 600 | `--text` |
| Field source/badge | 11px | 500 | `--muted` |
| Provider card name | 14px | 600 | `--text` |
| Provider card meta | 12px | 400 | `--muted` |
| Sidebar nav item | 13px | 500 | `--muted` |
| Sidebar active | 13px | 600 | `--accent` |
| Sidebar group header | 11px | 700 | `--muted` |

Line heights: `1.5` body, `1.3` headings.

### Spacing

- Main content padding: `32px 40px`
- Section gap (vertical + after separator): `28px`
- Field gap (vertical): `8px`
- Field-to-field gap within section: `14px`
- Provider card padding: `10px 12px`
- Sidebar padding: `20px 14px`
- Action bar padding: `12px 28px`

### Borders & Radius

- Section separator: `1px solid var(--line)`
- Input/select/textarea: `1px solid var(--line-strong)`, `border-radius: 6px`, `background: transparent`
- Input focus: `border-color: var(--accent)`, `outline: none`
- Buttons: `border-radius: 8px`
- Provider cards: `1px solid var(--line)`, `border-radius: 8px`, no background
- Status pills: `border-radius: 999px`, semi-transparent colored bg
- Sidebar nav item: `border-radius: 6px`

## Component Changes

### Provider Cards

```
Old: bg: --card, thick border, large min-height
New: no background, 1px solid var(--line), compact (min-height: auto)
     thinner status pill, font-weight adjustments
```

### Form Sections

```
Old: border + bg: --panel + title + fields + advanced toggle
New: border-bottom separator only, no background, no full border
     heading: thin underline, fields flow directly below
     invisible section grouping — just visual rhythm via spacing
```

### Action Bar

```
Old: fixed bottom, config path text, Validate + Apply
New: fixed bottom (same), thinner border-top, remove configPath
     message centering, disabled button more subtle
```

### Mobile (≤768px)

- Sidebar collapses to slide-in drawer with backdrop overlay
- New mini topbar: `brand-mark (FC) + hamburger (☰)`
- Drawer: same sidebar content, `width: 300px`, `transform: translateX(-100%) → 0`
- Overlay: semi-transparent, click to close
- Search input: full width in drawer
- Main: `padding: 24px 18px`

## JavaScript Changes (`admin.js`)

### Add (`~80 lines`)

- **`renderSidebar(sections)`** — builds sidebar nav DOM from section metadata + hardcoded group definitions
  - Creates `<nav>` with brand + search + collapsible groups
  - Each group: `<details>` → `<summary>` (icon + name) → list of `<a>` items
  - Each link: `data-section-id`, click handler for scroll + active state
- **`handleSearch(query)`** — filters nav items, scrolls to first match, "no results" state
- **Scroll spy** — `IntersectionObserver` on each section, updates active nav class
- **Mobile drawer** — toggle class on sidebar, backdrop click to close

### Modify (minor)

- `renderSections` / initialization — call `renderSidebar(sections)` after sections are known
- `load()` — chain `renderSidebar` into the flow

### No change

- `renderField`, `inputForField`, `readFieldValue`, `changedValues`, `updateDirtyState`
- `validate`, `apply`, `testProvider`, `refreshLocalStatus`, `syncModelDatalist`
- `providerName`, `statusClass`, `showMessage`

## CSS Changes (`admin.css`)

### Replace (~70%)

- Token definitions at `:root`
- Grid layout (sidebar + main)
- Sidebar-specific styles (brand, search, nav, details/summary, collapsible, scroll)
- Typography refinements
- Form sections (no-card style)
- Provider cards (no-bg style)
- Action bar (thinner, cleaner)
- Mobile responsive (drawer, topbar)

### Keep (~30%)

- Button base styles
- Status pill variants
- `* { box-sizing }` and font reset
- Field input styles (refined colors kept)
- Transitions/animations

## Edge Cases

| Case | Behavior |
|---|---|
| No search match | "No results" in nav, main content unchanged |
| Section with 0 fields | Hidden from nav + content (preserved existing) |
| Sidebar overflow | `overflow-y: auto`, brand+search sticky-top |
| Long labels | `text-overflow: ellipsis` in nav items |
| Dirty state + nav | No guard — Apply is separate action |
| Ctrl+/ Cmd+/ | Focuses sidebar search input |

## Animations

- `scroll-behavior: smooth` on `html`
- Nav items: `transition: color 150ms, background 150ms`
- Collapsible groups: native `details` open/close with `transition: transform 200ms` on chevron
- Mobile drawer: `transform` transition 250ms ease
- No JS animation libraries

## Files Changed

All within `api/admin_static/`:

- `index.html` — structural layout change (add `<nav>`, remove `<header>` split, adjust container)
- `admin.css` — ~70% rewrite
- `admin.js` — ~80 lines added, minor modifications

No new files. No dependency changes. No backend changes.

## Sequence

Implementation order:
1. `index.html` — new sidebar + main grid structure
2. `admin.css` — design tokens → sidebar → layout → components → responsive
3. `admin.js` — sidebar rendering → search → scroll spy → mobile toggle
4. Visual verification: load page, check layout, test nav/search, test responsive
5. Run `./scripts/ci.sh` to validate no regressions
6. Commit + bump version if production file changed

## Verification

- Load `/admin` — sidebar renders with nav groups, search input works
- Click nav item — smooth scrolls to section, active state updates, no page jump
- Type in search — nav filters, first match scrolls
- Resize to mobile — sidebar becomes drawer with backdrop, hamburger toggle works
- Form fields render correctly, validate/apply buttons work
- Provider cards show status, test buttons functional
- All existing JS behavior (dirty state, apply, restart, model datalist) unchanged
