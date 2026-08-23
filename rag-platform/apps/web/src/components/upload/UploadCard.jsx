import { useState } from 'react';
import { uploadPdf, uploadUrl } from '../../services/api';

export default function UploadCard({ onUploadSuccess }) {
  const [mode, setMode] = useState('pdf');
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);

  function switchMode(nextMode) {
    setMode(nextMode);
    setStatus('');
  }

  async function handleUpload(event) {
    event.preventDefault();

    if (mode === 'pdf') {
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

      return;
    }

    const trimmedUrl = url.trim();
    if (!trimmedUrl) {
      setStatus('Please enter a URL first.');
      return;
    }

    setLoading(true);
    setStatus('');

    try {
      const result = await uploadUrl(trimmedUrl);
      setStatus(result.message || 'Page indexed successfully.');
      onUploadSuccess?.(trimmedUrl);
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
          <h3 className="text-lg font-semibold text-white">Add a source</h3>
          <p className="mt-1 text-sm text-slate-400">Upload a PDF or index a web page and start chatting with it instantly.</p>
        </div>
        <div className="flex rounded-full border border-white/10 bg-slate-950/70 p-1 text-xs font-medium uppercase tracking-[0.3em]">
          <button
            type="button"
            onClick={() => switchMode('pdf')}
            className={`rounded-full px-3 py-1 transition ${
              mode === 'pdf' ? 'bg-sky-500/20 text-sky-300' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            PDF
          </button>
          <button
            type="button"
            onClick={() => switchMode('url')}
            className={`rounded-full px-3 py-1 transition ${
              mode === 'url' ? 'bg-sky-500/20 text-sky-300' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            URL
          </button>
        </div>
      </div>

      <form onSubmit={handleUpload} className="mt-5 space-y-4">
        {mode === 'pdf' ? (
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
        ) : (
          <input
            type="url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://example.com/article"
            className="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-sm text-slate-200 placeholder:text-slate-500 outline-none transition focus:border-sky-400"
          />
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-2xl bg-sky-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? 'Indexing...' : mode === 'pdf' ? 'Upload & index' : 'Fetch & index'}
        </button>
      </form>

      {status ? <p className="mt-4 text-sm text-slate-300">{status}</p> : null}
    </section>
  );
}
