import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: LucideIcon;
  color?: string;
}

export function KpiCard({ title, value, subtitle, icon: Icon, color = "text-blue-600" }: KpiCardProps) {
  return (
    <div className="bg-white rounded-xl border p-5 shadow-sm">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        <div className={cn("p-2.5 rounded-lg bg-gray-50", color)}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}
