"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

const ICON = {
  Pass:    <CheckCircle2 className="h-4 w-4 text-emerald-600" />,
  Warning: <AlertTriangle className="h-4 w-4 text-amber-600" />,
  Fail:    <XCircle className="h-4 w-4 text-red-600" />,
};

const VARIANT = { Pass: "success", Warning: "warning", Fail: "danger" };

export default function IntegrityPanel({ integrity }) {
  if (!integrity) return null;
  const { counts, findings } = integrity;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">2. Data Integrity Checks</CardTitle>
        <p className="text-xs text-muted-foreground">
          Advisory: warnings do not block analysis. Review before relying on results.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-4 text-sm">
          <span>✅ Passed: <strong>{counts.Pass ?? 0}</strong></span>
          <span>⚠️ Warnings: <strong>{counts.Warning ?? 0}</strong></span>
          <span>❌ Failures: <strong>{counts.Fail ?? 0}</strong></span>
        </div>

        <ul className="space-y-2">
          {findings.map((f) => (
            <li key={f.name} className="flex items-start gap-2 text-sm border rounded-md p-3">
              <span className="mt-0.5">{ICON[f.status]}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{f.name}</span>
                  <Badge variant={VARIANT[f.status]}>{f.status}</Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{f.summary}</p>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
