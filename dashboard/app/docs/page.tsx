import Link from "next/link";

const guides = [
  { href: "/docs/complete-workflow-guide.html", title: "Complete Workflow", desc: "Daily process & sizing" },
  { href: "/docs/tools-reference.html", title: "Tools Reference", desc: "Bubblemaps, DexScreener…" },
  { href: "/docs/low-float-playbook.html", title: "Low-Float Playbook", desc: "LAB / SIREN patterns" },
  { href: "/docs/alert-spotting-guide.html", title: "Alert & Spotting", desc: "Rise vs fall" },
  { href: "/docs/cashcat-case-study.html", title: "CASHCAT Case Study", desc: "Phase 0 example" },
  { href: "/docs/index.html", title: "All guides", desc: "Learning hub" },
];

export default function DocsPage() {
  return (
    <div>
      <header className="mb-8">
        <h1 className="font-serif text-4xl text-white mb-2">Guides</h1>
        <p className="text-zinc-400 text-sm">Static HTML from the repo — open in new tab.</p>
      </header>
      <div className="grid gap-3">
        {guides.map((g) => (
          <a
            key={g.href}
            href={g.href}
            target="_blank"
            rel="noreferrer"
            className="card block hover:border-accent/30 transition"
          >
            <h3 className="font-serif text-lg text-white">{g.title}</h3>
            <p className="text-sm text-zinc-500">{g.desc}</p>
          </a>
        ))}
      </div>
      <p className="mt-6 text-sm text-zinc-600">
        On Vercel: add <code>public/docs</code> symlink or copy docs at build — see dashboard README.
      </p>
      <Link href="/" className="btn-ghost mt-4 inline-flex">← Back</Link>
    </div>
  );
}
