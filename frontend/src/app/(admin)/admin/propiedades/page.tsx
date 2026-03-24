"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getProperties } from "@/lib/api";
import { COMMUNES, SOURCE_LABELS } from "@/lib/constants";
import { formatUFShort, formatM2, formatDate } from "@/lib/utils";
import { ScoreBadge } from "@/components/opportunities/ScoreBadge";
import { SlidersHorizontal, ExternalLink } from "lucide-react";

export default function PropiedadesAdminPage() {
  const [commune, setCommune] = useState("");
  const [onlyOpps, setOnlyOpps] = useState(false);
  const [page, setPage] = useState(1);

  const params: Record<string, string> = { page: String(page), limit: "25" };
  if (commune) params.commune = commune;
  if (onlyOpps) params.only_opportunities = "true";

  const { data, isLoading } = useQuery({
    queryKey: ["admin-properties", params],
    queryFn: () => getProperties(params),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Propiedades</h1>

      {/* Filters */}
      <div className="bg-white rounded-xl border p-4 mb-6 flex flex-wrap gap-3 items-center">
        <SlidersHorizontal className="h-4 w-4 text-gray-400" />
        <select value={commune} onChange={(e) => { setCommune(e.target.value); setPage(1); }} className="border rounded-lg px-3 py-1.5 text-sm bg-white">
          <option value="">Todas las comunas</option>
          {COMMUNES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" checked={onlyOpps} onChange={(e) => { setOnlyOpps(e.target.checked); setPage(1); }} className="rounded" />
          Solo oportunidades
        </label>
        {data && <span className="text-xs text-gray-400 ml-auto">{data.total} resultados</span>}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border overflow-hidden">
        {isLoading ? (
          <div className="p-6 animate-pulse h-96" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Título</th>
                  <th className="px-4 py-3 text-left">Comuna</th>
                  <th className="px-4 py-3 text-right">Precio</th>
                  <th className="px-4 py-3 text-right">UF/m²</th>
                  <th className="px-4 py-3 text-right">m²</th>
                  <th className="px-4 py-3 text-center">Dorms</th>
                  <th className="px-4 py-3 text-center">Score</th>
                  <th className="px-4 py-3 text-left">Fuente</th>
                  <th className="px-4 py-3 text-right">Detectado</th>
                  <th className="px-4 py-3 text-center">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(data?.data || []).map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 max-w-[200px] truncate font-medium">{p.title}</td>
                    <td className="px-4 py-3 whitespace-nowrap">{p.commune}</td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">{formatUFShort(p.price_uf)}</td>
                    <td className="px-4 py-3 text-right">{p.price_m2_uf?.toFixed(1) || "-"}</td>
                    <td className="px-4 py-3 text-right">{p.m2_total ? Math.round(p.m2_total) : "-"}</td>
                    <td className="px-4 py-3 text-center">{p.bedrooms || "-"}</td>
                    <td className="px-4 py-3 text-center">
                      {p.is_opportunity ? <ScoreBadge score={p.opportunity_score} /> : <span className="text-gray-400 text-xs">{p.opportunity_score ?? "-"}</span>}
                    </td>
                    <td className="px-4 py-3 text-xs">{SOURCE_LABELS[p.source] || p.source}</td>
                    <td className="px-4 py-3 text-right text-xs text-gray-400">{formatDate(p.first_seen_at)}</td>
                    <td className="px-4 py-3 text-center">
                      <a href={p.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700">
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.total > 25 && (
          <div className="flex justify-center gap-2 p-4 border-t">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1.5 border rounded text-xs disabled:opacity-50">Anterior</button>
            <span className="px-3 py-1.5 text-xs text-gray-500">Pág {page}/{Math.ceil(data.total / 25)}</span>
            <button onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(data.total / 25)} className="px-3 py-1.5 border rounded text-xs disabled:opacity-50">Siguiente</button>
          </div>
        )}
      </div>
    </div>
  );
}
