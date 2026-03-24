export const COMMUNES = [
  "Santiago Centro",
  "San Miguel",
  "Estación Central",
  "Ñuñoa",
] as const;

export const PRICE_RANGE = { min: 1500, max: 4000 } as const;
export const BEDROOMS = [1, 2] as const;
export const MIN_SCORE = 70;

export const SCORE_BADGES = {
  ORO: { min: 80, label: "Oro", color: "bg-yellow-500", text: "text-yellow-900" },
  PLATA: { min: 60, label: "Plata", color: "bg-gray-400", text: "text-gray-900" },
  BRONCE: { min: 0, label: "Bronce", color: "bg-amber-700", text: "text-amber-100" },
} as const;

export const SOURCE_LABELS: Record<string, string> = {
  portal_inmobiliario: "Portal Inmobiliario",
  mercadolibre_inmuebles: "ML Inmuebles",
  yapo: "Yapo.cl",
};

export const SANTIAGO_CENTER = { lat: -33.4489, lng: -70.6693 } as const;
export const DEFAULT_ZOOM = 12;
