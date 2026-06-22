"use client";

import * as React from "react";

/**
 * SignalCard — one Data Dictionary entry, in the
 * "means / matters / request / does not mean" pattern.
 * Presentational only; all content passed as props.
 */
export default function SignalCard({
  indicator,
  aka,
  whatItMeans,
  whyItMatters,
  whatToRequest,
  whatItDoesNotMean,
}) {
  const rows = [
    { label: "What it means", value: whatItMeans },
    { label: "Why it matters", value: whyItMatters },
    { label: "What to request / review", value: whatToRequest },
    { label: "What it does not mean", value: whatItDoesNotMean },
  ];

  return (
    <div className="rounded-lg border bg-background p-4 space-y-3">
      <div>
        <p className="text-sm font-semibold text-foreground">{indicator}</p>
        {aka && (
          <p className="text-[11px] italic text-muted-foreground">{aka}</p>
        )}
      </div>
      <div className="space-y-2">
        {rows.map((r) => (
          <div key={r.label} className="space-y-0.5">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              {r.label}
            </p>
            <p className="text-xs leading-relaxed text-foreground">{r.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
