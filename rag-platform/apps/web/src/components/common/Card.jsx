function Card({ children }) {
  return (
    <div
      className="
        w-full
        max-w-md
        rounded-3xl
        border
        border-slate-700/50
        bg-slate-900/60
        backdrop-blur-xl
        p-8
        shadow-2xl
      "
    >
      {children}
    </div>
  );
}

export default Card;