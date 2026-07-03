import { ref, computed } from "vue";
import en from "@/locales/en";
import fr from "@/locales/fr";
import ar from "@/locales/ar";

const LOCALE_KEY = "lp.locale";
const dicts = { en, fr, ar };
const locale = ref("en");

function apply(next) {
  locale.value = dicts[next] ? next : "en";
  const root = document.documentElement;
  root.setAttribute("lang", locale.value);
  root.setAttribute("dir", locale.value === "ar" ? "rtl" : "ltr");
}

export function initLocale() {
  apply(localStorage.getItem(LOCALE_KEY) || "en");
}

/** Resolve a dotted key ("nav.queue") against the active dictionary. */
function resolve(dict, key) {
  return key.split(".").reduce((o, k) => (o == null ? o : o[k]), dict);
}

export function useI18n() {
  const isRTL = computed(() => locale.value === "ar");

  function t(key, fallback) {
    const val = resolve(dicts[locale.value], key);
    if (val != null) return val;
    return resolve(dicts.en, key) ?? fallback ?? key;
  }
  function setLocale(next) {
    localStorage.setItem(LOCALE_KEY, next);
    apply(next);
  }
  return { locale, isRTL, t, setLocale };
}
