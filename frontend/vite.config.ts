import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  // No dev-server proxy: the frontend is strict API-only and must hit
  // VITE_API_BASE_URL directly (see frontend/src/lib/api.ts).
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
