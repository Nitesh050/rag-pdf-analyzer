function Button({
  children,
  type = "button",
  onClick,
  disabled = false,
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className="
        w-full
        rounded-xl
        bg-cyan-500
        py-3
        text-lg
        font-semibold
        text-white
        transition
        duration-300
        hover:bg-cyan-400
        disabled:cursor-not-allowed
        disabled:opacity-50
      "
    >
      {children}
    </button>
  );
}

export default Button;