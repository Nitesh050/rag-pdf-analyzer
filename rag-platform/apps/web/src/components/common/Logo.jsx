import { FaRobot } from "react-icons/fa";

function Logo() {
  return (
    <div className="flex flex-col items-center gap-4">

      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/40">

        <FaRobot className="text-4xl text-white" />

      </div>

      <div className="text-center">

        <h1 className="text-4xl font-bold text-white">
          RAG Studio
        </h1>

        <p className="mt-2 text-slate-400">
          AI Powered Knowledge Assistant
        </p>

      </div>

    </div>
  );
}

export default Logo;