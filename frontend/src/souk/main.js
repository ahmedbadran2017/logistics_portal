// The souk portal (/souk) — its own app, like the supplier portal: own
// shell, login, colour and bundle (logistics_souk.bundle.js). It shares the
// source tree with the logistics SPA — the souk pages, the RPC client, i18n,
// the theme — and nothing of the floor's chrome: no live clock, no Tasks
// pill, no clock-in card, no bonus notice, no notification bell, no ⌘K.
// Ahmed, 2026-11-17: "fully separate, like joyagent or partners".
import { createApp } from "vue";
import SoukApp from "./SoukApp.vue";
import router from "./router";
import { initTheme } from "@/composables/useTheme";
import { initLocale } from "@/composables/useI18n";
import "@/index.css";
import "./souk.css";

// The portal's own colour ramp (souk.css) hangs off this attribute, so the
// shared components' accent utilities turn green here and stay rust on the
// floor without a line changing in them.
document.documentElement.dataset.portal = "souk";
initTheme();
initLocale();

const app = createApp(SoukApp);
app.use(router);
app.mount("#app");
