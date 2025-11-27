import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// IMPORTANT: this URL is your backend (8000) Codespaces URL.
// If your Codespace name changes, update this string.
const BACKEND_URL =
  "https://sturdy-barnacle-9p6p5wxp647h7j7w-8000.app.github.dev";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
