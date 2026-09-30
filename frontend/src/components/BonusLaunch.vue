<template>
  <Teleport to="body">
    <Transition name="bl" :duration="{ enter: 600, leave: 320 }">
      <div
        v-if="open"
        class="bl-root"
        :class="{ 'bl-calm': calm }"
        role="dialog"
        aria-modal="true"
        aria-labelledby="bl-title"
        @keydown.esc="tryClose"
      >
        <div class="bl-backdrop" @click="tryClose" />

        <div class="bl-card bg-white">
          <!-- hero: the money on its way -->
          <div class="bl-hero" aria-hidden="true">
            <span v-for="c in COINS" :key="c.k" class="bl-coin" :style="c.s">
              <svg viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" fill="#fcd34d" stroke="#d97706" stroke-width="1.6" />
                <circle cx="12" cy="12" r="5.5" stroke="#d97706" stroke-width="1.4" />
              </svg>
            </span>
            <span v-for="s in SPARKS" :key="s.k" class="bl-spark" :style="s.s" />

            <div class="bl-trophy">
              <svg viewBox="0 0 64 64" fill="none">
                <path d="M20 10h24v14c0 9-5.4 15-12 15s-12-6-12-15V10z" fill="#fde68a" stroke="#b45309" stroke-width="2.4" stroke-linejoin="round" />
                <path d="M20 15h-7c0 8 3.5 12 8.5 13M44 15h7c0 8-3.5 12-8.5 13" stroke="#b45309" stroke-width="2.4" stroke-linecap="round" />
                <path d="M27 39h10l-1.5 8h-7L27 39z" fill="#fcd34d" stroke="#b45309" stroke-width="2.2" stroke-linejoin="round" />
                <rect x="21" y="47" width="22" height="7" rx="2" fill="#f59e0b" stroke="#b45309" stroke-width="2.2" />
                <path d="M27 16l2.4 4.8 5.3.8-3.8 3.7.9 5.3-4.8-2.5-4.8 2.5.9-5.3-3.8-3.7 5.3-.8z" fill="#fff7d6" />
              </svg>
              <span class="bl-shine" />
            </div>

            <div class="bl-date">
              <span class="bl-dot" />
              {{ t("an.date") }}
            </div>
          </div>

          <div ref="body" class="bl-body" @scroll.passive="measure">
            <p v-if="hello" class="bl-hi text-stone-500">
              {{ hello }} <span class="bl-wave">👋</span>
            </p>
            <h2 id="bl-title" class="text-stone-900">{{ t(variant === "cc" ? "an.title_cc" : "an.title") }}</h2>
            <p class="bl-lead text-stone-600">{{ t("an.lead_" + variant) }}</p>

            <ul class="bl-list">
              <li
                v-for="(it, i) in items" :key="it.k"
                class="bl-item" :class="{ 'bl-item-new': it.new }"
                :style="{ '--i': i }"
              >
                <span class="bl-ico"><Icon :name="it.icon" :size="17" /></span>
                <span class="bl-txt text-stone-800">{{ t(it.k) }}</span>
                <span v-if="it.new" class="bl-new">{{ t("an.new") }}</span>
              </li>
            </ul>

            <div class="bl-rule" :style="{ '--i': items.length }">
              <Icon name="zap" :size="15" />
              <span>{{ t("an.rule_" + variant) }}</span>
            </div>

            <div class="bl-notes" :style="{ '--i': items.length + 1 }">
              <p><Icon name="info" :size="13" class="bl-ni" />{{ t(variant === "cc" ? "an.trialPaid" : "an.trial") }}</p>
              <p v-if="variant !== 'cc'"><Icon name="clock" :size="13" class="bl-ni" />{{ t(variant === "ship" ? "an.amounts_ship" : "an.amounts") }}</p>
              <p v-if="ackedAt" class="bl-seen"><Icon name="check" :size="13" class="bl-ni" />{{ t("an.seenOn") }} {{ ackedAt.slice(0, 10) }}</p>
            </div>
          </div>

          <div class="bl-foot">
            <button
              ref="cta"
              class="bl-btn"
              :class="{ 'bl-ready': ready, 'bl-more': timed && !atEnd }"
              :disabled="!timed || busy"
              @click="onCta"
            >
              <span class="bl-fill" :style="{ animationDuration: readyMs + 'ms' }" />
              <span class="bl-lbl">
                <template v-if="ackedAt">{{ t("an.close") }}</template>
                <template v-else-if="ready">{{ t("an.cta") }} 🚀</template>
                <template v-else-if="timed"><span class="bl-arrow">↓</span> {{ t("an.more") }}</template>
                <template v-else>{{ t("an.reading") }}</template>
              </span>
            </button>
          </div>

          <!-- the moment they say yes -->
          <div v-if="party" class="bl-confetti" aria-hidden="true">
            <i v-for="p in confetti" :key="p.k" :style="p.s" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { SURFACE } from "@/lib/portal";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { useBonusLaunch } from "@/composables/useBonusLaunch";

const { t } = useI18n();
const { success, warn } = useToast();
const { isLoggedIn, isInitialized, role, viewAs } = useAuth();
const { reopen } = useBonusLaunch();

// Which BOARD the reader is paid on decides what the notice says — the server
// sends it from the same map the money uses. Not the portal: CS agents sit on
// /confirmation yet are paid on the ship board, and only the contact centre is
// paid for September. A manager has no board, so theirs follows the portal.
const group = ref(null);
const variant = computed(() => group.value
  || (SURFACE === "cc" ? "cc" : SURFACE === "ship" ? "ship" : "floor"));

const ITEMS = {
  floor: [
    { k: "an.f_pick", icon: "scan-line" },
    { k: "an.f_sort", icon: "layout-grid" },
    // The one habit that has to CHANGE: 9,344 parcels shipped in September
    // against 179 pack scans — packing is real work nobody can see.
    { k: "an.f_pack", icon: "package", new: true },
    { k: "an.f_manifest", icon: "truck" },
    { k: "an.f_short", icon: "search" },
    { k: "an.f_clock", icon: "clock" },
  ],
  cc: [
    { k: "an.c_decide", icon: "check" },
    { k: "an.c_delivered", icon: "truck" },
    { k: "an.c_returned", icon: "route" },
    { k: "an.c_fix", icon: "map-pin" },
    { k: "an.c_follow", icon: "trending-up" },
  ],
  ship: [
    { k: "an.c_decide", icon: "check" },
    { k: "an.s_landed", icon: "truck" },
    { k: "an.c_fix", icon: "map-pin" },
    { k: "an.s_clock", icon: "clock" },
  ],
};
const items = computed(() => ITEMS[variant.value]);

// Pure decoration, fixed at module load so a re-render never reshuffles it.
const COINS = [
  { k: 1, s: "--x:14%;--d:0s;--dur:3.8s;--sz:22px" },
  { k: 2, s: "--x:30%;--d:1.1s;--dur:4.4s;--sz:16px" },
  { k: 3, s: "--x:68%;--d:.5s;--dur:4s;--sz:20px" },
  { k: 4, s: "--x:84%;--d:1.7s;--dur:3.6s;--sz:14px" },
  { k: 5, s: "--x:50%;--d:2.3s;--dur:4.6s;--sz:12px" },
];
const SPARKS = [
  { k: 1, s: "top:18%;inset-inline-start:22%;--d:0s" },
  { k: 2, s: "top:30%;inset-inline-start:76%;--d:.7s" },
  { k: 3, s: "top:62%;inset-inline-start:12%;--d:1.3s" },
  { k: 4, s: "top:56%;inset-inline-start:88%;--d:.4s" },
  { k: 5, s: "top:12%;inset-inline-start:58%;--d:1.9s" },
];

const open = ref(false);
const ackedAt = ref(null);
const firstName = ref("");
// Two conditions, both needed before "I read it" means anything: the list has
// finished arriving (timed) and the reader has reached the end (atEnd) — the
// September line and the one rule that settles every argument sit at the
// bottom, below the fold on a PDA. The button does the scrolling itself, so
// this guides rather than blocks.
const timed = ref(false);
const atEnd = ref(false);
const ready = computed(() => timed.value && atEnd.value);
const body = ref(null);
const busy = ref(false);
const party = ref(false);
const confetti = ref([]);
const cta = ref(null);

const calm = typeof window !== "undefined" && window.matchMedia
  && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
// Long enough for the list to finish arriving — that is the reading — and no
// longer: a forced wait is a tax on the person who already read it.
const readyMs = computed(() => (calm || ackedAt.value ? 0 : 900 + items.value.length * 130));

const hello = computed(() => (firstName.value ? t("an.hello").replace("{n}", firstName.value) : ""));

let readyTimer = null;
function measure() {
  const el = body.value;
  if (!el) return;
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 8) atEnd.value = true;
}
function show() {
  open.value = true;
  timed.value = false;
  atEnd.value = false;
  party.value = false;
  document.documentElement.classList.add("bl-lock");
  // Content that fits needs no scrolling; measure once it has laid out.
  nextTick(() => setTimeout(measure, 60));
  clearTimeout(readyTimer);
  readyTimer = setTimeout(async () => {
    timed.value = true;
    measure();
    await nextTick();
    cta.value?.focus?.();
  }, readyMs.value);
}
function onCta() {
  if (ready.value || ackedAt.value) return doAck();
  body.value?.scrollTo({ top: body.value.scrollHeight, behavior: calm ? "auto" : "smooth" });
}
function hide() {
  open.value = false;
  document.documentElement.classList.remove("bl-lock");
  clearTimeout(readyTimer);
}
// Not acknowledged = not dismissable. Once read, it closes like any dialog.
function tryClose() { if (ackedAt.value && !busy.value) hide(); }

async function check(force = false) {
  // A manager viewing as a member is reading someone else's portal: the
  // acknowledgement would be recorded against the manager, so stay quiet.
  if (!isLoggedIn.value || !role.value || viewAs.value) return;
  try {
    const r = await api("announcements.pending");
    if (!r || !r.key) return;
    firstName.value = r.firstName || "";
    group.value = ["cc", "floor", "ship"].includes(r.group) ? r.group : null;
    ackedAt.value = r.acked ? r.ackedAt : null;
    if (force || !r.acked) {
      show();
      if (ackedAt.value) atEnd.value = true;
    }
  } catch (_) { /* an announcement must never block the portal */ }
}

// Let the page settle first — boot, the router's redirect, the first paint.
let bootTimer = null;
watch([isInitialized, role], ([ok, r]) => {
  if (!ok || !r) return;
  clearTimeout(bootTimer);
  bootTimer = setTimeout(() => check(false), 1100);
}, { immediate: true });
watch(reopen, () => check(true));

function burst() {
  const colors = ["#f59e0b", "#fcd34d", "#10b981", "#8b5cf6", "#ef4444", "#3b82f6", "#ec4899"];
  confetti.value = Array.from({ length: 38 }, (_, k) => {
    const a = (Math.PI * 2 * k) / 38 + Math.random() * 0.4;
    const r = 110 + Math.random() * 150;
    return {
      k,
      s: `--x:${Math.cos(a) * r}px;--y:${Math.sin(a) * r - 60}px;--r:${Math.random() * 720 - 360}deg;`
        + `--c:${colors[k % colors.length]};--w:${6 + Math.random() * 5}px;--h:${9 + Math.random() * 7}px;`
        + `--d:${Math.random() * 0.12}s`,
    };
  });
  party.value = true;
}

async function doAck() {
  if (ackedAt.value) { if (!busy.value) hide(); return; }
  if (!ready.value || busy.value) return;
  busy.value = true;
  try {
    const r = await apiPost("announcements.ack", { key: "bonus-2026-10" });
    ackedAt.value = r.ackedAt;
    if (!calm) burst();
    setTimeout(() => {
      hide();
      success(t("an.doneTitle"), t("an.doneBody"));
    }, calm ? 150 : 1350);
  } catch (e) {
    warn(t("common.loadFail"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

onBeforeUnmount(() => {
  clearTimeout(readyTimer);
  clearTimeout(bootTimer);
  document.documentElement.classList.remove("bl-lock");
});
</script>

<style>
/* Unscoped on purpose: the scroll lock sits on <html>, outside this tree, and
   the dark theme is an attribute on <html> too. Every class is bl- prefixed,
   so nothing here can leak onto another screen. The accent scale needs no
   dark override: the theme inverts it (--accent-50 is dark there). */
html.bl-lock, html.bl-lock body { overflow: hidden; }
html[data-theme="dark"] .bl-item { background: rgba(255,255,255,.05); }
html[data-theme="dark"] .bl-item-new { background: rgba(245,158,11,.12); }
html[data-theme="dark"] .bl-notes p { color: #a8a29e; }
html[data-theme="dark"] .bl-date { background: rgba(28,25,23,.92); color: #fcd34d; }
</style>

<style scoped>
.bl-root {
  position: fixed; inset: 0; z-index: 90;
  display: flex; align-items: center; justify-content: center;
  padding: 16px;
}
.bl-backdrop {
  position: absolute; inset: 0;
  background: rgba(28, 25, 23, .55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.bl-card {
  position: relative;
  width: 100%; max-width: 460px; max-height: calc(100dvh - 32px);
  display: flex; flex-direction: column;
  border-radius: 24px; overflow: hidden;
  box-shadow: 0 30px 80px -20px rgba(0,0,0,.45), 0 0 0 1px rgba(0,0,0,.04);
}

/* ── enter / leave ─────────────────────────────────────────── */
.bl-enter-active .bl-backdrop, .bl-leave-active .bl-backdrop { transition: opacity .28s ease; }
.bl-enter-from .bl-backdrop, .bl-leave-to .bl-backdrop { opacity: 0; }
.bl-enter-active .bl-card { transition: transform .55s cubic-bezier(.2, 1.35, .4, 1), opacity .3s ease; }
.bl-leave-active .bl-card { transition: transform .25s ease, opacity .22s ease; }
.bl-enter-from .bl-card { transform: translateY(34px) scale(.93); opacity: 0; }
.bl-leave-to .bl-card { transform: translateY(12px) scale(.97); opacity: 0; }

/* ── hero ───────────────────────────────────────────────────── */
.bl-hero {
  position: relative; flex-shrink: 0;
  height: 176px;
  background: linear-gradient(125deg, var(--accent-700), var(--accent-500) 45%, #f59e0b 100%);
  background-size: 220% 220%;
  animation: bl-sky 9s ease-in-out infinite;
  overflow: hidden;
}
.bl-hero::after {           /* soft floor light under the trophy */
  content: ""; position: absolute; left: 50%; bottom: -60px;
  width: 260px; height: 140px; transform: translateX(-50%);
  background: radial-gradient(closest-side, rgba(255,255,255,.35), transparent);
}
@keyframes bl-sky { 0%,100% { background-position: 0% 40%; } 50% { background-position: 100% 60%; } }

.bl-coin {
  position: absolute; bottom: -28px; left: var(--x);
  width: var(--sz); height: var(--sz);
  animation: bl-rise var(--dur) cubic-bezier(.3,.6,.4,1) var(--d) infinite;
  opacity: 0;
}
.bl-coin svg { width: 100%; height: 100%; filter: drop-shadow(0 2px 3px rgba(0,0,0,.18)); }
@keyframes bl-rise {
  0%   { transform: translateY(0) rotate(0deg); opacity: 0; }
  15%  { opacity: 1; }
  80%  { opacity: 1; }
  100% { transform: translateY(-210px) rotate(320deg); opacity: 0; }
}
.bl-spark {
  position: absolute; width: 6px; height: 6px; border-radius: 99px;
  background: #fff; box-shadow: 0 0 10px 2px rgba(255,255,255,.8);
  animation: bl-twinkle 2.6s ease-in-out var(--d) infinite;
  opacity: 0;
}
@keyframes bl-twinkle { 0%,100% { transform: scale(0); opacity: 0; } 50% { transform: scale(1); opacity: 1; } }

.bl-trophy {
  position: absolute; left: 50%; top: 26px;
  width: 92px; height: 92px; margin-left: -46px;
  animation: bl-bob 3s ease-in-out infinite;
  overflow: hidden; border-radius: 18px;
}
.bl-trophy svg { width: 100%; height: 100%; filter: drop-shadow(0 8px 14px rgba(120,53,15,.35)); }
.bl-shine {
  position: absolute; inset: 0;
  background: linear-gradient(105deg, transparent 38%, rgba(255,255,255,.75) 50%, transparent 62%);
  transform: translateX(-120%);
  animation: bl-shine 3.4s ease-in-out 1s infinite;
}
@keyframes bl-bob { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }
@keyframes bl-shine { 0%, 60% { transform: translateX(-120%); } 85%, 100% { transform: translateX(120%); } }

.bl-date {
  position: absolute; left: 50%; bottom: 14px; transform: translateX(-50%);
  display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 14px; border-radius: 99px;
  background: rgba(255,255,255,.95); color: var(--accent-800);
  font-size: 13px; font-weight: 800; letter-spacing: .01em; white-space: nowrap;
  box-shadow: 0 6px 18px -6px rgba(0,0,0,.35);
}
.bl-dot {
  width: 8px; height: 8px; border-radius: 99px; background: #10b981;
  box-shadow: 0 0 0 0 rgba(16,185,129,.6);
  animation: bl-ping 1.8s ease-out infinite;
}
@keyframes bl-ping { 0% { box-shadow: 0 0 0 0 rgba(16,185,129,.55); } 100% { box-shadow: 0 0 0 10px rgba(16,185,129,0); } }

/* ── body ───────────────────────────────────────────────────── */
.bl-body { padding: 20px 22px 6px; overflow-y: auto; -webkit-overflow-scrolling: touch; }
.bl-hi { font-size: 13px; font-weight: 600; }
.bl-wave { display: inline-block; transform-origin: 70% 70%; animation: bl-wave 2.2s ease-in-out .6s 2; }
@keyframes bl-wave { 0%,60%,100% { transform: rotate(0); } 10%,30% { transform: rotate(16deg); } 20% { transform: rotate(-8deg); } 40% { transform: rotate(-4deg); } 50% { transform: rotate(10deg); } }
#bl-title { font-size: 20px; font-weight: 800; letter-spacing: -.01em; line-height: 1.3; margin-top: 2px; }
.bl-lead { font-size: 13.5px; line-height: 1.6; margin-top: 6px; }

.bl-list { margin-top: 14px; display: grid; gap: 7px; }
.bl-item, .bl-rule, .bl-notes {
  opacity: 0; transform: translateY(8px);
  animation: bl-in .45s cubic-bezier(.2,.9,.3,1) forwards;
  animation-delay: calc(var(--i) * 130ms + 380ms);
}
@keyframes bl-in { to { opacity: 1; transform: none; } }
.bl-item {
  display: flex; align-items: center; gap: 11px;
  padding: 9px 11px; border-radius: 12px;
  background: rgba(120,113,108,.07);
}
.bl-ico {
  flex-shrink: 0; width: 32px; height: 32px; border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--accent-50); color: var(--accent-700);
}
.bl-txt { font-size: 13px; font-weight: 600; line-height: 1.45; flex: 1; min-width: 0; }
.bl-item-new { background: rgba(245,158,11,.1); box-shadow: inset 0 0 0 1.5px rgba(245,158,11,.45); }
.bl-item-new .bl-ico { background: #fef3c7; color: #b45309; }
.bl-new {
  flex-shrink: 0; font-size: 10.5px; font-weight: 800; text-transform: uppercase;
  padding: 3px 8px; border-radius: 99px; color: #fff;
  background: linear-gradient(90deg, #f59e0b, #ef4444, #f59e0b);
  background-size: 200% 100%;
  animation: bl-shimmer 2.2s linear infinite;
}
@keyframes bl-shimmer { to { background-position: -200% 0; } }

.bl-rule {                /* the one line that settles every argument — loud in both themes */
  margin-top: 12px; display: flex; align-items: center; gap: 8px;
  padding: 11px 13px; border-radius: 12px;
  font-size: 14px; font-weight: 800; color: #fff;
  background: var(--accent-600);
  box-shadow: 0 8px 20px -12px var(--accent-600);
}
.bl-notes { margin-top: 12px; display: grid; gap: 6px; }
.bl-notes p { font-size: 12px; line-height: 1.55; color: #78716c; display: flex; gap: 6px; align-items: flex-start; }
.bl-ni { flex-shrink: 0; margin-top: 2px; }
.bl-seen { color: #047857 !important; font-weight: 600; }

/* ── footer / button ────────────────────────────────────────── */
.bl-foot { padding: 12px 22px 18px; flex-shrink: 0; }
.bl-btn {
  position: relative; width: 100%; height: 50px; border-radius: 14px; overflow: hidden;
  font-size: 15px; font-weight: 800; color: #fff;
  background: var(--accent-300);
  transition: transform .15s ease, box-shadow .3s ease, background .3s ease;
}
.bl-btn:disabled { cursor: default; }
.bl-fill {
  position: absolute; inset: 0; width: 0;
  background: var(--accent-600);
  animation: bl-fill linear forwards;
}
@keyframes bl-fill { to { width: 100%; } }
.bl-ready { background: var(--accent-600); animation: bl-glow 2s ease-in-out .2s infinite; }
.bl-ready:active { transform: scale(.98); }
.bl-lbl { position: relative; display: inline-flex; align-items: center; gap: 6px; }
.bl-more { background: var(--accent-500); }
.bl-arrow { display: inline-block; animation: bl-nudge 1.1s ease-in-out infinite; }
@keyframes bl-nudge { 0%,100% { transform: translateY(-1px); } 50% { transform: translateY(3px); } }
@keyframes bl-glow {
  0%,100% { box-shadow: 0 8px 22px -10px var(--accent-600); }
  50%     { box-shadow: 0 10px 30px -6px var(--accent-500); }
}

/* ── confetti ───────────────────────────────────────────────── */
.bl-confetti { position: absolute; left: 50%; top: 58%; width: 0; height: 0; pointer-events: none; z-index: 3; }
.bl-confetti i {
  position: absolute; width: var(--w); height: var(--h); border-radius: 2px;
  background: var(--c); opacity: 0;
  animation: bl-pop 1.25s cubic-bezier(.12,.72,.28,1) var(--d) forwards;
}
@keyframes bl-pop {
  0%   { transform: translate(0,0) rotate(0) scale(.6); opacity: 1; }
  70%  { opacity: 1; }
  100% { transform: translate(var(--x), calc(var(--y) + 140px)) rotate(var(--r)) scale(1); opacity: 0; }
}

/* ── the PDA: one hand on the device, the other on a parcel ─── */
@media (max-width: 640px) {
  .bl-root { padding: 0; align-items: stretch; }
  .bl-card { max-width: none; max-height: none; height: 100dvh; border-radius: 0; }
  .bl-hero { height: 158px; }
  .bl-body { flex: 1; padding: 18px 18px 6px; }
  .bl-foot { padding: 10px 18px calc(14px + env(safe-area-inset-bottom)); }
  .bl-btn { height: 54px; font-size: 16px; }
  .bl-txt { font-size: 13.5px; }
}

/* Motion off: the same card, arriving still. */
.bl-calm *, .bl-calm *::before, .bl-calm *::after { animation: none !important; }
.bl-calm .bl-item, .bl-calm .bl-rule, .bl-calm .bl-notes { opacity: 1; transform: none; }
.bl-calm .bl-coin, .bl-calm .bl-spark { display: none; }
.bl-calm .bl-fill { width: 100%; }
@media (prefers-reduced-motion: reduce) {
  .bl-enter-active .bl-card, .bl-leave-active .bl-card { transition: opacity .2s ease; }
  .bl-enter-from .bl-card, .bl-leave-to .bl-card { transform: none; }
}

</style>
