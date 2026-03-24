"use client";
import { useMetrics, usePipelineStatus } from "@/lib/hooks/useAdmin";
import { KpiCard } from "@/components/admin/KpiCard";
import { Building2, TrendingUp, Users, Bell, Activity } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

const PIE_COLORS = ["#3b82f6", "#8b5cf6", "#f59e0b", "#22c55e"];

export default function AdminDashboard() {
  const { data: metrics, isLoading } = useMetrics();
  const { data: pipelineStatus } = usePipelineStatus();

  if (isLoading) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border p-5 animate-pulse h-24" />
          ))}
        </div>
      </div>
    );
  }

  if (!metrics) return <p className="text-red-500">Error cargando métricas</p>;

  const communeData = Object.entries(metrics.properties.by_commune).map(([name, count]) => ({
    name: name.replace("Estación Central", "Est. Central"),
    value: count,
  }));

  const sourceData = Object.entries(metrics.properties.by_source).map(([name, count]) => ({
    name: name === "portal_inmobiliario" ? "Portal Inmob." : name === "mercadolibre_inmuebles" ? "ML Inmuebles" : name,
    value: count,
  }));

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        {pipelineStatus && (
          <span className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-full ${
            pipelineStatus.running
              ? "bg-yellow-100 text-yellow-700"
              : "bg-green-100 text-green-700"
          }`}>
            <Activity className="h-3.5 w-3.5" />
            {pipelineStatus.running ? "Pipeline ejecutando..." : "Pipeline inactivo"}
          </span>
        )}
      </div>

      {/* KPIs */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard title="Propiedades activas" value={metrics.properties.total_active} subtitle={`${metrics.properties.new_today} nuevas hoy`} icon={Building2} />
        <KpiCard title="Oportunidades" value={metrics.opportunities.active} subtitle={`${metrics.opportunities.detected_today} detectadas hoy`} icon={TrendingUp} color="text-green-600" />
        <KpiCard title="Usuarios" value={metrics.users.active} subtitle={`${metrics.users.total} registrados`} icon={Users} color="text-purple-600" />
        <KpiCard title="Alertas hoy" value={metrics.alerts.sent_today} subtitle={`${metrics.alerts.sent_this_week} esta semana`} icon={Bell} color="text-orange-600" />
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-6 mb-8">
        {/* By commune */}
        <div className="bg-white rounded-xl border p-5">
          <h3 className="font-semibold mb-4">Propiedades por comuna</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={communeData} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={100} />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* By source */}
        <div className="bg-white rounded-xl border p-5">
          <h3 className="font-semibold mb-4">Propiedades por fuente</h3>
          <div className="h-64 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={sourceData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                  {sourceData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent pipeline runs */}
      {metrics.pipeline.last_runs.length > 0 && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="p-4 border-b">
            <h3 className="font-semibold">Últimas ejecuciones del pipeline</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Fecha</th>
                  <th className="px-4 py-3 text-center">Estado</th>
                  <th className="px-4 py-3 text-right">Propiedades</th>
                  <th className="px-4 py-3 text-right">Oportunidades</th>
                  <th className="px-4 py-3 text-right">Alertas</th>
                  <th className="px-4 py-3 text-right">Duración</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {metrics.pipeline.last_runs.map((run, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs">{new Date(run.timestamp).toLocaleString("es-CL")}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        run.status === "success" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
                      }`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">{run.properties_found}</td>
                    <td className="px-4 py-3 text-right">{run.opportunities_found}</td>
                    <td className="px-4 py-3 text-right">{run.alerts_sent}</td>
                    <td className="px-4 py-3 text-right">{run.duration_seconds.toFixed(1)}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
