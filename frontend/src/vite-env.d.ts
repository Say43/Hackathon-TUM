/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Base URL of the FastAPI backend (no trailing slash).
   * Configured in `frontend/.env` — see `.env.example` for details.
   * Example: "http://127.0.0.1:8000"
   */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
