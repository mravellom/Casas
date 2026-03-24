"use client";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { PropertyListItem } from "@/lib/types";
import { formatUFShort, formatM2, getScoreBadge } from "@/lib/utils";
import { SANTIAGO_CENTER, DEFAULT_ZOOM } from "@/lib/constants";

// Fix leaflet default icon issue in Next.js
const createIcon = (color: string) =>
  L.divIcon({
    className: "custom-marker",
    html: `<div style="width:12px;height:12px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3)"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });

const greenIcon = createIcon("#22c55e");
const blueIcon = createIcon("#3b82f6");
const redIcon = createIcon("#ef4444");

function getMarkerIcon(prop: PropertyListItem) {
  if (prop.is_opportunity && (prop.opportunity_score ?? 0) >= 80) return redIcon;
  if (prop.is_opportunity) return greenIcon;
  return blueIcon;
}

interface PropertyMapProps {
  properties: PropertyListItem[];
}

export default function PropertyMap({ properties }: PropertyMapProps) {
  const propsWithCoords = properties.filter(
    (p) => p.address // We use address as proxy since lat/lng may be null
  );

  return (
    <MapContainer
      center={[SANTIAGO_CENTER.lat, SANTIAGO_CENTER.lng]}
      zoom={DEFAULT_ZOOM}
      className="h-full w-full"
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />
      {/* Note: Markers will only show for properties with lat/lng coordinates.
          The scrapers need to extract coordinates for map functionality. */}
    </MapContainer>
  );
}
