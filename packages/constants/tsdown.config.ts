import { defineConfig } from "vite-plus/pack";

export default defineConfig({
  deps: {
    // tsdown <0.23 compatibility: resolve external dependency subpaths.
    // Remove to preserve subpath imports as written (the new default).
    // https://tsdown.dev/options/dependencies#deps-resolvedepsubpath
    resolveDepSubpath: true,
  },
  entry: ["src/index.ts"],
  format: ["esm"],
  dts: true,
  // tsdown 0.23 drops main/module for ESM-only builds unless legacy is set.
  exports: { legacy: true },
});
