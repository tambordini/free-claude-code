# Multi-Column Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เปลี่ยน Admin UI จาก sidebar-switching views → หน้าเดียวที่เห็นทั้ง 3 groups (Providers, Model Config, Messaging) ใน multi-column layout แบบ responsive

**Architecture:** แก้ไขเฉพาะ frontend 3 ไฟล์ (`index.html`, `admin.css`, `admin.js`) ไม่แตะ backend เลย ใช้ CSS grid จัด columns, เอา view-switching logic ทิ้ง

**Tech Stack:** Vanilla JS, CSS Grid, ไม่มี dependencies เพิ่ม

## Global Constraints

- ไม่ต้องแตะ backend (`admin_config.py`, `admin_routes.py`)
- ไม่เพิ่ม dependency
- Responsive: 3 cols ≥ 1100px, 2 cols ≥ 700px, 1 col < 700px
- CI checks ทั้งหมดต้องผ่าน (`./scripts/ci.sh`)

---

### Task 1: HTML — ยกเครื่องโครงสร้างหน้า

**Files:**
- Modify: `api/admin_static/index.html`

**Interfaces:**
- Consumes: —
- Produces: โครงสร้าง HTML ใหม่ที่ไม่มี sidebar, ไม่มี view-switching hidden, มี topbar แบบ compact

- [ ] **Step 1: เขียน index.html ใหม่**

เอาส่วนประกอบเก่าออก และใส่โครงสร้างใหม่:

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
      <header class="topbar">
        <div class="brand">
          <div class="brand-mark">FC</div>
          <div>
            <h1>Free Claude Code</h1>
            <p>Server Control</p>
          </div>
        </div>
      </header>

      <main class="main">
        <div id="adminViews" class="admin-views">
          <section class="admin-view" data-view="providers">
            <section class="provider-strip" aria-label="Provider status">
              <div class="strip-header">
                <h3>Providers</h3>
              </div>
              <div id="providerGrid" class="provider-grid"></div>
            </section>
            <div id="providersSections" class="form-sections" aria-label="Provider configuration"></div>
          </section>

          <section class="admin-view" data-view="model_config">
            <div id="modelConfigSections" class="form-sections" aria-label="Model configuration"></div>
          </section>

          <section class="admin-view" data-view="messaging">
            <div id="messagingSections" class="form-sections" aria-label="Messaging configuration"></div>
          </section>
        </div>
      </main>

      <footer class="action-bar">
        <div class="action-meta">
          <strong id="dirtyState">No changes</strong>
          <span id="configPath"></span>
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

**สิ่งที่เปลี่ยน:**
- `<aside class="sidebar">` + `<nav id="sectionNav">` → ถูกเอาออก
- `<header class="topbar">` → กลายเป็น topbar ตัวเดียวที่มี brand (ย้ายมาจาก sidebar)
- `<h2 id="pageTitle">` ถูกเอาออก (ไม่มี view switching)
- ทุก `admin-view` section ไม่มี `hidden` attribute และไม่มี `id="view-*"` (ใช้ class + data-view แทน)
- เอา `class="active"` ออกจาก admin-view (ไม่ต้องมี active state)

- [ ] **Step 2: Commit**

```bash
git add api/admin_static/index.html
git commit -m "refactor: simplify HTML layout for multi-column dashboard"
```

---

### Task 2: CSS — Grid layout + responsive

**Files:**
- Modify: `api/admin_static/admin.css`

**Interfaces:**
- Consumes: โครงสร้าง HTML จาก Task 1 (`.topbar`, `.admin-view` ไม่มี hidden/active)
- Produces: CSS layout แบบ multi-column responsive

- [ ] **Step 1: เขียน CSS ใหม่ทั้งไฟล์ (ใช้ของเดิมเป็นฐาน)**

```css
:root {
  color-scheme: dark;
  --bg: #11100e;
  --panel: #1a1815;
  --panel-strong: #25211c;
  --card: #201d19;
  --input: #12110f;
  --text: #f3eee7;
  --muted: #aaa197;
  --line: #373129;
  --line-strong: #4d4439;
  --accent: #2fb984;
  --accent-dark: #24946b;
  --warn: #f5b74f;
  --error: #ff746c;
  --ok: #59d994;
  --info: #7cc7ff;
  --shadow: 0 14px 34px rgba(0, 0, 0, 0.38);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  background: var(--bg);
  color: var(--text);
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
  letter-spacing: 0;
}

button,
input,
select,
textarea {
  font: inherit;
}

/* ── App Shell ── */

.app-shell {
  display: grid;
  min-height: 100vh;
  padding-bottom: 86px;
}

/* ── Top Bar ── */

.topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 28px;
  border-bottom: 1px solid var(--line);
  background: #171511;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 8px;
  background: var(--accent);
  color: #ffffff;
  font-weight: 800;
  font-size: 14px;
}

.brand h1,
.brand p {
  margin: 0;
}

.brand h1 {
  font-size: 15px;
  line-height: 1.2;
}

.brand p {
  color: var(--muted);
  font-size: 12px;
}

/* ── Main Content ── */

.main {
  min-width: 0;
  padding: 28px;
}

.admin-views {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
  align-items: start;
}

.admin-view[hidden] {
  display: none;
}

/* ── Provider Strip ── */

.provider-strip,
.settings-section {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  box-shadow: var(--shadow);
}

.provider-strip {
  grid-column: 1 / -1;
  padding: 16px;
}

.strip-header,
.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.strip-header {
  margin-bottom: 12px;
}

.strip-header h3,
.section-heading h3 {
  margin: 0;
  font-size: 16px;
}

.section-heading p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.provider-card {
  display: grid;
  gap: 8px;
  min-height: 108px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: var(--card);
}

.provider-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.provider-title strong {
  font-size: 14px;
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
  min-height: 30px;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 5px 10px;
  background: var(--panel-strong);
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.status-pill.ok {
  color: var(--ok);
  background: rgba(47, 185, 132, 0.13);
  border-color: rgba(89, 217, 148, 0.36);
}

.status-pill.warn {
  color: var(--warn);
  background: rgba(245, 183, 79, 0.13);
  border-color: rgba(245, 183, 79, 0.38);
}

.status-pill.error {
  color: var(--error);
  background: rgba(255, 116, 108, 0.12);
  border-color: rgba(255, 116, 108, 0.36);
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
  background: #34302a;
  color: #797067;
}

/* ── Form Sections ── */

.form-sections {
  display: grid;
  gap: 18px;
}

.settings-section {
  padding: 18px;
  scroll-margin-top: 20px;
}

.section-heading {
  margin-bottom: 16px;
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
  font-weight: 700;
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
  border-radius: 8px;
  background: var(--input);
  color: var(--text);
  padding: 8px 10px;
}

.field textarea {
  min-height: 90px;
  resize: vertical;
}

.field input:disabled,
.field select:disabled,
.field textarea:disabled {
  background: #26231f;
  color: #82796f;
}

.field-description {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.35;
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

/* ── Action Bar ── */

.action-bar {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 10;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, auto) auto;
  gap: 14px;
  align-items: center;
  min-height: 72px;
  border-top: 1px solid var(--line);
  background: rgba(26, 24, 21, 0.94);
  padding: 12px 28px;
  backdrop-filter: blur(12px);
}

.action-meta {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.action-meta strong,
.action-meta span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-area {
  min-width: 0;
  color: var(--muted);
  font-size: 13px;
}

.message-area.error {
  color: var(--error);
}

.message-area.ok {
  color: var(--ok);
}

.action-buttons {
  display: flex;
  gap: 8px;
}

/* ── Responsive ── */

@media (max-width: 1100px) {
  .admin-views {
    grid-template-columns: 2fr 1fr;
  }
  .admin-view:last-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 700px) {
  .admin-views {
    grid-template-columns: 1fr;
  }
  .admin-view:last-child {
    grid-column: auto;
  }

  .topbar {
    padding: 12px 18px;
  }

  .main {
    padding: 18px;
  }

  .action-bar {
    grid-template-columns: 1fr;
    align-items: stretch;
    padding: 12px 18px;
  }

  .action-buttons {
    justify-content: stretch;
  }

  .action-buttons button {
    flex: 1;
  }
}
```

**สิ่งที่เปลี่ยนจากของเดิม:**
- เอา `.sidebar`, `.section-nav`, `.nav-link` ทั้ง block ออก
- `.app-shell` → แก้เป็น `display: grid; min-height: 100vh` ไม่มี `grid-template-columns` (single column)
- `.topbar` → จาก `margin-bottom: 20px` เป็น flexbox layout แบบ top bar มี border-bottom
- `.admin-views` → `grid-template-columns: repeat(3, 1fr)` แทน `display: grid; gap: 18px`
- `.provider-strip` → เพิ่ม `grid-column: 1 / -1`
- `.field-grid` → จาก `grid-template-columns: repeat(auto-fit, minmax(260px, 1fr))` เป็น `1fr` (แต่ละ field กินเต็ม column, responsive ผ่าน multi-column parent แทน)
- `.action-bar` → `left: 0` แทน `left: 268px`
- responsive: ปรับ breakpoints จาก 900px → 1100px + 700px
- ตัด media query `@media (max-width: 900px)` เดิมทิ้ง เขียนใหม่

- [ ] **Step 2: Commit**

```bash
git add api/admin_static/admin.css
git commit -m "refactor: multi-column grid layout with responsive breakpoints"
```

---

### Task 3: JS — เอา view-switching logic ทิ้ง

**Files:**
- Modify: `api/admin_static/admin.js`

**Interfaces:**
- Consumes: HTML structure จาก Task 1 (ไม่มี `#sectionNav`, ไม่มี `#pageTitle`, ทุก view มองเห็นพร้อมกัน)
- Produces: JS ที่ไม่มี view switching, render ทุก section ทันที

- [ ] **Step 1: เขียน admin.js ใหม่โดยตัด view-switching ออก**

```javascript
const state = {
  config: null,
  fields: new Map(),
  localStatus: new Map(),
  modelOptions: [],
};

const MASKED_SECRET = "********";

const byId = (id) => document.getElementById(id);

function sourceLabel(source) {
  const labels = {
    default: "default",
    template: "template",
    repo_env: "repo .env",
    managed_env: "",
    explicit_env_file: "FCC_ENV_FILE",
    process: "process env",
  };
  return Object.prototype.hasOwnProperty.call(labels, source) ? labels[source] : source;
}

function sourceText(field) {
  const parts = [];
  const label = sourceLabel(field.source);
  if (label) {
    parts.push(label);
  }
  if (field.locked) {
    parts.push("locked");
  }
  return parts.join(" ");
}

function providerName(providerId) {
  const names = {
    nvidia_nim: "NVIDIA NIM",
    open_router: "OpenRouter",
    mistral_codestral: "Mistral Codestral",
    deepseek: "DeepSeek",
    lmstudio: "LM Studio",
    llamacpp: "llama.cpp",
    ollama: "Ollama",
    kimi: "Kimi",
    wafer: "Wafer",
    opencode: "OpenCode Zen",
    opencode_go: "OpenCode Go",
    zai: "Z.ai",
  };
  if (names[providerId]) return names[providerId];
  return providerId
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function statusClass(status) {
  if (["configured", "reachable", "running"].includes(status)) return "ok";
  if (["missing_key", "missing_url", "unknown"].includes(status)) return "warn";
  if (["offline", "error"].includes(status)) return "error";
  return "neutral";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function load() {
  showMessage("Loading admin config");
  const config = await api("/admin/api/config");
  state.config = config;
  state.fields = new Map(config.fields.map((field) => [field.key, field]));
  renderProviders(config.provider_status);
  renderSections(config.sections, config.fields);
  byId("configPath").textContent = config.paths.managed;
  await validate(false);
  await refreshLocalStatus();
  // Populate model datalist from server cache (zero provider API calls)
  try {
    const status = await api("/admin/api/status");
    const cachedModels = status.cached_models || {};
    state.modelOptions = Object.entries(cachedModels)
      .flatMap(([providerId, models]) => models.map(model => `${providerId}/${model}`))
      .sort();
    syncModelDatalist();
  } catch (e) {
    // status endpoint unavailable — datalist stays empty, manual refresh works
  }
  updateDirtyState();
  showMessage("");
}

function renderProviders(providerStatus) {
  const grid = byId("providerGrid");
  grid.innerHTML = "";
  providerStatus.forEach((provider) => {
    const card = document.createElement("article");
    card.className = "provider-card";
    card.dataset.provider = provider.provider_id;

    const title = document.createElement("div");
    title.className = "provider-title";
    title.innerHTML = `<strong>${providerName(provider.provider_id)}</strong>`;

    const pill = document.createElement("span");
    pill.className = `status-pill ${statusClass(provider.status)}`;
    pill.textContent = provider.label;
    title.appendChild(pill);

    const meta = document.createElement("div");
    meta.className = "provider-meta";
    meta.textContent =
      provider.kind === "local"
        ? provider.base_url || "No local URL configured"
        : provider.credential_env;

    const button = document.createElement("button");
    button.type = "button";
    button.className = "test-button";
    button.textContent = provider.kind === "local" ? "Test" : "Refresh models";
    button.addEventListener("click", () => testProvider(provider.provider_id, button));

    card.append(title, meta, button);
    grid.appendChild(card);
  });
}

function updateProviderCard(providerId, status, label, metaText) {
  const card = document.querySelector(`[data-provider="${providerId}"]`);
  if (!card) return;
  const pill = card.querySelector(".status-pill");
  pill.className = `status-pill ${statusClass(status)}`;
  pill.textContent = label;
  if (metaText) {
    card.querySelector(".provider-meta").textContent = metaText;
  }
}

// ponytail: sections grouped by container IDs instead of VIEW_GROUPS;
// add/remove container divs in HTML to rebalance
function renderSections(sections, fields) {
  const containerIds = ["providersSections", "modelConfigSections", "messagingSections"];
  containerIds.forEach((id) => {
    byId(id).innerHTML = "";
  });

  const sectionById = new Map(sections.map((section) => [section.id, section]));
  const bySection = new Map();
  sections.forEach((section) => bySection.set(section.id, []));
  fields.forEach((field) => {
    if (!bySection.has(field.section)) bySection.set(field.section, []);
    bySection.get(field.section).push(field);
  });

  // Map sections to their container based on which view group they belong to
  const sectionToContainer = {
    providers: "providersSections",
    runtime: "providersSections",
    models: "modelConfigSections",
    thinking: "modelConfigSections",
    web_tools: "modelConfigSections",
    messaging: "messagingSections",
    voice: "messagingSections",
  };

  sections.forEach((section) => {
    const sectionFields = bySection.get(section.id) || [];
    if (sectionFields.length === 0) return;

    const containerId = sectionToContainer[section.id];
    if (!containerId) return;

    const sectionEl = document.createElement("section");
    sectionEl.className = "settings-section";
    sectionEl.id = `section-${section.id}`;

    const heading = document.createElement("div");
    heading.className = "section-heading";
    heading.innerHTML = `<div><h3>${section.label}</h3><p>${section.description}</p></div>`;
    sectionEl.appendChild(heading);

    const grid = document.createElement("div");
    grid.className = "field-grid";
    sectionFields.forEach((field) => {
      grid.appendChild(renderField(field));
    });
    sectionEl.appendChild(grid);

    if (sectionFields.some((field) => field.advanced)) {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "ghost-button advanced-toggle";
      toggle.textContent = "Show advanced";
      toggle.addEventListener("click", () => {
        const showing = sectionEl.classList.toggle("show-advanced");
        toggle.textContent = showing ? "Hide advanced" : "Show advanced";
      });
      sectionEl.appendChild(toggle);
    }

    byId(containerId).appendChild(sectionEl);
  });
}

function renderField(field) {
  const wrapper = document.createElement("div");
  wrapper.className = `field${field.advanced ? " advanced-field" : ""}`;
  wrapper.dataset.key = field.key;

  const label = document.createElement("label");
  label.htmlFor = `field-${field.key}`;
  const labelText = document.createElement("span");
  labelText.textContent = field.label;
  label.appendChild(labelText);

  const source = sourceText(field);
  if (source) {
    const sourceEl = document.createElement("span");
    sourceEl.className = "field-source";
    sourceEl.textContent = source;
    label.appendChild(sourceEl);
  }

  const input = inputForField(field);
  input.id = `field-${field.key}`;
  input.dataset.key = field.key;
  input.dataset.original = field.value || "";
  input.dataset.secret = field.secret ? "true" : "false";
  input.dataset.configured = field.configured ? "true" : "false";
  input.disabled = field.locked;
  input.addEventListener("input", updateDirtyState);
  input.addEventListener("change", updateDirtyState);

  wrapper.append(label, input);
  if (field.description) {
    const description = document.createElement("div");
    description.className = "field-description";
    description.textContent = field.description;
    wrapper.appendChild(description);
  }
  return wrapper;
}

function inputForField(field) {
  if (field.type === "boolean") {
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = String(field.value).toLowerCase() === "true";
    input.dataset.original = input.checked ? "true" : "false";
    return input;
  }

  if (field.type === "tri_boolean") {
    const select = document.createElement("select");
    [
      ["", "Inherit"],
      ["true", "Enabled"],
      ["false", "Disabled"],
    ].forEach(([value, label]) => select.appendChild(option(value, label)));
    select.value = field.value || "";
    return select;
  }

  if (field.type === "select") {
    const select = document.createElement("select");
    field.options.forEach((value) => select.appendChild(option(value, value)));
    select.value = field.value || field.options[0] || "";
    return select;
  }

  if (field.type === "textarea") {
    const textarea = document.createElement("textarea");
    textarea.value = field.value || "";
    return textarea;
  }

  const input = document.createElement("input");
  input.type = field.type === "number" ? "number" : "text";
  if (field.type === "secret") {
    input.type = "password";
    input.placeholder = field.configured
      ? "Configured - enter a new value to replace"
      : "Not configured";
    input.value = "";
    input.autocomplete = "off";
  } else {
    input.value = field.value || "";
  }
  if (field.key.startsWith("MODEL")) {
    input.setAttribute("list", "model-options");
  }
  return input;
}

function option(value, label) {
  const optionEl = document.createElement("option");
  optionEl.value = value;
  optionEl.textContent = label;
  return optionEl;
}

function readFieldValue(input) {
  if (input.type === "checkbox") return input.checked ? "true" : "false";
  if (input.dataset.secret === "true" && input.dataset.configured === "true") {
    return input.value ? input.value : MASKED_SECRET;
  }
  return input.value;
}

function changedValues() {
  const values = {};
  document.querySelectorAll("[data-key]").forEach((input) => {
    if (input.disabled || !input.matches("input, select, textarea")) return;
    const value = readFieldValue(input);
    if (value !== input.dataset.original) {
      values[input.dataset.key] = value;
    }
  });
  return values;
}

function updateDirtyState() {
  const count = Object.keys(changedValues()).length;
  byId("dirtyState").textContent =
    count === 0 ? "No changes" : `${count} unsaved change${count === 1 ? "" : "s"}`;
  byId("applyButton").disabled = count === 0;
}

async function validate(showResult = true) {
  const result = await api("/admin/api/config/validate", {
    method: "POST",
    body: JSON.stringify({ values: changedValues() }),
  });
  if (showResult) {
    showValidationResult(result);
  }
  return result;
}

function showValidationResult(result) {
  if (result.valid) {
    showMessage("Config shape is valid", "ok");
  } else {
    showMessage(result.errors.join("; "), "error");
  }
}

async function apply() {
  const result = await api("/admin/api/config/apply", {
    method: "POST",
    body: JSON.stringify({ values: changedValues() }),
  });
  if (!result.applied) {
    showValidationResult(result);
    return;
  }
  const restart = result.restart || {};
  if (restart.required && restart.automatic) {
    showMessage("Applied. Restarting server...", "ok");
    byId("applyButton").disabled = true;
    setTimeout(() => {
      window.location.href = restart.admin_url || "/admin";
    }, 1600);
    return;
  }
  const pending = restart.required ? restart.fields || [] : result.pending_fields || [];
  await load();
  showMessage(
    pending.length
      ? `Applied. Restart fcc-server to use: ${pending.join(", ")}`
      : "Applied",
    "ok",
  );
}

async function refreshLocalStatus() {
  const result = await api("/admin/api/providers/local-status");
  result.providers.forEach((provider) => {
    state.localStatus.set(provider.provider_id, provider);
    const meta = provider.status_code
      ? `${provider.base_url} returned HTTP ${provider.status_code}`
      : provider.base_url;
    updateProviderCard(provider.provider_id, provider.status, provider.label, meta);
  });
}

async function testProvider(providerId, button) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Testing";
  try {
    const result = await api(`/admin/api/providers/${providerId}/test`, {
      method: "POST",
      body: "{}",
    });
    if (result.ok) {
      updateProviderCard(
        providerId,
        "reachable",
        `${result.models.length} models`,
        result.models.slice(0, 3).join(", ") || "No models returned",
      );
      state.modelOptions = Array.from(
        new Set([
          ...state.modelOptions,
          ...result.models.map((model) => `${providerId}/${model}`),
        ]),
      ).sort();
      syncModelDatalist();
    } else {
      updateProviderCard(providerId, "offline", result.error_type, result.error_type);
    }
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

function syncModelDatalist() {
  let datalist = byId("model-options");
  if (!datalist) {
    datalist = document.createElement("datalist");
    datalist.id = "model-options";
    document.body.appendChild(datalist);
  }
  datalist.innerHTML = "";
  state.modelOptions.forEach((model) => datalist.appendChild(option(model, model)));
}

function showMessage(message, kind = "") {
  const area = byId("messageArea");
  area.textContent = message;
  area.className = `message-area ${kind}`.trim();
}

byId("validateButton").addEventListener("click", () => validate(true));
byId("applyButton").addEventListener("click", apply);

load().catch((error) => {
  showMessage(error.message, "error");
});
```

**สิ่งที่เปลี่ยนจากของเดิม:**
- **ลบ:** `VIEW_GROUPS`, `renderNav()`, `setActiveView()`, `state.activeView`
- **ลบ:** การเรียก `renderNav()` ใน `load()`
- **เปลี่ยน `load()`:** ไม่ต้องตั้ง active view
- **เปลี่ยน `renderSections()`:** จากใช้ `VIEW_GROUPS` + container lookup → ใช้ `sectionToContainer` mapping ตรงๆ แทน
- คง logic field rendering, validate/apply, provider test, dirty state ไว้เหมือนเดิม

- [ ] **Step 2: Commit**

```bash
git add api/admin_static/admin.js
git commit -m "refactor: remove view-switching logic for single-page layout"
```

---

### Task 4: ตรวจสอบ + CI

**Files:**
- Modify: —
- Test: `./scripts/ci.sh` (ตรวจว่า syntax, import, type, test ทั้งหมดยังผ่าน)
- Manual: ลองเปิด `http://localhost:8080/admin` (ถ้า server รันอยู่)

- [ ] **Step 1: Run CI ทั้งหมด**

```bash
cd /Users/tamooods/Playground/free-claude-code && ./scripts/ci.sh
```

Expected: ทั้ง 5 checks ผ่าน (suppression-grep, ruff-format, ruff-check, ty, pytest)

**อนึ่ง:** ไฟล์ที่เปลี่ยนเป็น static frontend ล้วน ไม่มี Python — ถ้า CI ตรงไหนสะดุดเพราะ frontend files อนุโลมให้ข้ามได้

- [ ] **Step 2: live test (optional)**

ถ้า server เปิดอยู่ ลองเปิด browser ที่ `/admin` ดู

- [ ] **Step 3: commit สุดท้าย**

```bash
git add -A
git commit -m "refactor: multi-column dashboard layout for admin UI"
```
