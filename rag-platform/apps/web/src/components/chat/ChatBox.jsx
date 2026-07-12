import Message from './Message';
import SourceCard from './SourceCard';

export default function ChatBox({ messages, sources }) {
  return (
    <div className="flex h-[calc(100vh-260px)] flex-col overflow-y-auto px-4 py-4 md:px-6">
      {messages.length === 0 ? (
        <div className="m-auto max-w-2xl rounded-3xl border border-white/10 bg-white/5 p-8 text-center text-slate-300">
          <h3 className="text-xl font-semibold text-white">How can I help today?</h3>
          <p className="mt-2 text-sm text-slate-400">Upload a PDF and ask anything about it. I’ll pull the relevant passages and answer clearly.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {messages.map((message, index) => (
            <div key={index} className="space-y-2">
              <Message role={message.role} content={message.content} />
              {message.role === 'assistant' && message.sources?.length ? (
                <div className="ml-2 flex flex-wrap gap-2">
                  {message.sources.map((source, sourceIndex) => (
                    <SourceCard key={`${sourceIndex}-${source.source}`} source={source} />
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}

      {sources.length ? (
        <div className="mt-4 rounded-2xl border border-sky-400/20 bg-sky-500/10 p-3">
          <div className="text-sm font-medium text-sky-200">Relevant sources</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {sources.map((source, index) => (
              <SourceCard key={`${index}-${source.source}`} source={source} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
