import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatUF(value: number | null): string {
  if (value === null) return "N/D";
  return `${value.toLocaleString("es-CL")} UF`;
}

export function formatUFShort(value: number | null): string {
  if (value === null) return "N/D";
  return `${Math.round(value).toLocaleString("es-CL")} UF`;
}

export function formatPct(value: number | null): string {
  if (value === null) return "N/D";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function formatM2(value: number | null): string {
  if (value === null) return "N/D";
  return `${Math.round(value)} m²`;
}

export function formatDate(iso: string | null): string {
  if (!iso) return "N/D";
  return new Date(iso).toLocaleDateString("es-CL", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTimeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "Hace menos de 1 hora";
  if (hours < 24) return `Hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `Hace ${days}d`;
}

export function getScoreBadge(score: number | null) {
  if (score === null) return { label: "Sin score", color: "bg-gray-200", text: "text-gray-600" };
  if (score >= 80) return { label: "Oro", color: "bg-yellow-500", text: "text-yellow-900" };
  if (score >= 60) return { label: "Plata", color: "bg-gray-400", text: "text-gray-900" };
  return { label: "Bronce", color: "bg-amber-700", text: "text-amber-100" };
}
