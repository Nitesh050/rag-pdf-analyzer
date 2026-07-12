function AuthLayout({ children }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-black flex items-center justify-center px-6">
      {children}
    </div>
  );
}

export default AuthLayout;