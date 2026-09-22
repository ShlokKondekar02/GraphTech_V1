/**
 * Thin API Client for GraphTech Backend.
 * Uses environment variable VITE_API_BASE_URL (defaults to http://localhost:8000).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Perform a health check call to the backend.
 * @returns {Promise<{status: string}>}
 */
export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}
