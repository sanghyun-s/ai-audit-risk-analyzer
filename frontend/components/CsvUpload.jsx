"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Upload } from "lucide-react";

export default function CsvUpload({
  file,
  onFileChange,
  onRun,
  loading,
  requiredColumns,
  disabled,
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">1. Upload General Ledger CSV</CardTitle>
        <p className="text-xs text-muted-foreground">
          Required columns:{" "}
          {requiredColumns?.length
            ? requiredColumns.map((c) => <code key={c} className="mx-0.5 rounded bg-muted px-1.5 py-0.5 text-[11px]">{c}</code>)
            : null}
          . Phase 2 also reads optional <code>debit_amount</code>,{" "}
          <code>credit_amount</code>, <code>dr_cr_pattern</code>. A sample is in{" "}
          <code>backend/sample_data/sample_gl.csv</code>.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          <Input
            type="file"
            accept=".csv"
            onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
            className="max-w-md"
          />
          <Button
            onClick={onRun}
            disabled={!file || loading || disabled}
            className="gap-2"
          >
            <Upload className="h-4 w-4" />
            {loading ? "Analyzing…" : "Run Analysis"}
          </Button>
        </div>
        {file && (
          <p className="text-xs text-muted-foreground">
            Selected: <span className="font-medium">{file.name}</span>{" "}
            ({(file.size / 1024).toFixed(1)} KB)
          </p>
        )}
      </CardContent>
    </Card>
  );
}
