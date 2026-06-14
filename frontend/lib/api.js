// lib/api.js — thin fetch wrapper for the FastAPI endpoints.
// Calls go to /api/* which is proxied to the FastAPI server in dev (see next.config.js)
// and to NEXT_PUBLIC_API_BASE_URL in production.

export async function fetchOptions() {
  const r = await fetch("/api/options");
  if (!r.ok) throw new Error(`/api/options ${r.status}`);
  return r.json();
}

export async function analyze({
  file,
  entityType,
  benchmarkFigure,
  detectionSensitivity,
  periodStart,
  periodEnd,
}) {
  const fd = new FormData();
  fd.append("csv", file);
  fd.append("entity_type", entityType);
  fd.append("benchmark_figure", String(benchmarkFigure));
  fd.append("detection_sensitivity", detectionSensitivity);
  fd.append("period_start", periodStart);
  fd.append("period_end", periodEnd);

  const r = await fetch("/api/analyze", {
    method: "POST",
    body: fd,
  });

  if (!r.ok) {
    let detail;
    try {
      detail = (await r.json()).detail;
    } catch {
      detail = await r.text();
    }
    throw new Error(`Analysis failed (${r.status}): ${detail}`);
  }
  return r.json();
}

// Generate Top-N audit memos for already-flagged rows. Mirrors analyze():
// owns the transport only; callers handle UI state and response mapping.
export async function generateNarratives({ rows, entityContext, topN }) {
  const r = await fetch("/api/narratives", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      rows,
      entity_context: entityContext || {},
      top_n: topN,
    }),
  });

  if (!r.ok) {
    let detail;
    try {
      detail = (await r.json()).detail;
    } catch {
      detail = await r.text();
    }
    throw new Error(`Narrative generation failed (${r.status}): ${detail}`);
  }
  return r.json();
}
