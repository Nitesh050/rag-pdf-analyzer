import { createContext, useContext, useEffect, useState } from "react";

import * as api from "../services/api";

const AuthContext = createContext(null);

// Holds the logged-in user for the whole app. On page load it asks the API
// whether the saved token is still valid, so a refresh keeps you logged in.
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    api.getMe()
      .then((me) => {
        if (!me) api.setToken(null);
        setUser(me);
      })
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  async function login(email, password) {
    const result = await api.login(email, password);
    api.setToken(result.access_token);
    setUser(result.user);
  }

  async function signup(email, password, displayName) {
    await api.signup(email, password, displayName);
    await login(email, password);
  }

  async function logout() {
    await api.logout();
    api.setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, checking, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
