import { cn, getScoreBadge } from "@/lib/utils";

export function ScoreBadge({ score }: { score: number | null }) {
  const badge = getScoreBadge(score);
  return (
    <span className={cn("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold", badge.color, badge.text)}>
      {score ?? "?"} &middot; {badge.label}
    </span>
  );
}
