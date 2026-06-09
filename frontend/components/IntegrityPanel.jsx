"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

const ICON = {
  Pass:    <CheckCircle2 className="h-4 w-4 text-emerald-600" />,
  Warning: <AlertTriangle className="h-4 w-4 text-amber-600" />,
  Fail:    <XCircle className="h-4 w-4 text-red-600" />,
};

const VARIANT = { Pass: "success", Warning: "warning", Fail: "danger" };

/**
 * One-line summary the trigger shows when the panel is collapsed.
 * Always renders all three categories so the row reads consistently
 * even when one category is zero.
 */
function SummaryLine({ counts }) {
  const pass = counts?.Pass ?? 0;
  const warn = counts?.Warning ?? 0;
  const fail = counts?.Fail ?? 0;
  return (
    <span className="text-sm text-muted-foreground">
      <span className="text-emerald-700">{pass} Pass</span>
      <span className="mx-2 text-muted-foreground/60">·</span>
      <span className="text-amber-700">{warn} Warning</span>
      <span className="mx-2 text-muted-foreground/60">·</span>
      <span className="text-red-700">{fail} Fail</span>
    </span>
  );
}

export default function IntegrityPanel({ integrity }) {
  if (!integrity) return null;
  const { counts, findings } = integrity;

  return (
    <Card>
      <Collapsible defaultOpen={false}>
        <CollapsibleTrigger className="px-6 py-4">
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="text-base font-semibold">Data Integrity Checks</span>
            <SummaryLine counts={counts} />
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="space-y-3 pt-0">
            <p className="text-xs text-muted-foreground">
              Advisory: warnings do not block analysis. Review before relying on results.
            </p>
            <ul className="space-y-2">
              {findings.map((f) => (
                <li
                  key={f.name}
                  className="flex items-start gap-2 text-sm border rounded-md p-3"
                >
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
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
