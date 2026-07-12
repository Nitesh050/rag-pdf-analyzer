import { useState } from 'react';
import { uploadPdf } from '../../services/api';

export default function UploadCard({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleUpload(event) {
    event.preventDefault();
    if (!file) {
      setStatus('Please choose a PDF file first.');
      return;
    }

    setLoading(true);
    setStatus('');

    try {
      const result = await uploadPdf(file);
      setStatus(result.message || 'Upload successful.');
      onUploadSuccess?.(file.name);
    } catch (error) {
      setStatus(error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-900/80 p-5 shadow-2xl shadow-black/30 backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Upload document</h3>
          <p className="mt-1 text-sm text-slate-400">Drop in a PDF and start chatting with it instantly.</p>
        </div>
        <div className="rounded-full border border-sky-400/20 bg-sky-500/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.3em] text-sky-300">
          PDF
        </div>
      </div>

      <form onSubmit={handleUpload} className="mt-5 space-y-4">
        <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-950/70 px-4 py-8 text-center text-sm text-slate-400 transition hover:border-sky-400 hover:text-sky-300">
          <span className="text-base font-medium text-slate-200">{file ? file.name : 'Choose a PDF file'}</span>
          <span className="mt-1">Supports .pdf documents only</span>
          <input
            type="file"
            accept="application/pdf"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            className="hidden"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-2xl bg-sky-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? 'Uploading...' : 'Upload & index'}
        </button>
      </form>

      {status ? <p className="mt-4 text-sm text-slate-300">{status}</p> : null}
    </section>
  );
}
