"use client";
import { useState } from "react";
import { useOpportunities } from "@/lib/hooks/useOpportunities";
import { OpportunityCard } from "@/components/opportunities/OpportunityCard";
import { COMMUNES } from "@/lib/constants";
import { Search, SlidersHorizontal } from "lucide-react";

export default function OpportunitiesPage() {
  const [commune, setCommune] = useState("");
  const [bedrooms, setBedrooms] = useState("");
  const [minScore, setMinScore] = useState("0");
  const [page, setPage] = useState(1);

  const params: Record<string, string> = { page: String(page), limit: "12" };
  if (commune) params.commune = commune;
  if (bedrooms) params.bedrooms = bedrooms;
  if (minScore) params.min_score = minScore;

  const { data, isLoading, error } = useOpportunities(params);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Oportunidades</h1>
          <p className="text-gray-500 text-sm mt-1">
            Departamentos subvalorados detectados automáticamente
          </p>
        </div>
        {data && (
          <span className="text-sm text-gray-400">{data.total} oportunidades encontradas</span>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border p-4 mb-6 flex flex-wrap gap-3 items-center">
        <SlidersHorizontal className="h-4 w-4 text-gray-400" />
        <select
          value={commune}
          onChange={(e) => { setCommune(e.target.value); setPage(1); }}
          className="border rounded-lg px-3 py-1.5 text-sm bg-white"
        >
          <option value="">Todas las comunas</option>
          {COMMUNES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          value={bedrooms}
          onChange={(e) => { setBedrooms(e.target.value); setPage(1); }}
          className="border rounded-lg px-3 py-1.5 text-sm bg-white"
        >
          <option value="">Dormitorios</option>
          <option value="1">1 dormitorio</option>
          <option value="2">2 dormitorios</option>
        </select>
        <select
          value={minScore}
          onChange={(e) => { setMinScore(e.target.value); setPage(1); }}
          className="border rounded-lg px-3 py-1.5 text-sm bg-white"
        >
          <option value="80">Solo Oro (80+)</option>
          <option value="70">Oro + Plata (70+)</option>
          <option value="60">Todas (60+)</option>
          <option value="0">Sin filtro</option>
        </select>
      </div>

      {/* Grid */}
      {isLoading && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border p-5 animate-pulse h-64" />
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center text-red-600">
          Error cargando oportunidades. Verifica que el backend esté activo.
        </div>
      )}

      {data && data.data.length === 0 && (
        <div className="bg-white rounded-xl border p-12 text-center">
          <Search className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No hay oportunidades con estos filtros</p>
          <p className="text-gray-400 text-sm mt-1">Intenta con filtros menos restrictivos</p>
        </div>
      )}

      {data && data.data.length > 0 && (
        <>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {data.data.map((opp) => (
              <OpportunityCard key={opp.id} opp={opp} />
            ))}
          </div>

          {/* Pagination */}
          {data.total > 12 && (
            <div className="flex justify-center gap-2 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 border rounded-lg text-sm disabled:opacity-50 hover:bg-gray-50"
              >
                Anterior
              </button>
              <span className="px-4 py-2 text-sm text-gray-500">
                Página {page} de {Math.ceil(data.total / 12)}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(data.total / 12)}
                className="px-4 py-2 border rounded-lg text-sm disabled:opacity-50 hover:bg-gray-50"
              >
                Siguiente
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
