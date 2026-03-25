"use client";
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { PropertyListItem } from "@/lib/types";
import { formatUFShort, formatM2 } from "@/lib/utils";
import { SANTIAGO_CENTER, SOURCE_LABELS } from "@/lib/constants";

function getMarkerColor(prop: PropertyListItem): string {
  if (prop.is_opportunity && (prop.opportunity_score ?? 0) >= 80) return "#ef4444";
  if (prop.is_opportunity) return "#22c55e";
  return "#3b82f6";
}

interface Props {
  properties: PropertyListItem[];
}

export default function LeafletMap({ properties }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  // Init map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current).setView(
      [SANTIAGO_CENTER.lat, SANTIAGO_CENTER.lng],
      12
    );

    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 19,
    }).addTo(map);

    markersLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    // Fix tiles not loading on initial render
    setTimeout(() => map.invalidateSize(), 100);

    return () => {
      map.remove();
      mapRef.current = null;
      markersLayerRef.current = null;
    };
  }, []);

  // Update markers when properties change
  useEffect(() => {
    if (!markersLayerRef.current) return;

    markersLayerRef.current.clearLayers();

    properties.forEach((prop) => {
      if (prop.latitude == null || prop.longitude == null) return;

      const marker = L.circleMarker([prop.latitude, prop.longitude], {
        radius: prop.is_opportunity ? 9 : 6,
        color: "white",
        weight: 2,
        fillColor: getMarkerColor(prop),
        fillOpacity: 0.85,
      });

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

      marker.addTo(markersLayerRef.current!);
    });
  }, [properties]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}
