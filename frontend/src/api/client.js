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

// ── Diagram Generation (Sprint 3) ─────────────────────────────────────────────

/**
 * Generate a diagram from a natural language prompt.
 * Returns the validated and rendered diagram with SVG content and DSL code.
 * @param {string} prompt
 * @returns {Promise<object>}
 */
export async function generateDiagram(prompt) {
  const response = await fetch(`${API_BASE_URL}/api/diagrams/generate`, {
    ...defaultOptions,
    method: 'POST',
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = errorData.detail || errorData.rejection_reason || `Generation failed: ${response.status}`;
    throw new Error(message);
  }

  return response.json();
}

// ── Sprint 5: Async Jobs, History & Chat Q&A ──────────────────────────────────

/**
 * Start async diagram generation job.
 * @param {string} prompt
 * @returns {Promise<{job_id: string, status: string, poll_url: string}>}
 */
export async function generateDiagramAsync(prompt) {
  const response = await fetch(`${API_BASE_URL}/api/diagrams/generate-async`, {
    ...defaultOptions,
    method: 'POST',
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = errorData.detail || errorData.rejection_reason || `Async generation failed: ${response.status}`;
    throw new Error(message);
  }

  return response.json();
}

/**
 * Poll job status and stage progress.
 * @param {string} jobId
 * @returns {Promise<object>}
 */
export async function getJobStatus(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/diagrams/${jobId}/status`, defaultOptions);
  if (!response.ok) {
    throw new Error(`Job status poll failed: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch persisted user diagram history from backend database.
 * @returns {Promise<Array>}
 */
export async function getHistory() {
  const response = await fetch(`${API_BASE_URL}/api/history`, defaultOptions);
  if (!response.ok) {
    throw new Error(`Failed to fetch history: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch single diagram history detail.
 * @param {string} id
 * @returns {Promise<object>}
 */
export async function getHistoryItem(id) {
  const response = await fetch(`${API_BASE_URL}/api/history/${id}`, defaultOptions);
  if (!response.ok) {
    throw new Error(`Failed to fetch history item: ${response.status}`);
  }
  return response.json();
}

/**
 * Delete a diagram request from persistent history.
 * @param {string} id
 * @returns {Promise<object>}
 */
export async function deleteHistoryItem(id) {
  const response = await fetch(`${API_BASE_URL}/api/history/${id}`, {
    ...defaultOptions,
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete history item: ${response.status}`);
  }
  return response.json();
}

/**
 * Send Diagram-Aware conversational chat message.
 * @param {string} message
 * @param {object|null} diagramContext
 * @returns {Promise<{reply: string, diagram_aware: boolean, context_referenced: string|null}>}
 */
export async function sendChatMessage(message, diagramContext = null) {
  const response = await fetch(`${API_BASE_URL}/api/chat/message`, {
    ...defaultOptions,
    method: 'POST',
    body: JSON.stringify({ message, diagram_context: diagramContext }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Chat request failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Upload reference text/code file for prompt context extraction.
 * @param {File} file
 * @returns {Promise<{success: boolean, filename: string, extracted_text: string}>}
 */
export async function uploadReferenceFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/diagrams/upload-reference`, {
    credentials: 'include',
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Reference file upload failed: ${response.status}`);
  }

  return response.json();
}

