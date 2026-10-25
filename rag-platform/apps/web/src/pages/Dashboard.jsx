import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/layout/Sidebar';
import UploadCard from '../components/upload/UploadCard';
import ChatBox from '../components/chat/ChatBox';
import ChatInput from '../components/chat/ChatInput';
import { chatWithPdf } from '../services/api';
import { useAuth } from '../context/AuthContext';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [documentId, setDocumentId] = useState(null);

  async function handleSend(question) {
    setLoading(true);
    setMessages((prev) => [...prev, { role: 'user', content: question }]);

    try {
      const result = await chatWithPdf(question, documentId);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.answer, sources: result.sources || [] },
      ]);
      setSources(result.sources || []);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: error.message || 'Something went wrong.' },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.15),_transparent_35%),linear-gradient(135deg,_#07111f_0%,_#0f172a_100%)] text-slate-100">
      <Sidebar uploadedFile={uploadedFile} />

      <main className="flex flex-1 flex-col">
        <header className="border-b border-white/10 px-6 py-4 backdrop-blur md:px-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-sky-300">AI RAG Studio</p>
              <h1 className="text-xl font-semibold">Ask questions from your uploaded documents</h1>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-3">
              <div className="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-sm text-slate-300">
                {uploadedFile ? `Active file: ${uploadedFile}` : 'No document loaded yet'}
              </div>
              <span className="text-sm text-slate-400">{user?.display_name || user?.email}</span>
              <button
                onClick={async () => {
                  await logout();
                  navigate('/');
                }}
                className="rounded-full border border-white/10 px-3 py-1 text-sm text-slate-300 transition hover:bg-white/10"
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        <section className="flex flex-1 flex-col gap-4 overflow-hidden p-4 md:p-6 lg:flex-row lg:p-8">
          <div className="flex-1 overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 shadow-2xl shadow-black/30">
            <ChatBox messages={messages} sources={sources} />
            <div className="border-t border-white/10 bg-slate-900/70 p-3 md:p-4">
              <ChatInput onSend={handleSend} loading={loading} />
            </div>
          </div>

          <div className="w-full shrink-0 lg:w-[360px]">
            <UploadCard
              onUploadSuccess={(name, id) => {
                setUploadedFile(name);
                setDocumentId(id ?? null);
              }}
            />
          </div>
        </section>
      </main>
    </div>
  );
};

export default Dashboard;