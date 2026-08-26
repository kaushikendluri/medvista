"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/patients", label: "Patients" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-base-700/60 bg-base-900/60">
      <div className="flex items-center gap-2 px-5 py-5">
        <span className="h-2 w-2 rounded-full bg-accent shadow-[0_0_12px_2px_rgba(77,217,232,0.6)]" />
        <span className="text-sm font-semibold tracking-wide text-slate-100">MEDVISTA</span>
      </div>
      <nav className="flex flex-col gap-0.5 px-3">
        {NAV_ITEMS.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "focus-ring rounded-md px-3 py-2 text-sm transition",
                active
                  ? "bg-accent/10 text-accent"
                  : "text-slate-400 hover:bg-base-800 hover:text-slate-200",
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto px-5 py-4 text-[10px] leading-relaxed text-slate-600">
        Research / prototype system.
        <br />
        AI output requires physician review.
      </div>
    </aside>
  );
}
