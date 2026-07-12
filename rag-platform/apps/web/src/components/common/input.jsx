function Input({
  type = "text",
  placeholder,
  value,
  onChange,
}) {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      className="
        w-full
        rounded-xl
        border
        border-slate-700
        bg-slate-800
        px-4
        py-3
        text-white
        outline-none
        transition
        focus:border-cyan-500
      "
    />
  );
}

export default Input;