import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// fileURLToPath is used rather than __dirname so the alias resolves identically
// on macOS and Windows.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // Fail loudly instead of silently moving to 5174, which would break the
    // backend CORS allow-list and present as an unexplained "offline" badge.
    strictPort: true,
  },
});
