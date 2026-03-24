"use client";
import { useMarketAverages } from "@/lib/hooks/useOpportunities";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { formatDate } from "@/lib/utils";
import { BarChart3 } from "lucide-react";

export default function MercadoPage() {
  const { data, isLoading, error } = useMarketAverages();

  if (isLoading) return <div className="max-w-7xl mx-auto px-4 py-12"><div className="animate-pulse h-96 bg-white rounded-xl border" /></div>;
  if (error) return <div className="max-w-7xl mx-auto px-4 py-12 text-center text-red-500">Error cargando datos de mercado</div>;

  const averages = data?.data || [];

  // Prepare chart data: group by commune
  const communes = [...new Set(averages.map((a) => a.commune))];
  const chartData = communes.map((commune) => {
    const d1 = averages.find((a) => a.commune === commune && a.bedrooms === 1);
    const d2 = averages.find((a) => a.commune === commune && a.bedrooms === 2);
    return {
      commune: commune.replace("Estación Central", "Est. Central"),
      "1D avg": d1?.avg_price_m2_uf || 0,
      "2D avg": d2?.avg_price_m2_uf || 0,
      "1D median": d1?.median_price_m2_uf || 0,
      "2D median": d2?.median_price_m2_uf || 0,
    };
  });

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Visión del Mercado</h1>
        <p className="text-gray-500 text-sm mt-1">
          Promedios de precio UF/m² por comuna y dormitorios
        </p>
      </div>

      {averages.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center">
          <BarChart3 className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">Aún no hay datos de mercado</p>
          <p className="text-gray-400 text-sm mt-1">El sistema necesita recopilar propiedades primero</p>
        </div>
      ) : (
        <>
          {/* Chart */}
          <div className="bg-white rounded-xl border shadow-sm p-6 mb-8">
            <h2 className="font-semibold mb-4">Promedio UF/m² por comuna</h2>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                  <XAxis dataKey="commune" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(v) => `${Number(v).toFixed(1)} UF/m²`} />
                  <Legend />
                  <Bar dataKey="1D avg" fill="#3b82f6" name="1 Dorm (promedio)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="2D avg" fill="#8b5cf6" name="2 Dorms (promedio)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Table */}
          <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
            <div className="p-4 border-b">
              <h2 className="font-semibold">Detalle por zona</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                  <tr>
                    <th className="px-4 py-3 text-left">Comuna</th>
                    <th className="px-4 py-3 text-center">Dorms</th>
                    <th className="px-4 py-3 text-right">Promedio</th>
                    <th className="px-4 py-3 text-right">Mediana</th>
                    <th className="px-4 py-3 text-right">Mínimo</th>
                    <th className="px-4 py-3 text-right">Máximo</th>
                    <th className="px-4 py-3 text-right">Muestra</th>
                    <th className="px-4 py-3 text-right">Actualizado</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {averages.map((a) => (
                    <tr key={`${a.commune}-${a.bedrooms}`} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium">{a.commune}</td>
                      <td className="px-4 py-3 text-center">{a.bedrooms}D</td>
                      <td className="px-4 py-3 text-right font-semibold">{a.avg_price_m2_uf.toFixed(1)}</td>
                      <td className="px-4 py-3 text-right">{a.median_price_m2_uf?.toFixed(1) || "N/D"}</td>
                      <td className="px-4 py-3 text-right text-green-600">{a.min_price_m2_uf?.toFixed(1) || "N/D"}</td>
                      <td className="px-4 py-3 text-right text-red-500">{a.max_price_m2_uf?.toFixed(1) || "N/D"}</td>
                      <td className="px-4 py-3 text-right">{a.sample_count}</td>
                      <td className="px-4 py-3 text-right text-xs text-gray-400">{formatDate(a.last_updated)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
