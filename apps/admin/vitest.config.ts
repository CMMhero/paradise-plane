import path from "node:path";
import { defineConfig } from "vitest/config";

// Unit tests for pure God Mode logic (no DOM). Kept apart from vite.config.ts,
// whose React Router plugin is for the app build only.
export default defineConfig({
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, ".") },
  },
});
