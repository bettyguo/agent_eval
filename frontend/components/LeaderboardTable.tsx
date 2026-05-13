"use client";

import { useMemo, useState } from "react";

type Row = {
  entry_hash: string;
  model: string;
  provider: string;
  pass_at_1: number | null;
  pass_at_5: number | null;
  pass_caret_5: number | null;
  cost_usd_median: number | null;
  latency_s_p50: number | null;
  timeout_rate: number | null;
  flags: string[];
  verified: boolean;
};

type SortKey =
  | "pass_at_1"
  | "pass_at_5"
  | "pass_caret_5"
  | "cost_usd_median"
  | "latency_s_p50"
  | "timeout_rate";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "pass_at_1", label: "pass@1" },
  { key: "pass_at_5", label: "pass@5" },
  { key: "pass_caret_5", label: "pass^5" },
  { key: "cost_usd_median", label: "cost $ (med)" },
  { key: "latency_s_p50", label: "latency p50 (s)" },
  { key: "timeout_rate", label: "timeout_rate" },
];

export default function LeaderboardTable({
  rows,
  panel,
}: {
  rows: Row[];
  panel: "primary" | "secondary";
}) {
  const [sortBy, setSortBy] = useState<SortKey>("pass_at_1");
  const [desc, setDesc] = useState(true);

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      const va = a[sortBy] ?? -Infinity;
      const vb = b[sortBy] ?? -Infinity;
      return desc ? (vb as number) - (va as number) : (va as number) - (vb as number);
    });
    return copy;
  }, [rows, sortBy, desc]);

  if (rows.length === 0) {
    return (
      <p className="text-sm text-neutral-500 italic">
        No entries yet. PR a result JSON to <code>frontend/data/submissions/</code>.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm border border-neutral-800">
        <thead className="bg-neutral-900 text-neutral-300">
          <tr>
            <th className="px-3 py-2 text-left">Skill bundle</th>
            <th className="px-3 py-2 text-left">Model</th>
            {COLUMNS.map((c) => (
              <th
                key={c.key}
                className="px-3 py-2 text-right cursor-pointer hover:bg-neutral-800"
                aria-sort={sortBy === c.key ? (desc ? "descending" : "ascending") : "none"}
                onClick={() => {
                  if (sortBy === c.key) setDesc(!desc);
                  else {
                    setSortBy(c.key);
                    setDesc(true);
                  }
                }}
              >
                {c.label} {sortBy === c.key ? (desc ? "▼" : "▲") : ""}
              </th>
            ))}
            <th className="px-3 py-2 text-left">Flags</th>
            <th className="px-3 py-2">Verified</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr
              key={r.entry_hash}
              className={panel === "secondary" ? "bg-neutral-900/40" : ""}
            >
              <td className="px-3 py-2 font-mono text-xs">
                {r.entry_hash.slice(0, 12)}…
              </td>
              <td className="px-3 py-2">
                {r.provider}/{r.model}
              </td>
              {COLUMNS.map((c) => (
                <td key={c.key} className="px-3 py-2 text-right font-mono">
                  {r[c.key] == null ? "—" : (r[c.key] as number).toFixed(3)}
                </td>
              ))}
              <td className="px-3 py-2">
                {r.flags.length === 0 ? (
                  <span className="text-neutral-600">—</span>
                ) : (
                  r.flags.map((f) => (
                    <span
                      key={f}
                      className="inline-block mr-1 px-1.5 py-0.5 rounded text-xs bg-amber-900/40 text-amber-200"
                    >
                      {f}
                    </span>
                  ))
                )}
              </td>
              <td className="px-3 py-2 text-center">
                {r.verified ? (
                  <span className="text-emerald-400">✓</span>
                ) : (
                  <span className="text-amber-400">pending</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
