"use client";
import { usePipelineStatus, usePipelineLogs, useTriggerPipeline } from "@/lib/hooks/useAdmin";
import { Play, Activity, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function PipelinePage() {
  const { data: status } = usePipelineStatus();
  const { data: logs, isLoading } = usePipelineLogs(20);
  const trigger = useTriggerPipeline();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Control del Pipeline</h1>

      {/* Status + Trigger */}
      <div className="grid sm:grid-cols-2 gap-4 mb-8">
        <div className="bg-white rounded-xl border p-6">
          <h3 className="font-semibold mb-4">Estado actual</h3>
          {status && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${status.running ? "bg-yellow-400 animate-pulse" : "bg-green-500"}`} />
                <span className="font-medium">{status.running ? "Ejecutando..." : "Inactivo"}</span>
              </div>
              {status.last_run && (
                <p className="text-sm text-gray-500">Última ejecución: {formatDate(status.last_run)}</p>
              )}
              {status.last_error && (
                <p className="text-sm text-red-500">Error: {status.last_error}</p>
              )}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-6">
          <h3 className="font-semibold mb-4">Ejecutar manualmente</h3>
          <p className="text-sm text-gray-500 mb-4">
            Ejecuta el pipeline completo: scraping, dedup, pricing, scoring, alertas y limpieza.
          </p>
          <button
            onClick={() => trigger.mutate()}
            disabled={status?.running || trigger.isPending}
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
          >
            <Play className="h-4 w-4" />
            {trigger.isPending ? "Iniciando..." : status?.running ? "Pipeline en ejecución" : "Ejecutar pipeline"}
          </button>
          {trigger.isSuccess && (
            <p className="text-sm text-green-600 mt-2">Pipeline iniciado en background</p>
          )}
        </div>
      </div>

      {/* Logs */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="p-4 border-b">
          <h3 className="font-semibold">Historial de ejecuciones</h3>
        </div>
        {isLoading ? (
          <div className="p-6 animate-pulse h-64" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Fecha</th>
                  <th className="px-4 py-3 text-center">Estado</th>
                  <th className="px-4 py-3 text-right">Props</th>
                  <th className="px-4 py-3 text-right">Opps</th>
                  <th className="px-4 py-3 text-right">Alertas</th>
                  <th className="px-4 py-3 text-right">Duración</th>
                  <th className="px-4 py-3 text-left">Errores</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(logs?.runs || []).map((run, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs">{new Date(run.timestamp).toLocaleString("es-CL")}</td>
                    <td className="px-4 py-3 text-center">
                      {run.status === "success" ? (
                        <CheckCircle className="h-4 w-4 text-green-500 mx-auto" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 text-yellow-500 mx-auto" />
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">{run.properties_found}</td>
                    <td className="px-4 py-3 text-right">{run.opportunities_found}</td>
                    <td className="px-4 py-3 text-right">{run.alerts_sent}</td>
                    <td className="px-4 py-3 text-right">{run.duration_seconds.toFixed(1)}s</td>
                    <td className="px-4 py-3 text-xs text-red-500">
                      {run.errors.length > 0 ? run.errors.join(", ") : "-"}
                    </td>
                  </tr>
                ))}
                {(!logs?.runs || logs.runs.length === 0) && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                      No hay ejecuciones registradas
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
