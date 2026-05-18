"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";

const PAGE_SIZE = 25;

function tierVariant(tier) {
  if (tier === "High") return "danger";
  if (tier === "Medium") return "warning";
  if (tier === "Low") return "secondary";
  return "outline";
}

function fmtAmount(n) {
  if (n == null) return "";
  return `$${Number(n).toLocaleString(undefined, {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })}`;
}

function fmtDate(s) {
  if (!s) return "";
  return s.split("T")[0];
}

function fmtPct(n) {
  if (n == null) return "";
  return `${Number(n).toFixed(1)}%`;
}

function toCsv(rows, cols) {
  const escape = (v) => {
    if (v == null) return "";
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = cols.join(",");
  const body = rows.map((r) => cols.map((c) => escape(r[c])).join(",")).join("\n");
  return header + "\n" + body;
}

export default function FlaggedTable({ rows }) {
  const [page, setPage] = React.useState(0);

  if (!rows?.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Flagged Transactions</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No flagged transactions.</p>
        </CardContent>
      </Card>
    );
  }

  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const pageRows = rows.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  const downloadCsv = () => {
    const cols = [
      "date", "account_name", "vendor", "amount",
      "anomaly_score", "raw_tier", "final_tier", "pcaob_label",
      "materiality_annotation", "active_flags",
      "control_gap_score", "fraud_risk_flag",
      "period_over_period_pct", "vendor_concentration_pct",
      "is_year_end_concentration", "is_non_standard_pattern",
    ].filter((c) => rows[0] && c in rows[0]);
    const csv = toCsv(rows, cols);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "flagged_transactions.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-lg">Flagged Transactions ({rows.length})</CardTitle>
        <Button variant="outline" size="sm" onClick={downloadCsv} className="gap-2">
          <Download className="h-4 w-4" /> Download CSV
        </Button>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-muted/50">
              <tr className="text-left">
                <th className="px-3 py-2 font-medium">Date</th>
                <th className="px-3 py-2 font-medium">Account</th>
                <th className="px-3 py-2 font-medium">Vendor</th>
                <th className="px-3 py-2 font-medium text-right">Amount</th>
                <th className="px-3 py-2 font-medium">Final Tier</th>
                <th className="px-3 py-2 font-medium">PCAOB Label</th>
                <th className="px-3 py-2 font-medium text-center">Control Gap</th>
                <th className="px-3 py-2 font-medium text-center">Fraud Risk</th>
                <th className="px-3 py-2 font-medium">Active Flags</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((r, i) => (
                <tr key={i} className="border-t hover:bg-muted/30">
                  <td className="px-3 py-2 whitespace-nowrap">{fmtDate(r.date)}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{r.account_name}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{r.vendor}</td>
                  <td className="px-3 py-2 whitespace-nowrap text-right">{fmtAmount(r.amount)}</td>
                  <td className="px-3 py-2">
                    <Badge variant={tierVariant(r.final_tier)}>{r.final_tier}</Badge>
                  </td>
                  <td className="px-3 py-2">{r.pcaob_label}</td>
                  <td className="px-3 py-2 text-center">{r.control_gap_score}</td>
                  <td className="px-3 py-2 text-center">
                    {r.fraud_risk_flag ? <Badge variant="danger">⚠</Badge> : "—"}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">{r.active_flags}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-3 text-xs">
            <span className="text-muted-foreground">
              Page {page + 1} of {totalPages} · showing {pageRows.length} of {rows.length}
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}>
                Previous
              </Button>
              <Button variant="outline" size="sm" disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}>
                Next
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
