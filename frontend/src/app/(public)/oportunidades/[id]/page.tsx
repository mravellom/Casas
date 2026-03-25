"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getProperty } from "@/lib/api";
import { useMarketAverages } from "@/lib/hooks/useOpportunities";
import { ScoreBadge } from "@/components/opportunities/ScoreBadge";
import { formatUFShort, formatM2, formatDate } from "@/lib/utils";
import { SOURCE_LABELS } from "@/lib/constants";
import { MapPin, Bed, Bath, Building2, Car, Package, ExternalLink, ArrowLeft, FileDown } from "lucide-react";
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

        {/* Rentability */}
        {prop.rentability && (
          <div className="p-6 border-b">
            <div className="flex items-center gap-2 mb-4">
              <h3 className="font-semibold">Proyección de Inversión</h3>
              {prop.rentability.is_high_rentability && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-green-100 text-green-700">
                  Alta Rentabilidad
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500 mb-1">Arriendo estimado</p>
                <p className="text-lg font-bold text-gray-900">{prop.rentability.estimated_rent_uf} UF</p>
                <p className="text-xs text-gray-400">/mes</p>
              </div>
              <div className={`rounded-lg p-3 text-center ${prop.rentability.cap_rate > 6 ? "bg-green-50" : "bg-gray-50"}`}>
                <p className="text-xs text-gray-500 mb-1">Cap Rate</p>
                <p className={`text-lg font-bold ${prop.rentability.cap_rate > 6 ? "text-green-600" : "text-gray-900"}`}>
                  {prop.rentability.cap_rate}%
                </p>
                <p className="text-xs text-gray-400">bruto anual</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500 mb-1">Payback</p>
                <p className="text-lg font-bold text-gray-900">{prop.rentability.payback_years}</p>
                <p className="text-xs text-gray-400">años</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500 mb-1">Flujo mensual</p>
                <p className={`text-lg font-bold ${prop.rentability.monthly_cashflow_uf > 0 ? "text-green-600" : "text-red-500"}`}>
                  {prop.rentability.monthly_cashflow_uf > 0 ? "+" : ""}{prop.rentability.monthly_cashflow_uf} UF
                </p>
                <p className="text-xs text-gray-400">neto</p>
              </div>
            </div>
            <div className="mt-3 text-xs text-gray-400">
              ROI neto anual: {prop.rentability.roi_annual}% | Gastos comunes est: {prop.rentability.monthly_expenses_uf} UF/mes
            </div>
          </div>
        )}

        {/* Neighborhood */}
        {prop.neighborhood && (
          <div className="p-6 border-b">
            <div className="flex items-center gap-2 mb-4">
              <h3 className="font-semibold">Inteligencia de Barrio</h3>
              {prop.neighborhood.is_master_buy && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-700">
                  Compra Maestra
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {/* Metro actual */}
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">Metro más cercano</p>
                {prop.neighborhood.nearest_metro ? (
                  <>
                    <p className="text-sm font-bold">{prop.neighborhood.nearest_metro.name}</p>
                    <p className="text-xs text-gray-500">
                      {prop.neighborhood.nearest_metro.distance_m}m ({prop.neighborhood.nearest_metro.walk_minutes} min caminando)
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-gray-400">No encontrado</p>
                )}
              </div>

              {/* Servicios */}
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">Servicios (500m)</p>
                <p className="text-sm">
                  {prop.neighborhood.services_500m.supermarkets} supermercados
                </p>
                <p className="text-sm">
                  {prop.neighborhood.services_500m.pharmacies} farmacias
                </p>
                <p className="text-sm">
                  {prop.neighborhood.services_500m.parks} parques
                </p>
              </div>

              {/* Futuro metro */}
              <div className={`rounded-lg p-3 ${prop.neighborhood.future_metro ? "bg-purple-50" : "bg-gray-50"}`}>
                <p className="text-xs text-gray-500 mb-1">Futuro Metro</p>
                {prop.neighborhood.future_metro ? (
                  <>
                    <p className="text-sm font-bold text-purple-700">
                      {prop.neighborhood.future_metro.line} - {prop.neighborhood.future_metro.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {prop.neighborhood.future_metro.distance_m}m ({prop.neighborhood.future_metro.walk_minutes} min)
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-gray-400">Sin estaciones cercanas</p>
                )}
              </div>
            </div>

            {/* Connectivity Score */}
            <div className="mt-3 flex items-center gap-3">
              <span className="text-xs text-gray-500">Conectividad:</span>
              <div className="flex-1 h-2 bg-gray-200 rounded-full max-w-[200px]">
                <div
                  className="h-2 rounded-full bg-blue-500"
                  style={{ width: `${prop.neighborhood.connectivity_score}%` }}
                />
              </div>
              <span className="text-xs font-medium">{prop.neighborhood.connectivity_score}/100</span>
            </div>
          </div>
        )}

        {/* Direct Owner / Quality */}
        {prop.is_direct_owner && (
          <div className="px-6 py-3 border-b bg-green-50">
            <span className="text-sm font-medium text-green-700">
              Dueño Directo — Sin comisión de corredor
            </span>
          </div>
        )}

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
          <div className="flex gap-3">
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/reports/property/${prop.id}/pdf`}
              className="inline-flex items-center gap-2 border border-gray-300 text-gray-700 px-4 py-2.5 rounded-lg font-medium hover:bg-gray-50 text-sm"
            >
              <FileDown className="h-4 w-4" /> Descargar PDF
            </a>
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
    </div>
  );
}
