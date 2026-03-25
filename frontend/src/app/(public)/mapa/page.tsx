"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getProperties } from "@/lib/api";
import { COMMUNES } from "@/lib/constants";
import { SlidersHorizontal } from "lucide-react";
import type { PropertyListItem } from "@/lib/types";
import dynamic from "next/dynamic";

const LeafletMap = dynamic(() => import("./LeafletMap"), { ssr: false });

export default function MapaPage() {
  const [commune, setCommune] = useState("");
  const [onlyOpps, setOnlyOpps] = useState(false);

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
      <div style={{ flex: 1, minHeight: 0 }}>
        <LeafletMap properties={withCoords} />
      </div>
    </div>
  );
}
