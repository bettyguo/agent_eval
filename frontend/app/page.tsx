import data from "@/public/data/leaderboard.json";

export default function HomePage() {
  const generated = (data as { generated_at?: string }).generated_at ?? "—";
  const nPrimary = (data as { primary?: unknown[] }).primary?.length ?? 0;
  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-3xl font-semibold mb-2">
          Do Claude Code skills actually work?
        </h1>
        <p className="text-neutral-400 max-w-2xl">
          A reproducible benchmark for{" "}
          <code>.claude/skills/</code> directories and{" "}
          <code>CLAUDE.md</code> configurations. Every leaderboard entry is
          content-addressed and re-verified in two clean VMs before being
          listed. <a className="underline" href="/leaderboard">See the leaderboard →</a>
        </p>
      </section>

      <section className="border border-neutral-800 rounded-lg p-4 bg-neutral-900">
        <div className="text-xs uppercase tracking-wide text-neutral-500 mb-1">
          Snapshot
        </div>
        <div className="flex gap-6 text-sm">
          <div>
            <div className="text-neutral-500">Generated</div>
            <div>{generated}</div>
          </div>
          <div>
            <div className="text-neutral-500">Primary-panel entries</div>
            <div>{nPrimary}</div>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">Methodology summary</h2>
        <ul className="list-disc pl-5 space-y-1 text-sm text-neutral-300">
          <li>
            Two panels: <strong>primary</strong> (skill-specific-v1 + tau-bench-v1)
            and <strong>secondary</strong> (swe-bench-lite-v1, contaminated).
            Citable claims use primary only.
          </li>
          <li>
            Canonical seed list <code>[1,2,3,4,5]</code> for leaderboard entries
            (closes the seed-cherry-pick attack).
          </li>
          <li>
            No scalar &quot;agenteval score&quot;. Sortable, not ranked.
          </li>
          <li>
            Deterministic graders only (no LLM-as-judge in v1).
          </li>
          <li>
            Every entry re-verified in two cloud VMs.
          </li>
        </ul>
      </section>
    </div>
  );
}
