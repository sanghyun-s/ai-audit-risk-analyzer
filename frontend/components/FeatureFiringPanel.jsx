"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function MetricGrid({ items }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {items.map((it) => (
        <div key={it.label} className="rounded-md border p-3">
          <p className="text-[11px] text-muted-foreground leading-tight">{it.label}</p>
          <p className="text-xl font-semibold mt-1">{Number(it.value).toLocaleString()}</p>
        </div>
      ))}
    </div>
  );
}

export default function FeatureFiringPanel({ featureFiring }) {
  if (!featureFiring) return null;
  const { t1, t2 } = featureFiring;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">3. Feature Engineering</CardTitle>
        <p className="text-xs text-muted-foreground">
          How the app reads your GL before the ML model runs.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-sm font-medium mb-2">Tier 1 feature firing</p>
          <MetricGrid items={[
            { label: "Round-number",            value: t1.is_round_number },
            { label: "Weekend postings",        value: t1.is_weekend_posting },
            { label: "Missing descriptions",    value: t1.missing_description },
            { label: "New-vendor txns",         value: t1.is_new_vendor },
            { label: "Near approval threshold", value: t1.is_near_approval_threshold },
          ]} />
        </div>
        <div>
          <p className="text-sm font-medium mb-2">Tier 2 feature firing</p>
          <MetricGrid items={[
            { label: "Control gap ≥ 1",           value: t2.control_gap_ge_1 },
            { label: "Fraud risk flag (≥2 flags)", value: t2.fraud_risk_flag },
            { label: "Year-end concentration",     value: t2.is_year_end_concentration },
            { label: "Non-standard DR/CR",         value: t2.is_non_standard_pattern },
          ]} />
        </div>
      </CardContent>
    </Card>
  );
}
