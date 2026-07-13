"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Overview" },
  { href: "/config", label: "Configure" },
  { href: "/docs", label: "Guides" },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-56 shrink-0 border-r border-white/10 bg-surface/80 backdrop-blur p-5 hidden md:flex flex-col">
      <div className="mb-8">
        <p className="text-[10px] uppercase tracking-widest text-accent font-semibold mb-1">Phase 0</p>
        <h1 className="font-serif text-2xl text-white">Scanner</h1>
      </div>
      <nav className="space-y-1 flex-1">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`block px-3 py-2 rounded-lg text-sm transition ${
              path === l.href
                ? "bg-accent/15 text-accent border border-accent/20"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
            }`}
          >
            {l.label}
          </Link>
        ))}
      </nav>
      <p className="text-[10px] text-zinc-600 mt-4">
        Vercel UI · scanner runs locally
      </p>
    </aside>
  );
}
