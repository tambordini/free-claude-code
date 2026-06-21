# Admin UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the admin UI with a modern, minimal visual language — sidebar navigation, clean typography, thin borders, no card backgrounds, search, collapsible groups.

**Architecture:** Vanilla HTML/CSS/JS in 3 existing files — `index.html` gets layout restructure (sidebar + main grid), `admin.css` gets ~70% rewrite (new design tokens, sidebar styles, refined components), `admin.js` gets ~80 lines added (sidebar renderer, search, scroll spy, mobile drawer).

**Tech Stack:** Pure HTML/CSS/JS — no frameworks, no build step, no dependencies. Served as static files by FastAPI.

## Global Constraints

- No new files — all changes in `api/admin_static/` only
- No new dependencies — no npm, no CDN, no build tools
- No backend changes — `admin_routes.py`, `admin_config.py` untouched
- Stay vanilla — no frameworks, no TypeScript, no JSX
- Dark theme only — no light mode
- Version bump required if touching production files (current: 2.3.15)
- `./scripts/ci.sh` must pass before commit

---

### Task 1: HTML layout restructure — sidebar + main grid

**Files:**
- Modify: `api/admin_static/index.html` (full rewrite)

**Interfaces:**
- Consumes: Current section ID structure (`providers,runtime,models,thinking,web_tools,messaging,voice,diagnostics,smoke`) preserved in `data-section-ids`
- Produces: DOM with `<nav class="sidebar">`, `<div class="sidebar-overlay">`, `<header class="mobile-topbar">`, `<main>` with sections, `<footer class="action-bar">`

- [ ] **Step 1: Rewrite index.html**

Replace the full content of `api/admin_static/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Free Claude Code Admin</title>
    <link rel="icon" href="data:," />
    <link rel="stylesheet" href="/admin/assets/admin.css" />
  </head>
  <body>
    <div class="app-shell">

      <!-- Sidebar -->
      <nav class="sidebar" id="sidebar">
        <div class="sidebar-top">
          <div class="brand">
            <span class="brand-mark">FC</span>
            <span class="brand-text">Free Claude Code</span>
          </div>
          <div class="sidebar-search">
            <input type="search" id="sidebarSearch" placeholder="Search sections…" spellcheck="false" />
          </div>
        </div>
        <div class="sidebar-nav" id="sidebarNav">
          <!-- Rendered by admin.js -->
        </div>
      </nav>

      <!-- Mobile header -->
      <header class="mobile-topbar">
        <div class="brand">
          <span class="brand-mark">FC</span>
          <span class="brand-text">Free Claude Code</span>
        </div>
        <button class="hamburger" id="hamburgerBtn" type="button" aria-label="Toggle menu">☰</button>
      </header>

      <!-- Overlay for mobile sidebar -->
      <div class="sidebar-overlay" id="sidebarOverlay"></div>

      <!-- Main content -->
      <main class="main">
        <div id="adminViews" class="admin-views">

          <section class="provider-strip" aria-label="Provider status">
            <div class="strip-header">
              <h3>Providers</h3>
            </div>
            <div id="providerGrid" class="provider-grid"></div>
          </section>

          <div id="providersSections" class="form-sections" data-section-ids="providers,runtime" aria-label="Provider configuration"></div>
          <div id="modelConfigSections" class="form-sections" data-section-ids="models,thinking,web_tools" aria-label="Model configuration"></div>
          <div id="messagingSections" class="form-sections" data-section-ids="messaging,voice,diagnostics,smoke" aria-label="Messaging configuration"></div>

        </div>
      </main>

      <!-- Action bar -->
      <footer class="action-bar">
        <div class="action-meta">
          <strong id="dirtyState">No changes</strong>
        </div>
        <div id="messageArea" class="message-area"></div>
        <div class="action-buttons">
          <button id="validateButton" class="secondary-button" type="button">Validate</button>
          <button id="applyButton" class="primary-button" type="button" disabled>Apply</button>
        </div>
      </footer>

    </div>
    <script src="/admin/assets/admin.js"></script>
  </body>
</html>
```

Key changes from current:
- Added `<nav class="sidebar">` with brand + search input + nav container
- Added `<header class="mobile-topbar">` (hidden on desktop, shown on mobile)
- Added `<div class="sidebar-overlay">` for mobile drawer backdrop
- Removed `<div class="brand">` from topbar (moved to sidebar + mobile header)
- Removed `#configPath` span from action bar
- Classes and IDs preserved where referenced by JS (`#dirtyState`, `#messageArea`, `#validateButton`, `#applyButton`, `#providerGrid`, `#adminViews`, section containers)

- [ ] **Step 2: Load page to verify DOM**

Run the server and load `/admin` in the browser. No styles yet — just verify the HTML structure is valid:
- Sidebar element exists
- Mobile topbar element exists
- Section containers exist with correct `data-section-ids`

```bash
# Start the server (ctrl+c to stop)
uv run fcc-server

# Open the page
open http://localhost:9000/admin
```

Expected: page loads but looks unstyled (no CSS yet). Console shows no errors from JS failing to find expected DOM nodes.

---

### Task 2: CSS foundation — design tokens, sidebar, layout

**Files:**
- Modify: `api/admin_static/admin.css` (lines 1-175)

**Interfaces:**
- Consumes: New HTML structure from Task 1 (`.sidebar`, `.mobile-topbar`, `.sidebar-overlay`, `.app-shell` as grid)
- Produces: Dark theme with refined palette, sidebar + main layout grid, sidebar component styles, mobile topbar

- [ ] **Step 1: Replace CSS variables + resets**

Replace the `:root` block and add sidebar/mobile/layout styles at the top of `admin.css`:

```css
:root {
  color-scheme: dark;
  --bg: #0c0c0d;
  --panel: #111113;
  --panel-strong: #19191c;
  --text: #f3eee7;
  --muted: #8b8b95;
  --line: #1f1f23;
  --line-strong: #2b2b30;
  --accent: #2fb984;
  --accent-dark: #24946b;
  --warn: #f5b74f;
  --error: #ff746c;
  --ok: #59d994;
  --info: #7cc7ff;
  --shadow: 0 14px 34px rgba(0, 0, 0, 0.38);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  min-width: 320px;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

button, input, select, textarea { font: inherit; }
```

- [ ] **Step 2: Add app shell grid + sidebar + main layout**

```css
/* ── App Shell ── */

.app-shell {
  display: grid;
  grid-template-columns: 240px 1fr;
  grid-template-rows: 1fr auto;
  min-height: 100vh;
}

/* ── Sidebar ── */

.sidebar {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  border-right: 1px solid var(--line);
  background: var(--bg);
  overflow-y: auto;
}

.sidebar-top {
  padding: 20px 14px 12px;
  border-bottom: 1px solid var(--line);
}

.sidebar-top .brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.brand-mark {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 8px;
  background: var(--accent);
  color: #ffffff;
  font-weight: 800;
  font-size: 13px;
  flex-shrink: 0;
}

.brand-text {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  white-space: nowrap;
}

.sidebar-search input {
  width: 100%;
  min-height: 34px;
  padding: 6px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: transparent;
  color: var(--text);
  font-size: 13px;
  outline: none;
  transition: border-color 150ms;
}

.sidebar-search input:focus {
  border-color: var(--accent);
}

.sidebar-search input::placeholder {
  color: var(--muted);
}

/* ── Sidebar Nav ── */

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  overflow-y: auto;
}

.nav-group {
  margin-bottom: 6px;
}

.nav-group summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  list-style: none;
  user-select: none;
}

.nav-group summary::-webkit-details-marker { display: none; }

.nav-group summary::before {
  content: "▸";
  font-size: 10px;
  transition: transform 200ms;
}

.nav-group[open] summary::before {
  transform: rotate(90deg);
}

.nav-group summary:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.04);
}

.nav-group summary .group-icon {
  font-size: 14px;
  text-transform: none;
  letter-spacing: 0;
}

.nav-item {
  display: block;
  padding: 5px 8px 5px 28px;
  margin: 1px 0;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--muted);
  cursor: pointer;
  text-decoration: none;
  transition: color 150ms, background 150ms;
}

.nav-item:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.04);
}

.nav-item.active {
  color: var(--accent);
  background: rgba(47, 185, 132, 0.08);
  font-weight: 600;
}

/* ── Mobile Topbar ── */

.mobile-topbar {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--bg);
}

.mobile-topbar .brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hamburger {
  background: none;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  padding: 6px 10px;
  color: var(--text);
  font-size: 18px;
  cursor: pointer;
}

/* ── Sidebar Overlay (mobile) ── */

.sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 9;
  background: rgba(0, 0, 0, 0.6);
}

/* ── Main ── */

.main {
  min-width: 0;
  padding: 32px 40px;
  grid-column: 2;
}

.admin-views {
  display: grid;
  gap: 28px;
}
```

- [ ] **Step 3: Load page to verify layout**

```bash
uv run fcc-server
```

Open `/admin`. Verify:
- Sidebar renders on left (240px), brand + search visible
- Main content renders to the right
- No visual glitches at this stage (sections still have old styles, will be refined in Task 3)

- [ ] **Step 4: Commit**

```bash
git add api/admin_static/index.html api/admin_static/admin.css
git commit -m "refactor: restructure admin layout with sidebar + mobile topbar

- Sidebar with brand, search, and nav container
- Mobile topbar (hidden on desktop, shown on mobile)
- Sidebar overlay for mobile drawer backdrop
- Grid layout: sidebar 240px | main 1fr
- Refined dark color palette (cooler slate tones)"
```

---

### Task 3: CSS component refinements

**Files:**
- Modify: `api/admin_static/admin.css` (remaining lines — form sections, provider cards, action bar, responsive)

**Interfaces:**
- Consumes: CSS foundation from Task 2
- Produces: Complete visual overhaul matching the spec

- [ ] **Step 1: Replace form section styles (no-card, thin separators)**

Append after `.admin-views`:

```css
/* ── Provider Strip ── */

.provider-strip {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 16px;
}

.strip-header {
  margin-bottom: 12px;
}

.strip-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

/* ── Provider Card ── */

.provider-card {
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: transparent;
}

.provider-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.provider-title strong {
  font-size: 14px;
  font-weight: 600;
}

.provider-meta {
  color: var(--muted);
  font-size: 12px;
  word-break: break-word;
}

/* ── Status Pills ── */

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px 9px;
  background: var(--panel-strong);
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.status-pill.ok {
  color: var(--ok);
  background: rgba(89, 217, 148, 0.10);
  border-color: rgba(89, 217, 148, 0.30);
}

.status-pill.warn {
  color: var(--warn);
  background: rgba(245, 183, 79, 0.10);
  border-color: rgba(245, 183, 79, 0.30);
}

.status-pill.error {
  color: var(--error);
  background: rgba(255, 116, 108, 0.10);
  border-color: rgba(255, 116, 108, 0.30);
}

/* ── Buttons ── */

.test-button,
.ghost-button,
.secondary-button,
.primary-button {
  min-height: 34px;
  border-radius: 8px;
  border: 1px solid var(--line-strong);
  padding: 7px 12px;
  cursor: pointer;
  font-weight: 700;
  font-size: 13px;
  transition: border-color 150ms, background 150ms;
}

.ghost-button,
.secondary-button,
.test-button {
  background: var(--panel-strong);
  color: var(--text);
}

.ghost-button:hover,
.secondary-button:hover,
.test-button:hover {
  border-color: var(--accent);
}

.primary-button {
  border-color: var(--accent);
  background: var(--accent);
  color: #06100b;
}

.primary-button:hover {
  background: var(--accent-dark);
}

.primary-button:disabled {
  cursor: not-allowed;
  border-color: var(--line);
  background: #2b2825;
  color: #6b635a;
}

/* ── Form Sections ── */

.form-sections > * + * {
  padding-top: 24px;
  border-top: 1px solid var(--line);
}

.settings-section {
  scroll-margin-top: 20px;
}

.section-heading {
  margin-bottom: 16px;
}

.section-heading h3 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 700;
}

.section-heading p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

.field {
  display: grid;
  gap: 7px;
  align-content: start;
}

.field label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
}

.field-source {
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
}

.field input,
.field select,
.field textarea {
  width: 100%;
  min-height: 38px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: transparent;
  color: var(--text);
  padding: 8px 10px;
  font-size: 13px;
  outline: none;
  transition: border-color 150ms;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
  border-color: var(--accent);
}

.field textarea {
  min-height: 90px;
  resize: vertical;
}

.field input:disabled,
.field select:disabled,
.field textarea:disabled {
  background: #1a1a1d;
  color: #6b635a;
}

.field-description {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.4;
}

.field.advanced-field {
  display: none;
}

.settings-section.show-advanced .advanced-field {
  display: grid;
}

.advanced-toggle {
  justify-self: start;
  margin-top: 14px;
}
```

- [ ] **Step 2: Add action bar + responsive styles**

```css
/* ── Action Bar ── */

.action-bar {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 64px;
  border-top: 1px solid var(--line);
  background: rgba(12, 12, 13, 0.94);
  padding: 12px 28px;
  backdrop-filter: blur(12px);
  grid-column: 1 / -1;
}

.action-meta {
  flex: 1;
  min-width: 0;
}

.action-meta strong {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.message-area {
  min-width: 0;
  color: var(--muted);
  font-size: 13px;
}

.message-area.error { color: var(--error); }
.message-area.ok { color: var(--ok); }

.action-buttons {
  display: flex;
  gap: 8px;
}

/* ── Responsive ── */

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 10;
    transform: translateX(-100%);
    transition: transform 250ms ease;
    width: 280px;
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .sidebar-overlay.open {
    display: block;
  }

  .mobile-topbar {
    display: flex;
  }

  .main {
    grid-column: 1 / -1;
    padding: 24px 18px;
  }

  .action-bar {
    padding: 12px 18px;
    flex-wrap: wrap;
  }

  .action-buttons {
    flex: 1;
  }

  .action-buttons button {
    flex: 1;
  }
}
```

- [ ] **Step 3: Load page to verify components**

Open `/admin`. Verify:
- Provider cards have thin borders, no background, compact
- Form sections have only border-top separator (no card bg, no full border)
- Inputs get accent border on focus
- Action bar is thinner, no config path text
- Pill badges are compact
- Resize to mobile → sidebar slides away, mobile topbar appears, content full-width

- [ ] **Step 4: Commit**

```bash
git add api/admin_static/admin.css
git commit -m "refactor: refine admin UI components — no-card sections, thin borders
- Form sections: border-top separator instead of card backgrounds
- Provider cards: transparent bg, compact padding
- Inputs: transparent bg, focus ring accent border
- Status pills: tighter padding, softer colors
- Action bar: thinner, flex layout
- Responsive: sidebar drawer on ≤768px with overlay"
```

---

### Task 4: JavaScript sidebar rendering + navigation + search + scroll spy + mobile toggle

**Files:**
- Modify: `api/admin_static/admin.js`

**Interfaces:**
- Consumes: DOM elements from Task 1, CSS classes from Task 2-3
- Produces: `renderSidebar()` called from `load()`, search filtering, smooth scroll navigation, scroll spy active tracking, mobile drawer toggle

- [ ] **Step 1: Add NAV_GROUPS constant and renderSidebar function**

After `const MASKED_SECRET = "********";` in `admin.js`, add:

```js
const NAV_GROUPS = [
  { label: "Configuration", icon: "⚙️", sections: ["providers", "runtime"] },
  { label: "Models",        icon: "🖥️", sections: ["models", "thinking", "web_tools"] },
  { label: "Messaging",     icon: "💬", sections: ["messaging", "voice"] },
  { label: "Diagnostics",   icon: "🛠️", sections: ["diagnostics", "smoke"] },
];
```

Replace the `byId` reference with:

```js
const byId = (id) => document.getElementById(id);
```

Then after `renderSections` function, add:

```js
function renderSidebar(sections) {
  const nav = byId("sidebarNav");
  nav.innerHTML = "";

  NAV_GROUPS.forEach((group) => {
    const groupSections = group.sections
      .map((id) => sections.find((s) => s.id === id))
      .filter(Boolean);
    if (groupSections.length === 0) return;

    const details = document.createElement("details");
    details.className = "nav-group";
    details.open = true;

    const summary = document.createElement("summary");
    const icon = document.createElement("span");
    icon.className = "group-icon";
    icon.textContent = group.icon;
    summary.appendChild(icon);
    summary.append(group.label);
    details.appendChild(summary);

    groupSections.forEach((section) => {
      const a = document.createElement("a");
      a.className = "nav-item";
      a.href = `#section-${section.id}`;
      a.dataset.sectionId = section.id;
      a.textContent = section.label;
      a.addEventListener("click", (e) => {
        e.preventDefault();
        const target = byId(`section-${section.id}`);
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
          setActiveNav(section.id);
        }
        // Close mobile drawer on nav click
        closeSidebar();
      });
      details.appendChild(a);
    });

    nav.appendChild(details);
  });
}
```

- [ ] **Step 2: Add setActiveNav, closeSidebar, search handler functions**

After `renderSidebar`, add:

```js
function setActiveNav(sectionId) {
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.sectionId === sectionId);
  });
}

function closeSidebar() {
  byId("sidebar").classList.remove("open");
  byId("sidebarOverlay").classList.remove("open");
}

function openSidebar() {
  byId("sidebar").classList.add("open");
  byId("sidebarOverlay").classList.add("open");
}
```

- [ ] **Step 3: Add IntersectionObserver for scroll spy**

Add after `closeSidebar`:

```js
function setupScrollSpy() {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const sectionId = entry.target.id.replace("section-", "");
          setActiveNav(sectionId);
        }
      });
    },
    { rootMargin: "-20% 0px -70% 0px" }
  );

  document.querySelectorAll("[id^='section-']").forEach((el) => observer.observe(el));
}
```

- [ ] **Step 4: Add search handler**

```js
function setupSearch() {
  const input = byId("sidebarSearch");
  if (!input) return;

  input.addEventListener("input", () => {
    const query = input.value.trim().toLowerCase();
    document.querySelectorAll(".nav-item").forEach((item) => {
      const match = !query || item.textContent.toLowerCase().includes(query);
      item.style.display = match ? "" : "none";
      if (match && query) {
        item.classList.add("active");
        item.scrollIntoView({ behavior: "smooth", block: "center" });
      } else if (!query) {
        item.classList.remove("active");
      }
    });
    // Show/hide groups based on visible children
    document.querySelectorAll(".nav-group").forEach((group) => {
      const visible = Array.from(group.querySelectorAll(".nav-item")).some(
        (item) => item.style.display !== "none"
      );
      group.style.display = visible || !query ? "" : "none";
    });
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      input.value = "";
      input.dispatchEvent(new Event("input"));
      input.blur();
    }
  });
}
```

- [ ] **Step 5: Wire up mobile toggle + integrate into load()**

Add mobile toggle handlers (before `load()`):

```js
function setupMobileToggle() {
  byId("hamburgerBtn")?.addEventListener("click", openSidebar);
  byId("sidebarOverlay")?.addEventListener("click", closeSidebar);
  // Close sidebar on Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSidebar();
  });
}
```

Then modify `load()` — after `renderProviders` and `renderSections`:

```js
async function load() {
  showMessage("Loading admin config");
  const config = await api("/admin/api/config");
  state.config = config;
  state.fields = new Map(config.fields.map((field) => [field.key, field]));
  renderProviders(config.provider_status);
  renderSections(config.sections, config.fields);
  renderSidebar(config.sections);               // ← ADD
  setupScrollSpy();                              // ← ADD
  setupSearch();                                 // ← ADD
  setupMobileToggle();                           // ← ADD
  // byId("configPath").textContent = ...        // ← REMOVE this line
  await validate(false);
  await refreshLocalStatus();
  try {
    const status = await api("/admin/api/status");
    const cachedModels = status.cached_models || {};
    state.modelOptions = Object.entries(cachedModels)
      .flatMap(([providerId, models]) => models.map(model => `${providerId}/${model}`))
      .sort();
    syncModelDatalist();
  } catch (e) {
    // status endpoint unavailable — datalist stays empty
  }
  updateDirtyState();
  showMessage("");
}
```

- [ ] **Step 6: Load page to verify all JS features**

Open `/admin`. Verify:
- Sidebar shows 4 collapsible groups (Config, Models, Messaging, Diagnostics)
- Clicking a nav item smooth-scrolls to the section
- Scrolling updates the active nav item
- Search input filters nav items, "No results" state works
- Escape clears search
- On mobile (≤768px): hamburger opens sidebar drawer, overlay appears, clicking overlay closes drawer
- Escape closes mobile drawer
- Existing functionality works: Validate, Apply, dirty state counting, provider test buttons, model datalist

- [ ] **Step 7: Commit**

```bash
git add api/admin_static/admin.js
git commit -m "feat: add sidebar rendering, search, scroll spy, mobile drawer
- NAV_GROUPS define collapsible sidebar structure
- renderSidebar builds nav from section metadata
- IntersectionObserver scroll spy tracks active section
- Search input filters nav items with live matching
- Mobile drawer open/close with overlay + keyboard dismissal"
```

---

### Task 5: CI check + version bump + commit

**Files:**
- Modify: `pyproject.toml` (version bump 2.3.15 → 2.3.16)

- [ ] **Step 1: Bump version in pyproject.toml**

Run:
```bash
uv run python -c "
import re, sys
p = open('pyproject.toml').read()
old = re.search(r'version = \"(\\d+\\.\\d+\\.\\d+)\"', p).group(1)
parts = list(map(int, old.split('.')))
parts[2] += 1
new = '.'.join(map(str, parts))
p = p.replace(f'version = \"{old}\"', f'version = \"{new}\"')
open('pyproject.toml', 'w').write(p)
print(f'{old} → {new}')
"
```

- [ ] **Step 2: Update lockfile**

```bash
uv lock
```

- [ ] **Step 3: Run CI**

```bash
./scripts/ci.sh
```

Expected: all checks pass (ruff format, ruff check, mypy/ty, pytest).

If a test fails, investigate and fix before committing.

- [ ] **Step 4: Commit version bump with production changes**

```bash
git add pyproject.toml uv.lock
git commit -m "bump 2.3.15 → 2.3.16 for admin UI redesign"
```

- [ ] **Step 5: Amend or squash into a combined commit**

Since the version bump must be in the same commit as production file changes, combine all admin UI commits into one or create a final commit that touches production files:

```bash
# Soft reset to before the first admin UI commit, then recommit everything together
git reset --soft HEAD~4  # adjust count as needed
git commit -m "refactor: redesign admin UI with modern minimal visual language

- Sidebar navigation with collapsible groups and search
- Refined dark palette (cooler slate tones, thin borders)
- No-card form sections with thin border separators
- Reduced provider card footprint (transparent bg)
- Mobile drawer sidebar with overlay backdrop
- Scroll spy active tracking + smooth scroll nav
- bump 2.3.15 → 2.3.16"
```

Or keep individual commits and add one final commit that includes pyproject.toml + uv.lock:

```bash
git commit -m "bump 2.3.15 → 2.3.16 for admin UI redesign"
```
