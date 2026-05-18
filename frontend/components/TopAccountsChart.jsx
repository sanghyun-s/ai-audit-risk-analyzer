"use client";

import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const Plot = dynamic(() => import("react-plotly.js"), {
  ssr: false,
  loading: () => <div className="h-72 flex items-center justify-center text-sm text-muted-foreground">Loading chart…</div>,
});

export default function TopAccountsChart({ data }) {
  if (!data?.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Top Accounts by Flagged Amount</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No flagged transactions — nothing to rank.</p>
        </CardContent>
      </Card>
    );
  }

  // API returns descending; reverse for horizontal bar (smallest at bottom looks odd, so we sort ascending here)
  const sorted = [...data].sort((a, b) => a.flagged_amount - b.flagged_amount);
  const accounts = sorted.map((d) => d.account_name);
  const amounts  = sorted.map((d) => d.flagged_amount);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Top Accounts by Flagged Amount</CardTitle>
      </CardHeader>
      <CardContent>
        <Plot
          data={[
            {
              x: amounts,
              y: accounts,
              type: "bar",
              orientation: "h",
              hovertemplate: "%{y}<br>$%{x:,.0f}<extra></extra>",
            },
          ]}
          layout={{
            margin: { t: 20, l: 180, r: 30, b: 50 },
            xaxis: { title: "Total flagged amount ($)", tickprefix: "$", tickformat: "," },
            yaxis: { automargin: true },
            height: 320,
          }}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: "100%" }}
        />
      </CardContent>
    </Card>
  );
}
