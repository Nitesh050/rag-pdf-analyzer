import React from 'react';
import { FaComments, FaFilePdf, FaPlus, FaRobot } from 'react-icons/fa';

const Sidebar = ({ uploadedFile }) => {
  return (
    <aside className="hidden w-72 flex-col border-r border-white/10 bg-slate-950/90 p-4 lg:flex">
      <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/10 px-3 py-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-500/20 text-sky-300">
          <FaRobot />
        </div>
        <div>
          <p className="text-sm font-semibold">RAG Assistant</p>
          <p className="text-xs text-slate-400">Smart document Q&A</p>
        </div>
      </div>

      <button className="mt-5 flex items-center justify-center gap-2 rounded-2xl bg-sky-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-600">
        <FaPlus />
        New chat
      </button>

      <div className="mt-6">
        <p className="mb-3 text-xs uppercase tracking-[0.3em] text-slate-500">Recent chats</p>
        <div className="space-y-2">
          <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-slate-300">
            <div className="flex items-center gap-2">
              <FaComments />
              <span>Summarize this document</span>
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-slate-300">
            <div className="flex items-center gap-2">
              <FaComments />
              <span>Extract key takeaways</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <p className="mb-3 text-xs uppercase tracking-[0.3em] text-slate-500">Documents</p>
        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 px-3 py-3 text-sm text-emerald-200">
          <div className="flex items-center gap-2">
            <FaFilePdf />
            <span>{uploadedFile || 'No document uploaded'}</span>
          </div>
        </div>
      </div>

      <div className="mt-auto rounded-2xl border border-white/10 bg-white/5 p-3 text-sm text-slate-400">
        Upload a PDF and chat with it in the same workspace.
      </div>
    </aside>
  );
};

export default Sidebar;