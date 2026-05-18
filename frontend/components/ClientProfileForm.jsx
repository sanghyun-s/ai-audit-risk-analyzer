"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";

const BENCHMARK_LABELS = {
  "Private for-profit": "EBT (Earnings Before Tax)",
  "Public company":     "Net Income",
  "Non-profit":         "Total Expenses",
  "Fund":               "Net Asset Value (NAV)",
};

export default function ClientProfileForm({ value, onChange, options }) {
  const benchmarkLabel = BENCHMARK_LABELS[value.entityType] ?? "Benchmark";
  const update = (patch) => onChange({ ...value, ...patch });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Client Profile</CardTitle>
        <p className="text-xs text-muted-foreground">
          These inputs configure materiality and detection risk for the entire analysis.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="entity_type">Entity type</Label>
          <Select
            id="entity_type"
            value={value.entityType}
            onChange={(e) => update({ entityType: e.target.value })}
          >
            {(options?.entity_types ?? Object.keys(BENCHMARK_LABELS)).map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="benchmark_figure">Benchmark figure — {benchmarkLabel}</Label>
          <Input
            id="benchmark_figure"
            type="number"
            step="1000"
            min="0"
            value={value.benchmarkFigure}
            onChange={(e) => update({ benchmarkFigure: Number(e.target.value) })}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="detection_sensitivity">Detection sensitivity</Label>
          <Select
            id="detection_sensitivity"
            value={value.detectionSensitivity}
            onChange={(e) => update({ detectionSensitivity: e.target.value })}
          >
            {(options?.detection_sensitivities ?? [
              "Conservative (0.03)", "Balanced (0.05)", "Aggressive (0.10)",
            ]).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </Select>
          <p className="text-xs text-muted-foreground">
            Maps to Isolation Forest <code>contamination</code>. Lower = stricter.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label htmlFor="period_start">Period start</Label>
            <Input
              id="period_start"
              type="date"
              value={value.periodStart}
              onChange={(e) => update({ periodStart: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="period_end">Period end</Label>
            <Input
              id="period_end"
              type="date"
              value={value.periodEnd}
              onChange={(e) => update({ periodEnd: e.target.value })}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
