/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the 1B API, e.g. http://127.0.0.1:8000 (see frontend/.env.example). */
  readonly VITE_API_BASE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
