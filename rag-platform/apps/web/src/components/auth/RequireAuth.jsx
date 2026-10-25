import { Navigate } from "react-router-dom";

import Loader from "../common/Loader";
import { useAuth } from "../../context/AuthContext";

// Wraps pages that need a logged-in user; everyone else goes to the login page.
function RequireAuth({ children }) {
  const { user, checking } = useAuth();

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <Loader />
      </div>
    );
  }

  return user ? children : <Navigate to="/" replace />;
}

export default RequireAuth;
