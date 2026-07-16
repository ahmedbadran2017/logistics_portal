import { ref } from "vue";

const THEME_KEY = "lp.theme";
const theme = ref("light");

// The Android status bar of the installed PWA takes its colour from this meta.
// The manifest can only name one, and the theme is a per-user choice, so keep
// the tag in step with the toggle or a picker on dark mode gets a white bar.
const BAR = { light: "#ffffff", dark: "#1c1917" };

function apply(next) {
  theme.value = next;
  const root = document.documentElement;
  root.dataset.theme = next; // dark remap keys on html[data-theme="dark"]
  root.style.colorScheme = next;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", BAR[next] || BAR.light);
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
