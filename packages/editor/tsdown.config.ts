import { defineConfig } from "vite-plus/pack";

export default defineConfig({
  deps: {
    // tsdown <0.23 compatibility: resolve external dependency subpaths.
    // Remove to preserve subpath imports as written (the new default).
    // https://tsdown.dev/options/dependencies#deps-resolvedepsubpath
    resolveDepSubpath: true,
  },
  entry: ["src/index.ts", "src/lib.ts"],
  format: ["esm"],
  dts: true,
  copy: ["src/styles"],
  exports: {
    // tsdown 0.23 drops main/module for ESM-only builds unless legacy is set.
    legacy: true,
    customExports: (exports) => ({
      ...exports,
      "./styles.css": "./dist/styles/index.css",
      "./styles": "./dist/styles/index.css",
    }),
  },
  platform: "neutral",
});
