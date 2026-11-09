import { defineConfig } from "vite-plus/pack";

export default defineConfig({
  deps: {
    // tsdown <0.23 compatibility: resolve external dependency subpaths.
    // Remove to preserve subpath imports as written (the new default).
    // https://tsdown.dev/options/dependencies#deps-resolvedepsubpath
    resolveDepSubpath: true,
    // tsdown 0.23 bundles devDependency types into the dts; @types/express is
    // CommonJS dts and cannot be bundled. Keep `express` external as 0.16 did.
    neverBundle: ["express"],
  },
  entry: ["src/index.ts"],
  format: ["esm"],
  dts: true,
  // tsdown 0.23 drops main/module for ESM-only builds unless legacy is set.
  exports: { legacy: true },
});
