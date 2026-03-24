"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { LayoutDashboard, Building2, Play, MessageSquare, ArrowLeft } from "lucide-react";

const ADMIN_ITEMS = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/propiedades", label: "Propiedades", icon: Building2 },
  { href: "/admin/pipeline", label: "Pipeline", icon: Play },
  { href: "/admin/feedback", label: "Feedback", icon: MessageSquare },
];

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen hidden lg:block">
      <div className="p-4">
        <Link href="/" className="flex items-center gap-2 text-gray-400 hover:text-white text-sm mb-6">
          <ArrowLeft className="h-4 w-4" />
          Volver al sitio
        </Link>
        <h2 className="text-lg font-bold mb-6">Admin Panel</h2>
        <nav className="space-y-1">
          {ADMIN_ITEMS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                pathname === href
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:bg-gray-800 hover:text-white"
              )}
            >
              <Icon className="h-5 w-5" />
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  );
}
