import { useState } from 'react';

export default function ChatInput({ onSend, loading }) {
  const [value, setValue] = useState('');

  function handleSubmit(event) {
    event.preventDefault();
    if (!value.trim()) return;
    onSend(value.trim());
    setValue('');
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto flex w-full max-w-3xl gap-2">
      <input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Ask something about your uploaded PDF"
        className="flex-1 rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-slate-100 outline-none ring-0 placeholder:text-slate-500 focus:border-sky-400"
      />
      <button
        type="submit"
        disabled={loading}
        className="rounded-2xl bg-sky-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? 'Sending...' : 'Send'}
      </button>
    </form>
  );
}
