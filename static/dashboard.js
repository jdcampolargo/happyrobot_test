const state = {
  apiKey: null,
  latestMetrics: null,
};

const params = new URLSearchParams(window.location.search);
const brokerName = document.body.dataset.brokerName || "Acme Logistics";
const environment = document.body.dataset.environment || "production";

const outcomeLabels = {
  booked_transfer_mocked: "Booked / transfer mocked",
  quoted_too_high: "Quoted too high",
  carrier_ineligible: "Carrier ineligible",
  no_matching_load: "No matching load",
  not_interested: "Not interested",
  follow_up_required: "Follow-up required",
  abandoned: "Abandoned",
};

const sentimentLabels = {
  positive: "Positive",
  neutral: "Neutral",
  negative: "Negative",
  mixed: "Mixed",
};

function $(id) {
  return document.getElementById(id);
}

function money(value) {
  if (value === null || value === undefined || value === "") return "--";
  return "$" + Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function pct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toFixed(1) + "%";
}

function decimal(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toFixed(1);
}

function text(value) {
  if (value === null || value === undefined || value === "") return "--";
  return String(value);
}

function setText(id, value) {
  const node = $(id);
  if (node) node.textContent = value;
}

function normalizeLabel(value, labels) {
  return labels[value] || text(value).replaceAll("_", " ");
}

function classForOutcome(value) {
  if (value === "booked_transfer_mocked" || value === "positive") return "success";
  if (value === "quoted_too_high" || value === "follow_up_required" || value === "mixed" || value === "neutral") return "warning";
  if (value === "carrier_ineligible" || value === "abandoned" || value === "negative") return "danger";
  return "info";
}

function formatDate(value) {
  if (!value) return "--";
  const normalized = String(value).replace(" ", "T") + "Z";
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function escapeHtml(value) {
  return text(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showAuthGate(message = "") {
  const gate = $("auth_gate");
  gate.hidden = false;
  $("auth_error").textContent = message;
  $("api_key_input").focus();
}

function hideAuthGate() {
  $("auth_gate").hidden = true;
}

function getStoredApiKey() {
  const queryKey = params.get("api_key");
  if (queryKey) {
    window.localStorage.setItem("logistics_dashboard_api_key", queryKey);
    return queryKey;
  }
  return window.localStorage.getItem("logistics_dashboard_api_key");
}

function renderBars(targetId, counts, labels) {
  const target = $(targetId);
  const entries = Object.entries(counts || {});
  const total = entries.reduce((sum, [, value]) => sum + Number(value), 0);
  const max = Math.max(1, ...entries.map(([, value]) => Number(value)));

  if (!entries.length) {
    target.innerHTML = '<div class="empty-state">No call data has been logged yet.</div>';
    return;
  }

  target.innerHTML = entries
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .map(([name, value]) => {
      const percent = Math.round((Number(value) / max) * 100);
      const share = total ? Math.round((Number(value) / total) * 100) : 0;
      const className = classForOutcome(name);
      return `
        <div class="bar-row">
          <div class="bar-label">
            <strong>${escapeHtml(normalizeLabel(name, labels))}</strong>
            <small>${share}% of logged calls</small>
          </div>
          <div class="bar-track" aria-hidden="true">
            <div class="bar-fill ${className}" style="width: ${percent}%"></div>
          </div>
          <div class="bar-value">${Number(value)}</div>
        </div>
      `;
    })
    .join("");
}

function renderLaneRows(rows) {
  const target = $("lane_rows");
  if (!rows || !rows.length) {
    target.innerHTML = '<tr><td colspan="5" class="empty-state">No lane data has been logged yet.</td></tr>';
    return;
  }

  target.innerHTML = rows
    .map((row) => {
      const conversion = Number(row.conversion_rate || 0);
      return `
        <tr>
          <td data-label="Lane"><span class="lane-name">${escapeHtml(row.lane)}</span></td>
          <td data-label="Calls" class="numeric">${text(row.calls)}</td>
          <td data-label="Booked" class="numeric">${text(row.booked)}</td>
          <td data-label="Conversion">
            <div class="mini-meter">
              <div class="bar-track" aria-hidden="true">
                <div class="bar-fill ${conversion >= 60 ? "success" : conversion > 0 ? "warning" : "danger"}" style="width: ${conversion}%"></div>
              </div>
              <span class="numeric">${pct(conversion)}</span>
            </div>
          </td>
          <td data-label="Avg final offer" class="numeric">${money(row.avg_final_offer)}</td>
        </tr>
      `;
    })
    .join("");
}

function renderRecentRows(rows) {
  const target = $("recent_rows");
  if (!rows || !rows.length) {
    target.innerHTML = '<tr><td colspan="10" class="empty-state">No call records have been logged yet.</td></tr>';
    return;
  }

  target.innerHTML = rows
    .map((row) => {
      const outcomeClass = classForOutcome(row.outcome);
      const sentimentClass = classForOutcome(row.sentiment);
      return `
        <tr>
          <td data-label="Created">${formatDate(row.created_at)}</td>
          <td data-label="Run" class="numeric">${escapeHtml(row.run_id)}</td>
          <td data-label="Carrier">${escapeHtml(row.carrier_name)}</td>
          <td data-label="MC" class="numeric">${escapeHtml(row.mc_number)}</td>
          <td data-label="Load" class="numeric">${escapeHtml(row.load_id)}</td>
          <td data-label="Outcome"><span class="status-pill ${outcomeClass}">${escapeHtml(normalizeLabel(row.outcome, outcomeLabels))}</span></td>
          <td data-label="Sentiment"><span class="status-pill ${sentimentClass}">${escapeHtml(normalizeLabel(row.sentiment, sentimentLabels))}</span></td>
          <td data-label="Offer" class="numeric">${money(row.final_offer || row.initial_offer)}</td>
          <td data-label="Rounds" class="numeric">${text(row.negotiation_rounds)}</td>
          <td data-label="Summary" class="summary-cell">${escapeHtml(row.summary)}</td>
        </tr>
      `;
    })
    .join("");
}

function buildDecision(metrics) {
  const transfer = Number(metrics.transfer_rate || 0);
  const qualified = Number(metrics.qualified_carrier_rate || 0);
  const rateDelta = Number(metrics.avg_rate_vs_loadboard_pct || 0);
  const topOutcome = Object.entries(metrics.outcome_counts || {}).sort((a, b) => b[1] - a[1])[0];

  let title = "Metrics are live.";
  let body = `${brokerName} has ${metrics.total_calls} logged calls, ${pct(transfer)} mocked transfer conversion, and ${pct(qualified)} carrier qualification across the current demo set.`;

  if (metrics.total_calls > 0 && transfer >= 50 && qualified >= 75) {
    title = "Qualified transfer paths are working.";
    body = `${metrics.booked_calls} of ${metrics.total_calls} calls reached mocked transfer. Average booked offer is ${pct(rateDelta)} versus board, with rate discipline visible at report level.`;
  } else if (metrics.total_calls > 0 && topOutcome) {
    title = `${normalizeLabel(topOutcome[0], outcomeLabels)} is the leading outcome to improve next.`;
    body = `The report separates eligibility, price resistance, sentiment, and lane conversion so the broker can tune call scripts and pricing policy from the logged facts.`;
  }

  setText("decision_title", title);
  setText("decision_body", body);
}

function buildReportText(metrics) {
  const topLane = (metrics.lane_summary || [])[0];
  return [
    `${brokerName} custom metrics report`,
    `Environment: ${environment}`,
    `Total calls: ${metrics.total_calls}`,
    `Mocked transfer rate: ${pct(metrics.transfer_rate)} (${metrics.booked_calls} calls)`,
    `Qualified carrier rate: ${pct(metrics.qualified_carrier_rate)}`,
    `Average final offer: ${money(metrics.avg_final_offer)}`,
    `Average rate vs loadboard: ${pct(metrics.avg_rate_vs_loadboard_pct)}`,
    `Average negotiation rounds: ${decimal(metrics.avg_negotiation_rounds)}`,
    topLane ? `Top lane by volume: ${topLane.lane} (${topLane.calls} calls, ${pct(topLane.conversion_rate)} conversion)` : "Top lane by volume: none yet",
    "Source: custom /api/metrics endpoint backed by logged call records.",
  ].join("\n");
}

function downloadReport(metrics) {
  const blob = new Blob([JSON.stringify(metrics, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "carrier-sales-metrics.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function copyReport(metrics) {
  const report = buildReportText(metrics);
  await navigator.clipboard.writeText(report);
  const button = $("copy_report");
  const original = button.textContent;
  button.textContent = "Copied";
  window.setTimeout(() => {
    button.textContent = original;
  }, 1200);
}

function renderMetrics(metrics) {
  state.latestMetrics = metrics;
  document.body.classList.add("is-ready");
  hideAuthGate();

  setText("total_calls", text(metrics.total_calls));
  setText("transfer_rate", pct(metrics.transfer_rate));
  setText("booked_calls", text(metrics.booked_calls));
  setText("qualified_rate", pct(metrics.qualified_carrier_rate));
  setText("rate_vs_board", pct(metrics.avg_rate_vs_loadboard_pct));
  setText("avg_final_offer", money(metrics.avg_final_offer));
  setText("avg_rounds", decimal(metrics.avg_negotiation_rounds));
  setText("outcome_total", `${metrics.total_calls} calls`);
  setText("sentiment_total", `${metrics.total_calls} labels`);
  setText("lane_count", `${(metrics.lane_summary || []).length} lanes`);
  setText("environment_label", environment);
  setText("last_refresh", new Date().toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }));
  setText("latest_call", formatDate(metrics.recent_calls && metrics.recent_calls[0] && metrics.recent_calls[0].created_at));

  renderBars("outcome_bars", metrics.outcome_counts, outcomeLabels);
  renderBars("sentiment_bars", metrics.sentiment_counts, sentimentLabels);
  renderLaneRows(metrics.lane_summary);
  renderRecentRows(metrics.recent_calls);
  buildDecision(metrics);
}

function renderError(message) {
  const target = document.querySelector(".workspace");
  target.insertAdjacentHTML(
    "afterbegin",
    `<div class="error-state" role="alert">Could not load metrics: ${escapeHtml(message)}</div>`
  );
}

async function loadMetrics() {
  const resp = await fetch("/api/metrics", {
    headers: { "X-API-Key": state.apiKey },
  });

  if (resp.status === 401) {
    window.localStorage.removeItem("logistics_dashboard_api_key");
    showAuthGate("That API key was rejected.");
    throw new Error("Unauthorized");
  }

  if (!resp.ok) {
    throw new Error(`Metrics request failed with HTTP ${resp.status}`);
  }

  const metrics = await resp.json();
  renderMetrics(metrics);
}

function bindAuthForm() {
  $("auth_form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const key = $("api_key_input").value.trim();
    if (!key) {
      $("auth_error").textContent = "Enter the API key to open the report.";
      return;
    }
    state.apiKey = key;
    window.localStorage.setItem("logistics_dashboard_api_key", key);
    try {
      await loadMetrics();
    } catch (err) {
      if (err.message !== "Unauthorized") renderError(err.message);
    }
  });
}

function bindActions() {
  $("copy_report").addEventListener("click", () => {
    if (state.latestMetrics) copyReport(state.latestMetrics);
  });

  $("download_report").addEventListener("click", () => {
    if (state.latestMetrics) downloadReport(state.latestMetrics);
  });
}

async function init() {
  bindAuthForm();
  bindActions();

  state.apiKey = getStoredApiKey();
  if (!state.apiKey) {
    showAuthGate();
    return;
  }

  try {
    await loadMetrics();
    window.setInterval(() => {
      loadMetrics().catch((err) => {
        if (err.message !== "Unauthorized") renderError(err.message);
      });
    }, 30000);
  } catch (err) {
    if (err.message !== "Unauthorized") renderError(err.message);
  }
}

init();
