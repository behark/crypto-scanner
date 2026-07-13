import { ConfigForm } from "@/components/ConfigForm";

export default function ConfigPage() {
  return (
    <div>
      <header className="mb-8">
        <p className="text-xs uppercase tracking-widest text-accent font-semibold mb-2">Settings</p>
        <h1 className="font-serif text-4xl text-white mb-2">Configure scanner</h1>
        <p className="text-zinc-400 text-sm">
          Changes apply after save → copy to scanner or enable remote config pull.
        </p>
      </header>
      <ConfigForm />
    </div>
  );
}
