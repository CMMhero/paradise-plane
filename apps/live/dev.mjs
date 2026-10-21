/* Dev runner. Replaces `tsdown --watch --onSuccess "node ."`.
   Under turbo, the live task's output pipe stops being drained at a fixed
   point; the server's synchronous bootstrap writes then block forever and it
   wedges silently (alive, 0 CPU, no logs, port never bound). So the server's
   stdio goes to live-dev.log instead of turbo's pipe, and a health-checked
   supervisor respawns it if boot ever wedges anyway. */
/* eslint-disable no-await-in-loop -- this is a supervisor: the awaits are
   sequential on purpose (poll, then wait for exit, then respawn). Promise.all
   would defeat the point. */
import { spawn } from "node:child_process";
import { existsSync, openSync, watch } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";

const ENTRY = "dist/start.mjs";
const LOG_FILE = "live-dev.log";
// ponytail: port duplicated from .env, read it here if it ever diverges
const HEALTH_URL = `http://localhost:${process.env.PORT ?? 3100}/live/health`;
const BOOT_TIMEOUT_MS = 120_000;
const POLL_MS = 2_000;

const watcher = spawn("tsdown --watch --no-clean", { stdio: "inherit", shell: true });
watcher.on("exit", (code) => process.exit(code ?? 1));

// fresh clone: wait for the first build to produce the entry
while (!existsSync(ENTRY)) await sleep(300);

let server;
process.on("exit", () => server?.kill());

// restart the server when tsdown rewrites dist (debounced)
let debounce;
watch("dist", () => {
  clearTimeout(debounce);
  debounce = setTimeout(() => server?.kill(), 300);
});

const isHealthy = async () => {
  try {
    return (await fetch(HEALTH_URL)).ok;
  } catch {
    return false;
  }
};

for (;;) {
  const log = openSync(LOG_FILE, "a");
  server = spawn(process.execPath, ["--env-file=.env", ENTRY], { stdio: ["ignore", log, log] });
  const exited = new Promise((resolve) => server.on("exit", resolve));
  const deadline = Date.now() + BOOT_TIMEOUT_MS;

  // supervise boot: healthy → wait for exit; wedged past deadline → respawn
  for (;;) {
    const exitedFirst = await Promise.race([exited.then(() => true), sleep(POLL_MS).then(() => false)]);
    if (exitedFirst) break;
    if (await isHealthy()) {
      console.log(`[live-dev] healthy on ${HEALTH_URL} (logs: apps/live/${LOG_FILE})`);
      await exited;
      console.log("[live-dev] server exited, restarting");
      break;
    }
    if (Date.now() > deadline) {
      console.error("[live-dev] server never became healthy, respawning");
      server.kill();
      await exited;
      break;
    }
  }
  await sleep(1_000); // crash-loop damper
}
