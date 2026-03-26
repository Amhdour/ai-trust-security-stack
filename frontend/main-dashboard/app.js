const root = document.getElementById("dashboard-root");
const tabStrip = document.getElementById("tab-strip");
const heroMeta = document.getElementById("hero-meta");
const heroSteps = document.getElementById("hero-steps");
const sourcesRoot = document.getElementById("sources");

const LANDING_STEPS = [
  "Dashboard main page",
  "Identity and session",
  "Governed AI runtime",
  "Evidence and analytics",
];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function statusClass(status) {
  return `status-pill status-${status || "neutral"}`;
}

function renderHero(payload) {
  heroMeta.innerHTML = `
    <span class="chip">${escapeHtml(payload.runtime_module)}</span>
    <span class="chip">Generated ${escapeHtml(new Date(payload.generated_at).toLocaleString())}</span>
  `;

  heroSteps.innerHTML = LANDING_STEPS.map(
    (label, index) => `
      <article class="step-card">
        <span class="step-index">${index + 1}</span>
        <span class="step-label">${escapeHtml(label)}</span>
      </article>
    `,
  ).join("");
}

function renderTabs(tabs) {
  tabStrip.innerHTML = tabs
    .map(
      (tab) => `
        <button class="tab-button" type="button" data-target="${escapeHtml(tab.id)}">
          ${escapeHtml(tab.label)}
        </button>
      `,
    )
    .join("");

  for (const button of tabStrip.querySelectorAll("button")) {
    button.addEventListener("click", () => {
      const target = document.getElementById(button.dataset.target);
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  }
}

function renderCards(items) {
  return `
    <div class="cards-grid">
      ${items
        .map(
          (item) => `
            <article class="metric-card">
              <div class="metric-label">${escapeHtml(item.label)}</div>
              <div class="metric-value">${escapeHtml(item.value)}</div>
              <div class="metric-detail">${escapeHtml(item.detail)}</div>
              <div class="${statusClass(item.status)}">${escapeHtml(item.status || "neutral")}</div>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderRecords(items) {
  return `
    <div class="records-grid">
      ${items
        .map(
          (item) => `
            <article class="record-card">
              <h3>${escapeHtml(item.title)}</h3>
              <p class="record-meta">${escapeHtml(item.meta)}</p>
              <p class="record-detail">${escapeHtml(item.detail)}</p>
              <div class="${statusClass(item.status)}">${escapeHtml(item.status || "neutral")}</div>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderTable(block) {
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            ${block.columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}
          </tr>
        </thead>
        <tbody>
          ${block.rows
            .map(
              (row) => `
                <tr>
                  ${block.columns.map((column) => `<td>${escapeHtml(row[column.key] ?? "")}</td>`).join("")}
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderLinks(items, className = "link-grid") {
  return `
    <div class="${className}">
      ${items
        .map(
          (item) => `
            <a class="link-card" href="${escapeHtml(item.href)}" target="_blank" rel="noreferrer">
              <div class="${statusClass(item.status)}">${escapeHtml(item.status || "neutral")}</div>
              <h3>${escapeHtml(item.label)}</h3>
              <p class="link-description">${escapeHtml(item.description)}</p>
            </a>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderBlocks(blocks) {
  return blocks
    .map((block) => {
      let content = "";
      if (block.type === "cards") {
        content = renderCards(block.items);
      } else if (block.type === "records") {
        content = renderRecords(block.items);
      } else if (block.type === "table") {
        content = renderTable(block);
      } else if (block.type === "links") {
        content = renderLinks(block.items);
      }

      return `
        <section class="block">
          <h3 class="block-title">${escapeHtml(block.title)}</h3>
          ${content}
        </section>
      `;
    })
    .join("");
}

function renderSections(sections) {
  root.innerHTML = sections
    .map(
      (section) => `
        <section class="dashboard-section" id="${escapeHtml(section.id)}">
          <div class="section-head">
            <p class="eyebrow">${escapeHtml(section.id)}</p>
            <h2>${escapeHtml(section.title)}</h2>
            <p class="section-description">${escapeHtml(section.description)}</p>
          </div>
          ${renderBlocks(section.blocks)}
        </section>
      `,
    )
    .join("");
}

function renderSources(sources) {
  sourcesRoot.innerHTML = sources
    .map(
      (source) => `
        <a class="source-card" href="${escapeHtml(source.href)}" target="_blank" rel="noreferrer">
          <h3>${escapeHtml(source.label)}</h3>
          <p class="source-description">${escapeHtml(source.description)}</p>
        </a>
      `,
    )
    .join("");
}

async function boot() {
  try {
    const response = await fetch("/api/control-plane/overview");
    if (!response.ok) {
      throw new Error(`Dashboard API returned ${response.status}`);
    }

    const payload = await response.json();
    renderHero(payload);
    renderTabs(payload.tabs);
    renderSections(payload.sections);
    renderSources(payload.sources);
  } catch (error) {
    root.innerHTML = `
      <section class="loading-panel">
        <p class="eyebrow">Unavailable</p>
        <h2>Control-plane dashboard could not load</h2>
        <p>${escapeHtml(error.message || "Unknown error")}</p>
      </section>
    `;
  }
}

boot();
