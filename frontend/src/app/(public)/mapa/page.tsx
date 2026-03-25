"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getProperties } from "@/lib/api";
import { COMMUNES } from "@/lib/constants";
import { SlidersHorizontal, Info, X } from "lucide-react";
import type { PropertyListItem } from "@/lib/types";
import dynamic from "next/dynamic";

const LeafletMap = dynamic(() => import("./LeafletMap"), { ssr: false });

export default function MapaPage() {
  const [commune, setCommune] = useState("");
  const [onlyOpps, setOnlyOpps] = useState(false);
  const [showLegend, setShowLegend] = useState(false);

  const params: Record<string, string> = { limit: "100" };
  if (commune) params.commune = commune;
  if (onlyOpps) params.only_opportunities = "true";

  const { data, isLoading } = useQuery({
    queryKey: ["properties-map", params],
    queryFn: () => getProperties(params),
  });

  const properties = data?.data || [];
  const withCoords = properties.filter(
    (p) => p.latitude != null && p.longitude != null
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 64px)" }}>
      <div className="bg-white border-b px-4 py-3 flex flex-wrap items-center gap-3" style={{ flexShrink: 0 }}>
        <SlidersHorizontal className="h-4 w-4 text-gray-400" />
        <select
          value={commune}
          onChange={(e) => setCommune(e.target.value)}
          className="border rounded-lg px-3 py-1.5 text-sm bg-white"
        >
          <option value="">Todas las comunas</option>
          {COMMUNES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={onlyOpps}
            onChange={(e) => setOnlyOpps(e.target.checked)}
            className="rounded border-gray-300"
          />
          Solo oportunidades
        </label>
        <span className="text-xs text-gray-400 ml-auto">
          {isLoading ? "Cargando..." : `${withCoords.length} propiedades en el mapa`}
        </span>
      </div>
      <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
        <LeafletMap properties={withCoords} />

        {/* Botón de leyenda */}
        <button
          onClick={() => setShowLegend(!showLegend)}
          className="absolute top-3 right-3 z-[1000] bg-white border shadow-md rounded-lg px-3 py-2 flex items-center gap-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <Info className="h-4 w-4" />
          Leyenda
        </button>

        {/* Panel de leyenda */}
        {showLegend && (
          <div className="absolute top-14 right-3 z-[1000] bg-white border shadow-lg rounded-xl p-4 w-64">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-semibold text-sm">Leyenda del Mapa</h3>
              <button onClick={() => setShowLegend(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="inline-block w-4 h-4 rounded-full bg-blue-500 border-2 border-white shadow-sm flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium">Propiedad regular</p>
                  <p className="text-xs text-gray-400">Precio dentro del promedio</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="inline-block w-5 h-5 rounded-full bg-green-500 border-2 border-white shadow-sm flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium">Oportunidad detectada</p>
                  <p className="text-xs text-gray-400">15%+ bajo el promedio de zona</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="inline-block w-5 h-5 rounded-full bg-red-500 border-2 border-white shadow-sm flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium">Oportunidad Oro</p>
                  <p className="text-xs text-gray-400">Score 80+, alta prioridad</p>
                </div>
              </div>
              <hr className="my-2" />
              <p className="text-xs text-gray-400">
                Haz clic en un marcador para ver el detalle de la propiedad.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
