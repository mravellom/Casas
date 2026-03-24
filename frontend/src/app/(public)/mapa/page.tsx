"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getProperties } from "@/lib/api";
import { COMMUNES } from "@/lib/constants";
import { SlidersHorizontal } from "lucide-react";

const PropertyMap = dynamic(() => import("@/components/map/PropertyMap"), { ssr: false });

export default function MapaPage() {
  const [commune, setCommune] = useState("");
  const [onlyOpps, setOnlyOpps] = useState(false);

  const params: Record<string, string> = { limit: "200" };
  if (commune) params.commune = commune;
  if (onlyOpps) params.only_opportunities = "true";

  const { data, isLoading } = useQuery({
    queryKey: ["properties-map", params],
    queryFn: () => getProperties(params),
  });

  const properties = data?.data || [];

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Filters bar */}
      <div className="bg-white border-b px-4 py-3 flex flex-wrap items-center gap-3">
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
          {isLoading ? "Cargando..." : `${properties.length} propiedades en el mapa`}
        </span>
      </div>

      {/* Map */}
      <div className="flex-1">
        <PropertyMap properties={properties} />
      </div>
    </div>
  );
}
