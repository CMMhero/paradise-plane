import path from "node:path";
import * as dotenv from "dotenv";
import { reactRouter } from "@react-router/dev/vite";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

dotenv.config({ path: path.resolve(__dirname, ".env") });

// Expose only vars starting with VITE_
const viteEnv = Object.keys(process.env)
  .filter((k) => k.startsWith("VITE_"))
  .reduce<Record<string, string>>((a, k) => {
    a[k] = process.env[k] ?? "";
    return a;
  }, {});

// Hasil build tiap paket workspace yang dipakai web. Garis miring maju karena
// pencocok glob menolak pemisah gaya Windows.
const WORKSPACE_DIST_ENTRIES = [
  "constants",
  "editor",
  "hooks",
  "i18n",
  "propel",
  "services",
  "shared-state",
  "ui",
  "utils",
].map((pkg) => `${path.resolve(__dirname, "../../packages", pkg, "dist").replaceAll("\\", "/")}/**/*.{js,mjs}`);

export default defineConfig(() => ({
  define: {
    "process.env": JSON.stringify(viteEnv),
  },
  build: {
    assetsInlineLimit: 0,
  },
  plugins: [reactRouter(), tsconfigPaths({ projects: [path.resolve(__dirname, "tsconfig.json")] })],
  resolve: {
    alias: {
      // Next.js compatibility shims used within web
      "next/link": path.resolve(__dirname, "app/compat/next/link.tsx"),
      "next/navigation": path.resolve(__dirname, "app/compat/next/navigation.ts"),
      "next/script": path.resolve(__dirname, "app/compat/next/script.tsx"),
    },
    dedupe: ["react", "react-dom", "@headlessui/react"],
  },
  server: {
    host: "0.0.0.0",
  },
  optimizeDeps: {
    // Paradise: rute dipindai lewat `future.unstable_optimizeDeps` di
    // react-router.config.ts (entri ini digabung dengan milik plugin). Yang
    // ditambah di sini: `dist` paket workspace. Dependensi yang diimpor dari
    // sana (base-ui, blueprintjs, atlaskit, ...) tidak ikut terayapi dari rute,
    // jadi baru ketemu saat halaman dibuka. Vite lalu mengoptimasi ulang di
    // tengah sesi, hash bundel yang sudah dimuat jadi basi (504 "Outdated
    // Optimize Dep"), impor modul rute gagal, dan halaman tampil kosong.
    entries: WORKSPACE_DIST_ENTRIES,
  },
  // No SSR-specific overrides needed; alias resolves to ESM build
}));
