import Link from "next/link";
import type { OpportunityItem } from "@/lib/types";
import { formatUFShort, formatM2, formatPct, formatTimeAgo } from "@/lib/utils";
import { SOURCE_LABELS } from "@/lib/constants";
import { ScoreBadge } from "./ScoreBadge";
import { MapPin, Bed, ArrowDownRight, ExternalLink } from "lucide-react";

export function OpportunityCard({ opp }: { opp: OpportunityItem }) {
  return (
    <div className="bg-white rounded-xl border shadow-sm hover:shadow-md transition-shadow p-5">
      <div className="flex justify-between items-start mb-3">
        <ScoreBadge score={opp.opportunity_score} />
        <span className="text-xs text-gray-400">
          {SOURCE_LABELS[opp.source] || opp.source}
        </span>
      </div>

      <h3 className="font-semibold text-gray-900 text-sm line-clamp-2 mb-2">
        {opp.title}
      </h3>

      <div className="flex items-center gap-1 text-sm text-gray-500 mb-3">
        <MapPin className="h-3.5 w-3.5" />
        {opp.commune}
        {opp.bedrooms && (
          <>
            <span className="mx-1">&middot;</span>
            <Bed className="h-3.5 w-3.5" />
            {opp.bedrooms}D
          </>
        )}
        {opp.m2_total && (
          <>
            <span className="mx-1">&middot;</span>
            {formatM2(opp.m2_total)}
          </>
        )}
      </div>

      <div className="flex justify-between items-end mb-3">
        <div>
          <p className="text-xl font-bold text-gray-900">{formatUFShort(opp.price_uf)}</p>
          {opp.price_m2_uf && (
            <p className="text-xs text-gray-500">{opp.price_m2_uf.toFixed(1)} UF/m²</p>
          )}
        </div>
        {opp.pct_below_market !== null && (
          <div className="text-right">
            <p className="text-sm font-bold text-green-600 flex items-center gap-0.5">
              <ArrowDownRight className="h-4 w-4" />
              {formatPct(opp.pct_below_market)}
            </p>
            {opp.potential_profit_uf !== null && (
              <p className="text-xs text-green-600">
                +{formatUFShort(opp.potential_profit_uf)} potencial
              </p>
            )}
          </div>
        )}
      </div>

      {opp.has_urgency_keyword && (
        <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700 mb-3">
          Urgencia detectada
        </span>
      )}

      <div className="flex justify-between items-center pt-3 border-t">
        <span className="text-xs text-gray-400">{formatTimeAgo(opp.first_seen_at)}</span>
        <a
          href={opp.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          Ver anuncio <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  );
}
