/**
 * Justyol Logistics — design tokens (Claude Design handoff).
 * Warm stone neutrals (Tailwind default) + a themeable accent ramp exposed as
 * CSS variables (default Rust). Components reference `accent-*`/`brand-*` which
 * both resolve to var(--accent-*), so the Tweaks panel can swap the ramp live.
 * Dark mode is a curated utility remap keyed on html[data-theme="dark"].
 */
function accent(shade) {
  return `var(--accent-${shade})`;
}
const ACCENT = Object.fromEntries(
  [50, 100, 200, 300, 400, 500, 600, 700, 800, 900].map((s) => [s, accent(s)])
);

export default {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
    "./node_modules/frappe-ui/src/components/**/*.{vue,js,ts}",
  ],
  theme: {
    extend: {
      colors: {
        accent: ACCENT,
        brand: ACCENT, // alias — existing bg-brand-* usages become the accent
        // Surface/text tokens (stone-based) so existing components keep working
        // and flip in dark mode. New screens may also use raw stone-* classes.
        bg: "rgb(var(--bg) / <alpha-value>)",
        bg2: "rgb(var(--bg2) / <alpha-value>)",
        card: "rgb(var(--card) / <alpha-value>)",
        card2: "rgb(var(--card2) / <alpha-value>)",
        border: "rgb(var(--border) / <alpha-value>)",
        content: {
          DEFAULT: "rgb(var(--text) / <alpha-value>)",
          2: "rgb(var(--text2) / <alpha-value>)",
          3: "rgb(var(--text3) / <alpha-value>)",
          4: "rgb(var(--text4) / <alpha-value>)",
        },
        // Semantic status (aligned to the handoff's stage/SLA vocab)
        info: "#3b82f6",
        cyan: "#06b6d4",
        success: "#10b981",
        warn: "#f59e0b",
        orange: "#f97316",
        purple: "#8b5cf6",
        danger: "#f43f5e",
      },
      fontFamily: {
        sans: ["Inter", "Noto Sans Arabic", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      letterSpacing: { tighter: "-0.02em", tight: "-0.01em" },
      borderRadius: { card: "12px", btn: "8px", chip: "6px" },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.03)",
        lift: "0 4px 16px -6px rgba(0,0,0,0.1)",
        drawer: "0 0 60px -10px rgba(0,0,0,0.3)",
        floating: "0 24px 64px -16px rgba(0,0,0,0.22)",
      },
      animation: {
        "fade-in": "fadeIn 220ms cubic-bezier(0.16,1,0.3,1)",
        "scale-in": "scaleIn 240ms cubic-bezier(0.16,1,0.3,1)",
        menu: "menuIn 140ms cubic-bezier(0.16,1,0.3,1)",
        "toast-in": "toastIn 280ms cubic-bezier(0.16,1,0.3,1)",
        "drawer-in": "drawerIn 280ms cubic-bezier(0.16,1,0.3,1)",
        "success-pulse": "successPulse 0.5s ease",
        "error-shake": "errorShake 0.4s ease",
      },
      keyframes: {
        // Entrance keyframes keep opacity:1 at 0% so content is never invisible
        // when animations are paused (print / reduced-motion / offscreen).
        fadeIn: { "0%": { opacity: "1", transform: "translateY(6px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        scaleIn: { "0%": { opacity: "1", transform: "scale(.97)" }, "100%": { opacity: "1", transform: "scale(1)" } },
        menuIn: { "0%": { opacity: "1", transform: "translateY(-4px) scale(.98)" }, "100%": { opacity: "1", transform: "translateY(0) scale(1)" } },
        toastIn: { "0%": { opacity: "1", transform: "translate(-50%,12px)" }, "100%": { opacity: "1", transform: "translate(-50%,0)" } },
        drawerIn: { "0%": { opacity: "1", transform: "translateX(24px)" }, "100%": { opacity: "1", transform: "translateX(0)" } },
        successPulse: { "0%": { transform: "scale(1)", boxShadow: "0 0 0 0 rgba(16,185,129,.5)" }, "70%": { transform: "scale(1.02)", boxShadow: "0 0 0 12px rgba(16,185,129,0)" }, "100%": { transform: "scale(1)", boxShadow: "0 0 0 0 rgba(16,185,129,0)" } },
        errorShake: { "0%,100%": { transform: "translateX(0)" }, "20%,60%": { transform: "translateX(-6px)" }, "40%,80%": { transform: "translateX(6px)" } },
      },
    },
  },
  plugins: [],
};
