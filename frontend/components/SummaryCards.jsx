"use client";

import { Card, CardContent } from "@/components/ui/card";

function fmtInt(n) {
  return Number(n).toLocaleString();
}

export default function SummaryCards({ summary }) {
  if (!summary) return null;
  const items = [
    { label: "Total transactions analyzed", value: fmtInt(summary.total) },
    { label: "Flagged (High + Medium)", value: fmtInt(summary.flagged) },
    { label: "Flagged %", value: `${summary.flagged_pct.toFixed(1)}%` },
    { label: "Overall risk rating", value: summary.risk_rating },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {items.map((it) => (
        <Card key={it.label}>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">{it.label}</p>
            <p className="text-2xl font-semibold mt-1">{it.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
