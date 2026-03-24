"use client";
import { useFeedbackStats } from "@/lib/hooks/useAdmin";
import { KpiCard } from "@/components/admin/KpiCard";
import { ThumbsUp, ThumbsDown, Target, Activity } from "lucide-react";

export default function FeedbackPage() {
  const { data, isLoading, error } = useFeedbackStats();

  if (isLoading) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">Análisis de Feedback</h1>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border p-5 animate-pulse h-24" />
          ))}
        </div>
      </div>
    );
  }

  if (error) return <p className="text-red-500">Error cargando feedback</p>;

  const fp = data?.false_positive_rate;
  const isOk = data?.status === "OK";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Análisis de Feedback</h1>

      {/* KPIs */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard title="Total feedback" value={data?.total_feedback ?? 0} icon={Activity} />
        <KpiCard title="Buenas" value={data?.good ?? 0} icon={ThumbsUp} color="text-green-600" />
        <KpiCard title="Malas (FP)" value={data?.bad ?? 0} icon={ThumbsDown} color="text-red-600" />
        <KpiCard
          title="Tasa falsos positivos"
          value={fp !== null && fp !== undefined ? `${fp}%` : "N/D"}
          subtitle={`Target: ${data?.target || "< 30%"}`}
          icon={Target}
          color={isOk ? "text-green-600" : "text-red-600"}
        />
      </div>

      {/* Gauge visualization */}
      <div className="bg-white rounded-xl border p-6">
        <h3 className="font-semibold mb-6">Tasa de Falsos Positivos</h3>

        {data?.total_feedback === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">Sin feedback todavía</p>
            <p className="text-gray-400 text-sm mt-1">
              Los usuarios pueden evaluar oportunidades con /feedback en el bot de Telegram
            </p>
          </div>
        ) : (
          <div className="max-w-md mx-auto">
            {/* Simple bar gauge */}
            <div className="mb-4">
              <div className="flex justify-between text-sm mb-2">
                <span>0%</span>
                <span className="font-medium">
                  {fp !== null ? `${fp}%` : "N/D"}
                </span>
                <span>100%</span>
              </div>
              <div className="h-6 bg-gray-200 rounded-full overflow-hidden relative">
                {/* Target line at 30% */}
                <div className="absolute top-0 bottom-0 left-[30%] w-0.5 bg-red-500 z-10" />
                <div
                  className={`h-full rounded-full transition-all ${
                    isOk ? "bg-green-500" : "bg-red-500"
                  }`}
                  style={{ width: `${Math.min(fp || 0, 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span></span>
                <span className="text-red-500" style={{ marginLeft: "30%" }}>Target: 30%</span>
                <span></span>
              </div>
            </div>

            <div className={`text-center p-4 rounded-lg mt-4 ${
              isOk ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
            }`}>
              <p className="font-semibold text-lg">{isOk ? "OK" : "NECESITA AJUSTE"}</p>
              <p className="text-sm mt-1">
                {isOk
                  ? "La tasa de falsos positivos está dentro del rango aceptable"
                  : "Considera ajustar PRICE_DEVIATION_THRESHOLD u OPPORTUNITY_MIN_SCORE"
                }
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
