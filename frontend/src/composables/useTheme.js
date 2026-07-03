import { ref } from "vue";

const THEME_KEY = "lp.theme";
const theme = ref("light");

function apply(next) {
  theme.value = next;
  const root = document.documentElement;
  root.dataset.theme = next; // dark remap keys on html[data-theme="dark"]
  root.style.colorScheme = next;
}

/** Called once at boot (main.js) before first paint. */
export function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  apply(saved === "dark" || saved === "light" ? saved : "light");
}

export function useTheme() {
  function toggle() {
    const next = theme.value === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_KEY, next);
    apply(next);
  }
  function set(next) {
    localStorage.setItem(THEME_KEY, next);
    apply(next);
  }
  return { theme, toggle, set };
}
