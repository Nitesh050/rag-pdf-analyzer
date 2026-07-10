export default function Message({ role, content }) {
  const isUser = role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${isUser ? 'bg-sky-500 text-white' : 'border border-white/10 bg-white/10 text-slate-200'}`}>
        {content}
      </div>
    </div>
  );
}
