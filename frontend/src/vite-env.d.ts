/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "true" shows the demo credentials on the login page in a production build. */
  readonly VITE_DEMO_MODE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
