import type { Config } from "@react-router/dev/config";

export default {
  appDirectory: "app",
  // Web runs as a client-side app; build a static client bundle only
  ssr: false,
  future: {
    // Paradise: give Vite's dependency scanner the client entry and every
    // route file. Without this the scanner sees no routes at all, so each
    // route's dependencies are discovered only when the page is opened, Vite
    // re-optimizes mid-session, and the route import fails with 504
    // "Outdated Optimize Dep" (the blank Chat page).
    unstable_optimizeDeps: true,
  },
} satisfies Config;
