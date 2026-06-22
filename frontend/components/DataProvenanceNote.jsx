"use client";

import * as React from "react";
import { Info } from "lucide-react";

/**
 * DataProvenanceNote — makes the "where did this data come from?" answer
 * visible right at the upload. Pass the selected sample file name if you have
 * it; otherwise it renders the generic line. Detail expands on click.
 *
 * Mount near the file picker / selected-file label in Section 1.
 *
 * Usage:
 *   <DataProvenanceNote fileName={selectedFileName} />
 */
export default function DataProvenanceNote({ fileName }) {
  const [showDetail, setShowDetail] = React.useState(false);

  return (
    <div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
      <div className="flex items-start gap-2">
        <Info className="h-3.5 w-3.5 mt-0.5 shrink-0" />
        <div className="space-y-1">
          <p>
            <span className="font-medium text-foreground">Demo dataset:</span>{" "}
            Seeded synthetic QuickBooks-style GL · No real client data
            {fileName ? (
              <>
                {" "}
                · <span className="font-mono">{fileName}</span>
              </>
            ) : null}
          </p>
          <button
            type="button"
            onClick={() => setShowDetail((v) => !v)}
            className="underline underline-offset-2 hover:text-foreground"
          >
            {showDetail ? "Hide detail" : "What does this mean?"}
          </button>
          {showDetail && (
            <p className="leading-relaxed">
              This sample ledger was generated for validation and contains planted
              review patterns. It does not contain real company or client data.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
