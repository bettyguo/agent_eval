import data from "@/public/data/leaderboard.json";
import LeaderboardTable from "@/components/LeaderboardTable";

type Entry = {
  entry_hash: string;
  model: string;
  provider: string;
  panel: string;
  pass_at_1: number | null;
  pass_at_5: number | null;
  pass_caret_5: number | null;
  cost_usd_median: number | null;
  latency_s_p50: number | null;
  timeout_rate: number | null;
  flags: string[];
  verified: boolean;
};

export default function LeaderboardPage() {
  const primary = ((data as { primary?: Entry[] }).primary ?? []) as Entry[];
  const secondary = ((data as { secondary?: Entry[] }).secondary ?? []) as Entry[];

  return (
    <div className="space-y-12">
      <section>
        <h1 className="text-2xl font-semibold mb-1">Primary panel</h1>
        <p className="text-sm text-neutral-400 mb-4">
          Uncontaminated by construction: 20 skill-specific tasks + 50 TAU-Bench
          subset tasks. All cite-worthy claims live here.
        </p>
        <LeaderboardTable rows={primary} panel="primary" />
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-1">
          Secondary panel — Informative but contaminated
        </h2>
        <p className="text-sm text-amber-300 mb-4">
          ⚠ Contaminated benchmark — delta may be confounded by
          skill × memorization interaction; not citable as a skill-effect claim.
        </p>
        <LeaderboardTable rows={secondary} panel="secondary" />
      </section>
    </div>
  );
}
