"use client";

import { Card, CardContent } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";

function MetricGrid({ items }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {items.map((it) => (
        <div key={it.label} className="rounded-md border p-3">
          <p className="text-[11px] text-muted-foreground leading-tight">{it.label}</p>
          <p className="text-xl font-semibold mt-1">
            {Number(it.value).toLocaleString()}
          </p>
        </div>
      ))}
    </div>
  );
}

/**
 * One-line summary when collapsed. Reports the count of T1 features that
 * fired ≥1 time and the count of T2 features that fired ≥1 time, plus
 * the combined firing count.
 */
function SummaryLine({ t1, t2 }) {
  const t1Active = Object.values(t1 || {}).filter((v) => Number(v) > 0).length;
  const t2Active = Object.values(t2 || {}).filter((v) => Number(v) > 0).length;
  const total =
    Object.values(t1 || {}).reduce((a, b) => a + (Number(b) || 0), 0) +
    Object.values(t2 || {}).reduce((a, b) => a + (Number(b) || 0), 0);
  return (
    <span className="text-sm text-muted-foreground">
      <span>{t1Active} T1</span>
      <span className="mx-2 text-muted-foreground/60">+</span>
      <span>{t2Active} T2 features active</span>
      <span className="mx-2 text-muted-foreground/60">·</span>
      <span>{total.toLocaleString()} total firings</span>
    </span>
  );
}

export default function FeatureFiringPanel({ featureFiring }) {
  if (!featureFiring) return null;
  const { t1, t2 } = featureFiring;

  return (
    <Card>
      <Collapsible defaultOpen={false}>
        <CollapsibleTrigger className="px-6 py-4">
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="text-base font-semibold">Feature Engineering</span>
            <SummaryLine t1={t1} t2={t2} />
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="space-y-4 pt-0">
            <p className="text-xs text-muted-foreground">
              How the app reads your GL before the ML model runs.
            </p>
            <div>
              <p className="text-sm font-medium mb-2">Tier 1 feature firing</p>
              <MetricGrid
                items={[
                  { label: "Round-number",            value: t1.is_round_number },
                  { label: "Weekend postings",        value: t1.is_weekend_posting },
                  { label: "Missing descriptions",    value: t1.missing_description },
                  { label: "New-vendor txns",         value: t1.is_new_vendor },
                  { label: "Near approval threshold", value: t1.is_near_approval_threshold },
                ]}
              />
            </div>
            <div>
              <p className="text-sm font-medium mb-2">Tier 2 feature firing</p>
              <MetricGrid
                items={[
                  { label: "Control gap ≥ 1",            value: t2.control_gap_ge_1 },
                  { label: "Fraud risk flag (≥2 flags)", value: t2.fraud_risk_flag },
                  { label: "Year-end concentration",     value: t2.is_year_end_concentration },
                  { label: "Non-standard DR/CR",         value: t2.is_non_standard_pattern },
                ]}
              />
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
