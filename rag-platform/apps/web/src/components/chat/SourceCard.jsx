export default function SourceCard({ source }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/80 p-3 text-sm text-slate-300">
      <div className="font-medium text-white">{source.source || 'Source'}</div>
      <div className="mt-1 text-xs text-slate-500">Page {source.page ?? 'n/a'}</div>
    </div>
  );
}
