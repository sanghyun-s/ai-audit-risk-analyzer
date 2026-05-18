"use client";

import { Card, CardContent } from "@/components/ui/card";

function fsPctForEntity(entityType) {
  return entityType === "Public company" ? 0.05 : 0.04;
}

function formatMoney(n) {
  return `$${Math.round(n).toLocaleString()}`;
}

export default function MaterialityBanner({ entityType, benchmarkFigure }) {
  const fsPct = fsPctForEntity(entityType);
  const fs = benchmarkFigure * fsPct;
  const perf = fs * 0.5;
  const txn = fs * 0.8;

  const items = [
    { label: `FS Materiality (${(fsPct * 100).toFixed(0)}% of benchmark)`, value: fs },
    { label: "Performance Materiality (50% of FS)", value: perf },
    { label: "Transaction Materiality (80% of FS)", value: txn },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {items.map((it) => (
        <Card key={it.label}>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">{it.label}</p>
            <p className="text-3xl font-semibold mt-1">{formatMoney(it.value)}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
