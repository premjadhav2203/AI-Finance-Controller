const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore parse failure */
    }
    throw new Error(detail || `Request to ${path} failed`);
  }
  return res.json();
}

export const api = {
  reconcile: () => request("/reconcile", { method: "POST" }),
  taxCheck: () => request("/tax-check"),
  forecast: () => request("/forecast"),
  ask: (question) =>
    request("/qa", { method: "POST", body: JSON.stringify({ question }) }),
  generateData: (n = 80, seed = 42) =>
    request(`/generate-data?n=${n}&seed=${seed}`, { method: "POST" }),
};

export { API_BASE };
