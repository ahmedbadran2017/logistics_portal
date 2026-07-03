import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { initTheme } from "./composables/useTheme";
import { initLocale } from "./composables/useI18n";
import "./index.css";

// Apply persisted theme + locale before first paint to avoid a flash.
initTheme();
initLocale();

const app = createApp(App);
app.use(router);
app.mount("#app");
