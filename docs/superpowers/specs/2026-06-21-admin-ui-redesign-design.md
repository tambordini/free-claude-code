# Admin UI Redesign

## Goal
Replace vanilla JS/CSS admin frontend with Tailwind CSS v4 + Alpine.js v3 for a more polished, responsive, and user-friendly interface.

## Files Changed
- `api/admin_static/index.html` — restructure layout, add CDN scripts, Alpine x-data/x-for
- `api/admin_static/admin.js` — convert to Alpine components, reactive form state
- `api/admin_static/admin.css` — **removed**, replaced by Tailwind utility classes

## Architecture

### CDN (no build step)
- Tailwind CSS v4: `<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>`
- Alpine.js v3: `<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>`

### Layout
```
app-shell (grid: sidebar | main)
├── sidebar (sticky, mobile drawer)
│   ├── brand + search
│   └── nav groups (collapsible details)
├── mobile-topbar (hidden on desktop)
├── main
│   ├── model-routing section (full-width, top)
│   ├── provider-strip (cards grid)
│   ├── remaining form sections
│   └── action-bar (sticky bottom)
└── toast (fixed top-right)
```

### Component Map
| Vanilla Feature | Alpine Replacement |
|---|---|
| `renderSections()` | `x-for` over config sections |
| `changedValues()` | Alpine `$watch` / x-model |
| `showMessage()` | Alpine `x-data` toast state |
| `renderField()` | `x-for` over fields with type switch |
| `updateDirtyState()` | computed via Alpine `$watch` |
| `setupSearch()` | Alpine `x-model` + filter |
| `setupScrollSpy()` | Alpine `IntersectionObserver` |
| `setupMobileToggle()` | Alpine `x-show` / class toggle |

### Form Input Overhauls
| Field Type | Before | After |
|---|---|---|
| model selector | plain `<input>` | autocomplete dropdown (Alpine) |
| boolean | plain checkbox | toggle switch (Tailwind styled) |
| secret | `<input type="password">` | + show/hide button |
| tri-boolean | plain `<select>` | styled select |
| loading | n/a | skeleton pulse animation |

### State Management
- Single Alpine `adminUi()` function (like the mockup's pattern)
- `state.config` — loaded from `/admin/api/config`
- `state.fields` — Map of field key → field spec
- `state.toast` — { show, message, type }

## Verification
1. Load `/admin` page — all sections render correctly
2. Form inputs work: model search, password toggle, tri-boolean, toggle switch
3. Validate/Apply buttons call correct API endpoints
4. Mobile responsive: sidebar drawers, hamburger menu
5. No console errors
