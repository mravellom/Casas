"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getProperty } from "@/lib/api";
import { useMarketAverages } from "@/lib/hooks/useOpportunities";
import { ScoreBadge } from "@/components/opportunities/ScoreBadge";
import { formatUFShort, formatM2, formatDate } from "@/lib/utils";
import { SOURCE_LABELS } from "@/lib/constants";
import { MapPin, Bed, Bath, Building2, Car, Package, ExternalLink, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function PropertyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: prop, isLoading, error } = useQuery({
    queryKey: ["property", id],
    queryFn: () => getProperty(id),
  });
  const { data: marketData } = useMarketAverages(prop?.commune);

  if (isLoading) return <div className="max-w-4xl mx-auto px-4 py-12"><div className="animate-pulse h-96 bg-white rounded-xl border" /></div>;
  if (error || !prop) return <div className="max-w-4xl mx-auto px-4 py-12 text-center text-red-500">Error cargando propiedad</div>;

  const marketAvg = marketData?.data?.find((m) => m.commune === prop.commune && m.bedrooms === prop.bedrooms);
  const avgM2 = marketAvg?.avg_price_m2_uf;
  const pctBelow = avgM2 && prop.price_m2_uf ? ((prop.price_m2_uf - avgM2) / avgM2) * 100 : null;
  const estimatedValue = avgM2 && prop.m2_total ? avgM2 * prop.m2_total : null;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 sm:px-6">
      <Link href="/oportunidades" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-6">
        <ArrowLeft className="h-4 w-4" /> Volver a oportunidades
      </Link>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b">
          <div className="flex flex-wrap justify-between items-start gap-4">
            <div>
              <h1 className="text-xl font-bold text-gray-900 mb-2">{prop.title}</h1>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <MapPin className="h-4 w-4" />
                {prop.commune}
                {prop.address && <span>· {prop.address}</span>}
              </div>
            </div>
            <ScoreBadge score={prop.opportunity_score} />
          </div>
        </div>

        {/* Price section */}
        <div className="grid sm:grid-cols-2 gap-6 p-6 border-b bg-gray-50">
          <div>
            <p className="text-sm text-gray-500 mb-1">Precio publicado</p>
            <p className="text-3xl font-bold text-gray-900">{formatUFShort(prop.price_uf)}</p>
            {prop.price_m2_uf && <p className="text-sm text-gray-500 mt-1">{prop.price_m2_uf.toFixed(1)} UF/m²</p>}
          </div>
          {avgM2 && (
            <div>
              <p className="text-sm text-gray-500 mb-1">Promedio de la zona</p>
              <p className="text-3xl font-bold text-gray-400">{estimatedValue ? formatUFShort(estimatedValue) : "N/D"}</p>
              <p className="text-sm text-gray-500 mt-1">{avgM2.toFixed(1)} UF/m² promedio</p>
              {pctBelow !== null && (
                <p className={`text-sm font-bold mt-2 ${pctBelow < 0 ? "text-green-600" : "text-red-500"}`}>
                  {pctBelow > 0 ? "+" : ""}{pctBelow.toFixed(1)}% vs mercado
                </p>
              )}
            </div>
          )}
        </div>

        {/* Attributes */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-6 border-b">
          {prop.m2_total && (
            <div className="flex items-center gap-2 text-sm">
              <Building2 className="h-4 w-4 text-gray-400" />
              {formatM2(prop.m2_total)}
            </div>
          )}
          {prop.bedrooms && (
            <div className="flex items-center gap-2 text-sm">
              <Bed className="h-4 w-4 text-gray-400" />
              {prop.bedrooms} dormitorio{prop.bedrooms > 1 ? "s" : ""}
            </div>
          )}
          {prop.bathrooms && (
            <div className="flex items-center gap-2 text-sm">
              <Bath className="h-4 w-4 text-gray-400" />
              {prop.bathrooms} baño{prop.bathrooms > 1 ? "s" : ""}
            </div>
          )}
          {prop.floor !== null && (
            <div className="flex items-center gap-2 text-sm">
              <Building2 className="h-4 w-4 text-gray-400" />
              Piso {prop.floor}
            </div>
          )}
          <div className="flex items-center gap-2 text-sm">
            <Car className="h-4 w-4 text-gray-400" />
            Estacionamiento: {prop.has_parking ? "Sí" : prop.has_parking === false ? "No" : "N/D"}
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Package className="h-4 w-4 text-gray-400" />
            Bodega: {prop.has_bodega ? "Sí" : prop.has_bodega === false ? "No" : "N/D"}
          </div>
        </div>

        {/* Tags */}
        <div className="p-6 border-b flex flex-wrap gap-2">
          <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
            {SOURCE_LABELS[prop.source] || prop.source}
          </span>
          {prop.has_urgency_keyword && (
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
              Urgencia detectada
            </span>
          )}
          {prop.is_opportunity && (
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
              Oportunidad
            </span>
          )}
        </div>

        {/* Description */}
        {prop.description && (
          <div className="p-6 border-b">
            <h3 className="font-semibold mb-2">Descripción</h3>
            <p className="text-sm text-gray-600 whitespace-pre-line">{prop.description}</p>
          </div>
        )}

        {/* Footer */}
        <div className="p-6 flex flex-wrap justify-between items-center gap-4">
          <div className="text-xs text-gray-400">
            <p>Detectado: {formatDate(prop.first_seen_at)}</p>
            <p>Última vez visto: {formatDate(prop.last_seen_at)}</p>
          </div>
          <a
            href={prop.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-blue-700 text-sm"
          >
            Ver anuncio original <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </div>
    </div>
  );
}
