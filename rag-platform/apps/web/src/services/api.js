const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const TOKEN_KEY = 'rag_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

// Every request carries the login token, so the API knows who is asking.
function authHeaders(headers = {}) {
  const token = getToken();
  return token ? { ...headers, Authorization: `Bearer ${token}` } : headers;
}

async function errorFrom(response, fallback) {
  const error = await response.json().catch(() => ({}));
  // FastAPI sends a string for HTTPException and a list for validation errors.
  const detail = Array.isArray(error.detail) ? error.detail[0]?.msg : error.detail;
  return new Error(detail || fallback);
}

export async function signup(email, password, displayName) {
  const response = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName || null }),
  });

  if (!response.ok) throw await errorFrom(response, 'Sign up failed');
  return response.json();
}

export async function login(email, password) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) throw await errorFrom(response, 'Login failed');
  return response.json();
}

// Returns the logged-in user, or null when the token is missing or no longer valid.
export async function getMe() {
  if (!getToken()) return null;

  const response = await fetch(`${API_BASE_URL}/auth/me`, { headers: authHeaders() });

  if (response.status === 401) return null;
  if (!response.ok) throw await errorFrom(response, 'Could not load account');
  return response.json();
}

export async function logout() {
  await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', headers: authHeaders() }).catch(() => {});
}

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) throw await errorFrom(response, 'Upload failed');
  return response.json();
}

export async function uploadUrl(url) {
  const response = await fetch(`${API_BASE_URL}/upload/url`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ url }),
  });

  if (!response.ok) throw await errorFrom(response, 'URL ingestion failed');
  return response.json();
}

export async function chatWithPdf(question, documentId) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    // Scope retrieval to the active document; without it the backend
    // searches every uploaded document.
    body: JSON.stringify({ question, document_id: documentId ?? null }),
  });

  if (!response.ok) throw await errorFrom(response, 'Chat failed');
  return response.json();
}
