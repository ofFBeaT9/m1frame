import { createApp } from "./app.js";
import { seed } from "./db/seed.js";
import { config } from "./config.js";
import { aiOnline } from "./services/ai.js";

seed();
const app = createApp();
app.listen(config.port, () => {
  // eslint-disable-next-line no-console
  console.log(`NEXUS API on :${config.port} — AI ${aiOnline() ? "ONLINE" : "OFFLINE (degraded mode)"}, demo=${config.features.demoMode}`);
});
