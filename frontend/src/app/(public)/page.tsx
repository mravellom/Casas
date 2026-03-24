"use client";
import Link from "next/link";
import { useHealth } from "@/lib/hooks/useAdmin";
import { useTopOpportunities } from "@/lib/hooks/useOpportunities";
import { OpportunityCard } from "@/components/opportunities/OpportunityCard";
import { TrendingUp, Search, Bell, BarChart3, MapPin, ArrowRight } from "lucide-react";

const FEATURES = [
  { icon: Search, title: "Scraping Automático", desc: "Monitoreamos Portal Inmobiliario y Yapo.cl cada 4 horas" },
  { icon: BarChart3, title: "Análisis de Mercado", desc: "Calculamos promedios UF/m² por comuna para detectar subvaloraciones" },
  { icon: Bell, title: "Alertas Instantáneas", desc: "Recibe oportunidades por Telegram antes que la competencia" },
];

const COMMUNES = [
  { name: "Santiago Centro", desc: "Alta rotación, buena conectividad" },
  { name: "San Miguel", desc: "Crecimiento acelerado" },
  { name: "Estación Central", desc: "Precios accesibles" },
  { name: "Ñuñoa", desc: "Zona consolidada" },
];

export default function LandingPage() {
  const { data: health } = useHealth();
  const { data: topOpps } = useTopOpportunities(3);

  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-br from-blue-600 to-blue-800 text-white">
        <div className="max-w-7xl mx-auto px-4 py-20 sm:py-28 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <h1 className="text-4xl sm:text-5xl font-bold leading-tight mb-6">
              Detectamos oportunidades inmobiliarias en Santiago antes que nadie
            </h1>
            <p className="text-xl text-blue-100 mb-8">
              Análisis automático de departamentos subvalorados en la Región Metropolitana.
              Datos en tiempo real para inversionistas inteligentes.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/oportunidades"
                className="inline-flex items-center gap-2 bg-white text-blue-700 px-6 py-3 rounded-lg font-semibold hover:bg-blue-50 transition-colors"
              >
                Ver oportunidades <ArrowRight className="h-5 w-5" />
              </Link>
              <Link
                href="/mercado"
                className="inline-flex items-center gap-2 border border-white/30 text-white px-6 py-3 rounded-lg font-semibold hover:bg-white/10 transition-colors"
              >
                Explorar mercado
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      {health && (
        <section className="max-w-7xl mx-auto px-4 -mt-8 sm:px-6 lg:px-8 relative z-10">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: "Propiedades rastreadas", value: health.properties_in_db },
              { label: "Comunas cubiertas", value: 4 },
              { label: "Actualizaciones/día", value: 6 },
              { label: "Rango de precio", value: "1.5K-4K UF" },
            ].map((s) => (
              <div key={s.label} className="bg-white rounded-xl border shadow-sm p-4 text-center">
                <p className="text-2xl font-bold text-gray-900">{s.value}</p>
                <p className="text-xs text-gray-500 mt-1">{s.label}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Features */}
      <section className="max-w-7xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
        <h2 className="text-2xl font-bold text-center mb-10">Cómo funciona</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="text-center">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-blue-100 text-blue-600 mb-4">
                <Icon className="h-7 w-7" />
              </div>
              <h3 className="font-semibold text-lg mb-2">{title}</h3>
              <p className="text-gray-500 text-sm">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Communes */}
      <section className="bg-white border-y">
        <div className="max-w-7xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-center mb-10">Comunas que monitoreamos</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {COMMUNES.map((c) => (
              <div key={c.name} className="border rounded-xl p-5 hover:border-blue-300 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <MapPin className="h-5 w-5 text-blue-500" />
                  <h3 className="font-semibold">{c.name}</h3>
                </div>
                <p className="text-sm text-gray-500">{c.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Top Opportunities */}
      {topOpps?.data && topOpps.data.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-2xl font-bold">Mejores oportunidades ahora</h2>
            <Link href="/oportunidades" className="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center gap-1">
              Ver todas <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {topOpps.data.map((opp) => (
              <OpportunityCard key={opp.id} opp={opp} />
            ))}
          </div>
        </section>
      )}

      {/* CTA */}
      <section className="bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 py-16 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold mb-4">Recibe alertas por Telegram</h2>
          <p className="text-gray-400 mb-8 max-w-xl mx-auto">
            Configura tus preferencias y recibe oportunidades directamente en tu celular.
            Máximo 5 alertas por día, solo las mejores.
          </p>
          <Link
            href="/oportunidades"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            <TrendingUp className="h-5 w-5" />
            Explorar oportunidades
          </Link>
        </div>
      </section>
    </div>
  );
}
