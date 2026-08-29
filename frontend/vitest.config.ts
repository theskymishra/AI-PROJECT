import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Vitest configuration.
 *
 * Separate from vite.config.ts so the dev/build pipeline carries no test
 * tooling. The alias is duplicated deliberately -- it is two lines, and
 * sharing it would couple the build config to the test runner.
 *
 * Tailwind is NOT loaded here: these tests assert structure and geometry, not
 * computed styles. jsdom does not do layout, so any test that claimed to check
 * appearance would be lying.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
