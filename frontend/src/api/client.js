/**
 * Thin API Client for GraphTech Backend.
 * Uses environment variable VITE_API_BASE_URL (defaults to http://localhost:8000).
 *
 * All fetch calls use credentials: 'include' so the httpOnly session cookie is
 * sent automatically on every request.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const defaultOptions = {
  credentials: 'include', // send httpOnly cookie on every request
  headers: { 'Content-Type': 'application/json' },
};

// ── Health ────────────────────────────────────────────────────────────────────

/**
 * Perform a health check call to the backend.
 * @returns {Promise<{status: string}>}
 */
export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health`, defaultOptions);
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

/**
 * Returns the URL to redirect the browser to for Google OAuth login.
 * The backend will redirect to Google — no fetch needed.
 */
export function getGoogleLoginUrl() {
  return `${API_BASE_URL}/api/auth/google/login`;
}

/**
 * Check whether the user has an active session.
 * Returns the user object if authenticated, or null if not.
 * @returns {Promise<object|null>}
 */
export async function getSession() {
  const response = await fetch(`${API_BASE_URL}/api/auth/session`, defaultOptions);
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Session check failed: ${response.status}`);
  }
  return response.json();
}

/**
 * Clear the session by deleting the httpOnly cookie on the server.
 * @returns {Promise<void>}
 */
export async function logout() {
  const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
    ...defaultOptions,
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Logout failed: ${response.status}`);
  }
}

// ── Me (protected) ────────────────────────────────────────────────────────────

/**
 * Fetch the authenticated user's profile from the protected /api/me route.
 * Returns null on 401 (no session / expired session).
 * @returns {Promise<object|null>}
 */
export async function getMe() {
  const response = await fetch(`${API_BASE_URL}/api/me`, defaultOptions);
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`GET /api/me failed: ${response.status}`);
  }
  return response.json();
}
