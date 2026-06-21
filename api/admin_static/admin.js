// ── Constants ──
const MASKED_SECRET = "********";

const NAV_GROUPS = [
  { label: "Model Routing", icon: "🖥️", sections: ["models"] },
  { label: "Configuration", icon: "⚙️", sections: ["providers", "runtime"] },
  { label: "Models", icon: "🧠", sections: ["thinking", "web_tools"] },
  { label: "Messaging", icon: "💬", sections: ["messaging", "voice"] },
  { label: "Diagnostics", icon: "🛠️", sections: ["diagnostics", "smoke"] },
];

// ── Standalone helpers ──

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok)
    throw new Error(`${response.status} ${response.statusText}`);

  return response.json();
}

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
  return (
    names[providerId] ||
    providerId
      .split("_")
      .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
      .join(" ")
  );
}



function statusClass(status) {
  if (["configured", "reachable", "running"].includes(status)) return "ok";
  if (["missing_key", "missing_url", "unknown"].includes(status)) return "warn";
  if (["offline", "error"].includes(status)) return "error";
  return "neutral";
}

// ── Alpine Component ──

function adminUi() {
  return {
    // === Reactive State ===
    config: null,
    sections: [],
    fields: [],
    fieldValues: {},
    originals: {},
    providerStatus: [],
    modelOptions: [],
    toast: { show: false, message: "", type: "" },
    activeSection: "",
    sidebarOpen: false,
    searchQuery: "",
    loading: true,
    showAdvanced: {},
    combos: {},
    validationErrors: {},



    // === Init (auto-called by Alpine) ===
    async init() {
      await this.load();
    },


    async load() {
      this.loading = true;
      try {
        const config = await api("/admin/api/config");
        this.config = config;
        this.sections = config.sections;
        this.fields = config.fields;
        this.providerStatus = config.provider_status;

        // Seed form values and originals for dirty tracking
        const values = {};
        const originals = {};
        config.fields.forEach((f) => {
          const val =
            f.type === "secret" && f.configured ? MASKED_SECRET : f.value || "";
          values[f.key] = val;
          originals[f.key] = val;

        });
        this.fieldValues = values;
        this.originals = originals;

        // Initialize showSecrets for each secret field
        const secrets = {};
        config.fields
          .filter((f) => f.type === "secret")
          .forEach((f) => {
            secrets[f.key] = false;
          });

        this.showSecrets = secrets;

        // Set initial active section
        const firstGroup = NAV_GROUPS.find((g) => g.sections.length > 0);
        this.activeSection = firstGroup ? firstGroup.sections[0] : "";

        // Load model options from server model cache (zero provider API calls)
        try {
          const status = await api("/admin/api/status");
          const cached = status.cached_models || {};
          this.modelOptions = Object.entries(cached)
            .flatMap(([pid, models]) => models.map((m) => `${pid}/${m}`))
            .sort();
        } catch (_) {
          /* status endpoint unavailable — datalist stays empty */
        }

        // Setup scroll spy once DOM is rendered
        await this.$nextTick();
        this.setupScrollSpy();

        // Clear validation errors when user edits a field
        this.$watch(
          "fieldValues",
          (val) => {
            for (const key of Object.keys(this.validationErrors)) {
              if (val[key] !== this.originals[key]) {
                delete this.validationErrors[key];
              }
            }
          },
          { deep: true },
        );


      } catch (e) {
        this.showToast(e.message, "error");
      } finally {
        this.loading = false;
      }
    },

    // === Field helpers (used in Alpine templates) ===

    fieldsForSection(sectionId) {
      return this.fields.filter((f) => f.section === sectionId);
    },

    sectionsFor(ids) {
      const idList = ids.split(",");
      return this.sections.filter((s) => idList.includes(s.id));
    },

    navGroups() {
      return NAV_GROUPS;
    },

    sectionFromId(id) {
      return this.sections.find((s) => s.id === id);
    },

    sourceText(field) {
      const parts = [];
      const label = sourceLabel(field.source);
      if (label) parts.push(label);
      if (field.locked) parts.push("locked");
      return parts.join(" ");
    },

    providerName,
    statusClass,


    errCls(key) {
      return this.validationErrors[key] ? "field-error" : "";
    },


    // === Search (filters NAV_GROUPS by section label) ===

    filteredNavGroups(query) {
      if (!query) return NAV_GROUPS;
      const q = query.toLowerCase();
      return NAV_GROUPS.map((g) => ({
        ...g,
        sections: g.sections.filter((id) => {
          const s = this.sections.find((x) => x.id === id);
          return s && s.label.toLowerCase().includes(q);
        }),
      })).filter((g) => g.sections.length > 0);

    },

    // === Dirty state ===

    changedValues() {
      const vals = {};
      for (const key of Object.keys(this.fieldValues)) {
        const val = this.fieldValues[key];
        if (val === MASKED_SECRET) continue; // unchanged secret
        if (val !== this.originals[key]) {
          vals[key] = val;
        }
      }
      return vals;
    },

    get dirtyCount() {
      return Object.keys(this.changedValues()).length;
    },

    get dirtyText() {
      const c = this.dirtyCount;
      return c === 0
        ? "No changes"
        : `${c} unsaved change${c === 1 ? "" : "s"}`;
    },

    // === Form toggles ===

    toggleField(key) {
      this.fieldValues[key] =
        this.fieldValues[key] === "true" ? "false" : "true";
      delete this.validationErrors[key];
    },

    // === Model combobox helpers ===

    filteredModels(fieldKey) {
      const q = (this.fieldValues[fieldKey] || "").toLowerCase();
      if (!q) return this.modelOptions;
      return this.modelOptions.filter((m) => m.toLowerCase().includes(q));
    },

    comboNav(fieldKey, direction) {
      const c = this.combos[fieldKey] || { idx: -1 };
      this.combos[fieldKey] = c;
      const len = this.filteredModels(fieldKey).length;
      if (direction === "down") c.idx = Math.min(c.idx + 1, len - 1);
      if (direction === "up") c.idx = Math.max(c.idx - 1, 0);
    },

    comboSelectActive(fieldKey) {
      const c = this.combos[fieldKey];
      if (c && c.idx >= 0) {
        const models = this.filteredModels(fieldKey);
        if (models[c.idx]) this.selectModel(fieldKey, models[c.idx]);
      }
    },

    selectModel(fieldKey, model) {
      this.fieldValues[fieldKey] = model;
      if (this.combos[fieldKey]) {
        this.combos[fieldKey].open = false;
        this.combos[fieldKey].idx = -1;
      }

    },

    // === Validate / Apply ===

    async validate() {
      return api("/admin/api/config/validate", {
        method: "POST",
        body: JSON.stringify({ values: this.changedValues() }),
      }).catch((e) => ({ valid: false, errors: [e.message] }));
    },

    async validateAndShow() {
      this.validationErrors = {};

      const result = await this.validate();
      if (result.valid) {
        this.showToast("Config shape is valid", "ok");
      } else {
        (result.errors || []).forEach((e) => {
          const colon = e.indexOf(":");
          if (colon > 0) {
            const key = e.substring(0, colon).trim();
            if (Object.prototype.hasOwnProperty.call(this.fieldValues, key)) {
              this.validationErrors[key] = e.substring(colon + 1).trim();
            }
          }
        });

        this.showToast(result.errors.join("; "), "error");
      }
    },

    async apply() {
      this.validationErrors = {};

      const result = await api("/admin/api/config/apply", {
        method: "POST",
        body: JSON.stringify({ values: this.changedValues() }),
      }).catch((e) => ({ applied: false, errors: [e.message] }));

      if (!result.applied) {
        this.showToast(result.errors?.join("; ") || "Apply failed", "error");
        return;
      }

      const restart = result.restart || {};
      if (restart.required && restart.automatic) {
        this.showToast("Applied. Restarting server...", "ok");
        setTimeout(() => {
          window.location.href = restart.admin_url || "/admin";
        }, 1600);
        return;
      }

      const pending = restart.required
        ? restart.fields || []
        : result.pending_fields || [];
      await this.load();
      this.showToast(
        pending.length
          ? `Applied. Restart fcc-server to use: ${pending.join(", ")}`
          : "Applied",
        "ok",
      );
    },

    // === Provider operations ===

    async testProvider(providerId) {
      try {
        const result = await api(`/admin/api/providers/${providerId}/test`, {
          method: "POST",
          body: "{}",
        });
        const card = this.providerStatus.find(
          (p) => p.provider_id === providerId,
        );
        if (!card) return;

        if (result.ok) {
          card.status = "reachable";
          card.label = `${result.models.length} models`;
          this.modelOptions = Array.from(
            new Set([
              ...this.modelOptions,
              ...result.models.map((m) => `${providerId}/${m}`),
            ]),
          ).sort();
        } else {
          card.status = "offline";
          card.label = result.error_type;
        }
      } catch (e) {
        this.showToast(e.message, "error");
      }
    },

    // === Navigation ===

    scrollToSection(sectionId) {
      const el = document.getElementById(`section-${sectionId}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        this.activeSection = sectionId;
      }
      this.sidebarOpen = false;
    },

    // === Scroll spy (IntersectionObserver) ===


    setupScrollSpy() {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const id = entry.target.id.replace("section-", "");
              this.activeSection = id;
            }
          });
        },
        { rootMargin: "-20% 0px -70% 0px" },
      );
      document
        .querySelectorAll("[id^='section-']")
        .forEach((el) => observer.observe(el));
    },

    // === Advanced sections ===

    hasAdvanced(sectionId) {
      return this.fields.some((f) => f.section === sectionId && f.advanced);

    },

    // === Notifications ===

    showToast(message, type = "success") {
      this.toast = { show: true, message, type };
      setTimeout(() => {
        this.toast.show = false;
      }, 3000);
    },
  };
}
