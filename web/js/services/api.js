export async function scoreApi({ query, file }) {
  const options = { method: "POST" };
  if (file) {
    const fd = new FormData();
    fd.append("file", file);
    options.body = fd;
  }
  const res = await fetch(`/api/score${query}`, options);
  const data = await res.json();
  return { res, data };
}

export async function getLastScoreApi(compact = true) {
  return fetch(`/api/score/last?compact=${compact ? "1" : "0"}`);
}

export async function getRecordsApi(params) {
  return fetch(`/api/records?${params.toString()}`);
}

export async function getTopApi(params) {
  return fetch(`/api/top?${params.toString()}`);
}

export async function getScenarioApi() {
  return fetch("/api/scenario/simulate?top_n=100");
}

export async function getDecisionApi(applicationId) {
  return fetch(`/api/decisions/${encodeURIComponent(applicationId)}`);
}

export async function getAuditApi(applicationId) {
  return fetch(`/api/audit/${encodeURIComponent(applicationId)}`);
}

export async function saveDecisionApi(payload) {
  return fetch("/api/decisions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
