"use client";
import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { getProperties } from "@/lib/api";
import { COMMUNES, SANTIAGO_CENTER, SOURCE_LABELS } from "@/lib/constants";
import { formatUFShort, formatM2 } from "@/lib/utils";
import { SlidersHorizontal } from "lucide-react";
import type { PropertyListItem } from "@/lib/types";

function getMarkerColor(prop: PropertyListItem): string {
  if (prop.is_opportunity && (prop.opportunity_score ?? 0) >= 80) return "#ef4444";
  if (prop.is_opportunity) return "#22c55e";
  return "#3b82f6";
}

export default function MapaPage() {
  const [commune, setCommune] = useState("");
  const [onlyOpps, setOnlyOpps] = useState(false);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const leafletRef = useRef<any>(null);

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

  // Inicializar mapa UNA sola vez
  useEffect(() => {
    let cancelled = false;

    import("leaflet").then((L) => {
      if (cancelled || !mapContainerRef.current) return;

      // Verificar si el div ya tiene un mapa (Leaflet marca internamente)
      const container = mapContainerRef.current as any;
      if (container._leaflet_id) return;

      const map = L.default.map(container, {
        scrollWheelZoom: true,
        center: [SANTIAGO_CENTER.lat, SANTIAGO_CENTER.lng],
        zoom: 12,
      });

      L.default.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 19,
      }).addTo(map);

      mapInstanceRef.current = map;
      leafletRef.current = L.default;
    });

    return () => {
      cancelled = true;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Actualizar marcadores
  useEffect(() => {
    const L = leafletRef.current;
    const map = mapInstanceRef.current;
    if (!L || !map) return;

    // Limpiar anteriores
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    withCoords.forEach((prop) => {
      const marker = L.circleMarker(
        [prop.latitude!, prop.longitude!],
        {
          radius: prop.is_opportunity ? 9 : 6,
          color: "white",
          weight: 2,
          fillColor: getMarkerColor(prop),
          fillOpacity: 0.85,
        }
      ).addTo(map);

      const scoreHtml = prop.is_opportunity
        ? `<p style="font-size:12px;font-weight:bold;color:#16a34a;margin-top:4px">Score: ${prop.opportunity_score}</p>`
        : "";

      marker.bindPopup(`
        <div style="min-width:200px;font-size:13px">
          <p style="font-weight:bold;margin-bottom:4px">${prop.title}</p>
          <p style="color:#666;margin-bottom:4px">${prop.commune}</p>
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-weight:bold">${formatUFShort(prop.price_uf)}</span>
            ${prop.m2_total ? `<span style="color:#888">${formatM2(prop.m2_total)}</span>` : ""}
          </div>
          ${prop.price_m2_uf ? `<p style="font-size:12px;color:#888">${prop.price_m2_uf.toFixed(1)} UF/m²</p>` : ""}
          ${scoreHtml}
          <a href="${prop.source_url}" target="_blank" rel="noopener noreferrer"
             style="font-size:12px;color:#2563eb;margin-top:4px;display:block">
            Ver en ${SOURCE_LABELS[prop.source] || prop.source}
          </a>
        </div>
      `);

      markersRef.current.push(marker);
    });
  }, [withCoords.length, commune, onlyOpps]);

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
      <div ref={mapContainerRef} style={{ flex: 1, minHeight: 0 }} />
    </div>
  );
}
