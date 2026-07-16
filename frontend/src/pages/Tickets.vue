<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1200px] mx-auto">
    <!-- hero -->
    <header class="cs-hero rounded-2xl p-5 sm:p-6">
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3.5">
          <span class="cs-hero-icon"><Icon name="message-circle" :size="22" /></span>
          <div>
            <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('cs.title') }}</h1>
            <p class="text-[12.5px] text-stone-500 mt-1.5">{{ t('cs.intro') }}</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <div v-if="data" class="flex items-stretch gap-2">
            <div class="cs-stat">
              <span class="cs-stat-n text-emerald-600">{{ data.mine.resolve }}</span>
              <span class="cs-stat-l"><Icon name="check-circle" :size="10" class="inline -mt-px me-0.5" />{{ t('cs.statResolved') }}</span>
            </div>
            <div class="cs-stat">
              <span class="cs-stat-n text-violet-600">{{ data.mine.reply + data.mine.create }}</span>
              <span class="cs-stat-l"><Icon name="corner-down-left" :size="10" class="inline -mt-px me-0.5" />{{ t('cs.statHandled') }}</span>
            </div>
          </div>
          <button class="cs-new" @click="createFor = createFor === '_new' ? '' : '_new'; resetForm()">
            <Icon name="plus" :size="15" class="inline -mt-px me-1" />{{ t('cs.newTicket') }}
          </button>
        </div>
      </div>
    </header>

    <!-- create panel -->
    <Transition name="csslide">
      <div v-if="createFor === '_new'" class="bg-white rounded-2xl ring-1 ring-violet-200/80 p-4 space-y-3 shadow-sm">
        <TicketForm :categories="data?.categories || []" :busy="creating" @submit="submitCreate" />
      </div>
    </Transition>

    <!-- tabs + search -->
    <div class="flex items-center gap-3 flex-wrap">
      <div class="cs-seg">
        <button v-for="tb in tabs" :key="tb.key" class="cs-seg-btn" :class="tab === tb.key ? 'cs-seg-on' : ''"
                @click="tab = tb.key; page = 1; load()">
          <Icon :name="tb.icon" :size="14" />
          <span>{{ t(tb.label) }}</span>
          <span class="cs-seg-count" :class="tab === tb.key ? tb.onColor : 'bg-stone-200/70 text-stone-500'">
            {{ data?.counts?.[tb.key] ?? '–' }}
          </span>
        </button>
      </div>
      <div class="relative ms-auto">
        <Icon name="search" :size="13" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input v-model="q" :placeholder="t('cs.searchPh')" @input="debouncedLoad"
               class="h-10 w-[240px] ps-9 pe-3 text-[12.5px] bg-white rounded-xl ring-1 ring-stone-200/80 focus:ring-2 outline-none transition-shadow"
               style="--tw-ring-color: rgb(196 181 253)" />
      </div>
    </div>

    <!-- rows -->
    <div v-if="loading" class="space-y-2.5">
      <div v-for="n in 6" :key="n" class="h-[72px] rounded-2xl cs-shimmer" />
    </div>
    <div v-else-if="loadError" class="cs-empty rounded-2xl p-12 text-center">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-rose-50 text-rose-500 mb-3"><Icon name="alert-triangle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
      <div class="text-[12px] text-stone-400 mt-1 font-mono max-w-[420px] mx-auto break-words">{{ loadError }}</div>
    </div>
    <div v-else-if="!rows.length" class="cs-empty rounded-2xl p-12 text-center">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3"><Icon name="check-circle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('cs.empty') }}</div>
      <div class="text-[12.5px] text-stone-400 mt-1">{{ tab === 'inbox' ? t('cs.emptyInboxHint') : t('cs.emptyHint') }}</div>
    </div>

    <!-- WHATSAPP INBOX rows -->
    <TransitionGroup v-else-if="tab === 'inbox'" name="csrow" tag="div" class="space-y-2.5 relative">
      <div v-for="r in rows" :key="r.id" class="cs-card rounded-2xl p-4">
        <div class="flex items-center gap-3.5 flex-wrap">
          <span class="cs-avatar cs-avatar-wa"><Icon name="message-circle" :size="17" /></span>
          <div class="min-w-0 flex-1 cursor-pointer" @click="openThread(r)">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[13.5px] font-bold text-stone-900">{{ r.customer || r.phone }}</span>
              <span v-if="r.customer" class="font-mono text-[11px] text-stone-400">{{ r.phone }}</span>
              <span v-if="r.order" class="font-mono text-[11px] text-violet-600">{{ r.order }}</span>
              <span v-if="r.msgCount > 1" class="text-[10px] font-bold text-violet-700 bg-violet-50 ring-1 ring-violet-200 rounded-full px-2 py-0.5 tabular-nums">×{{ r.msgCount }}</span>
              <span v-if="r.images" class="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 rounded-full px-2 py-0.5 tabular-nums">
                <Icon name="image" :size="10" />{{ r.images }}
              </span>
            </div>
            <div class="text-[12px] text-stone-600 truncate max-w-[520px] mt-1" dir="auto">
              {{ r.message || (r.images ? t('cs.photoMsg') : '') }}
            </div>
            <div class="flex items-center gap-2 text-[10.5px] text-stone-400 tabular-nums mt-0.5">
              <span>{{ r.lastAt.slice(5) }}</span>
              <span class="inline-flex items-center gap-1 text-violet-500 font-medium">
                <Icon :name="threadFor === r.id ? 'chevron-up' : 'chevron-down'" :size="10" />{{ t('cs.thread') }}
              </span>
            </div>
          </div>
          <a :href="'https://wa.me/' + r.phone" target="_blank" title="WhatsApp" class="cs-contact cs-wa">
            <Icon name="message-circle" :size="15" />
          </a>
          <div class="flex items-center gap-1.5">
            <button class="cs-act cs-act-main" :disabled="busy === r.id" @click="openCreateFromWa(r)">
              <Icon name="plus" :size="14" class="inline -mt-px me-1" />{{ t('cs.toTicket') }}
            </button>
            <button class="cs-act cs-act-soft text-stone-500" :disabled="busy === r.id" :title="t('cs.dismiss')"
                    @click="dismiss(r)"><Icon name="x" :size="15" /></button>
          </div>
        </div>
        <Transition name="csslide">
          <div v-if="threadFor === r.id" class="bg-stone-50 rounded-xl p-3 mt-3 max-h-[320px] overflow-y-auto space-y-1.5">
            <div v-if="threadLoading" class="text-[12px] text-stone-400 text-center py-3">…</div>
            <template v-else>
              <div v-for="(m, i) in thread" :key="i" class="flex" :class="m.in ? 'justify-start' : 'justify-end'">
                <div class="max-w-[75%] rounded-xl px-3 py-1.5 text-[12px]"
                     :class="m.in ? 'bg-white ring-1 ring-stone-200 text-stone-800' : 'bg-emerald-50 ring-1 ring-emerald-200 text-emerald-900'"
                     dir="auto">
                  <span v-if="m.kind === 'image'" class="inline-flex items-center gap-1 text-stone-500"><Icon name="image" :size="12" />{{ t('cs.photoMsg') }}</span>
                  <template v-if="m.text"> {{ m.text }}</template>
                  <div class="text-[9.5px] text-stone-400 tabular-nums mt-0.5">{{ m.at.slice(5) }}</div>
                </div>
              </div>
              <div v-if="!thread.length" class="text-[12px] text-stone-400 text-center py-3">—</div>
            </template>
          </div>
        </Transition>
        <Transition name="csslide">
          <div v-if="createFor === r.id" class="bg-violet-50/50 rounded-xl p-3 mt-3">
            <TicketForm :categories="data?.categories || []" :busy="creating"
                        :init="{ subject: r.message.slice(0, 100), phone: r.phone, order: r.order, channel: 'whatsapp', waPhone: r.phone }"
                        @submit="submitCreate" />
          </div>
        </Transition>
      </div>
    </TransitionGroup>

    <!-- TICKET rows -->
    <TransitionGroup v-else name="csrow" tag="div" class="space-y-2.5 relative">
      <div v-for="r in rows" :key="r.id" class="cs-card rounded-2xl p-4"
           :class="r.respBreached || r.resoBreached ? 'cs-card-breach' : ''">
        <div class="flex items-center gap-3.5 flex-wrap">
          <span class="cs-avatar" :class="r.respBreached || r.resoBreached ? 'cs-avatar-breach' : ''">
            <Icon :name="r.channel === 'whatsapp' ? 'message-circle' : 'phone'" :size="16" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[13.5px] font-bold text-stone-900 truncate max-w-[340px]" dir="auto">{{ r.subject }}</span>
              <span class="cs-chip" :class="statusClass(r.status)">{{ t('cs.st' + r.status.replace(' ', ''), r.status) }}</span>
              <span v-if="r.category" class="cs-chip text-stone-600 bg-stone-100">{{ r.category }}</span>
              <span v-if="r.respBreached" class="cs-breach">{{ t('cs.respLate') }}</span>
              <span v-else-if="r.resoBreached" class="cs-breach">{{ t('cs.resoLate') }}</span>
            </div>
            <div class="flex items-center gap-2.5 text-[11.5px] text-stone-500 tabular-nums mt-1 flex-wrap">
              <span class="font-mono text-[10.5px] text-stone-400">{{ r.id }}</span>
              <span v-if="r.order" class="font-mono text-violet-600">{{ r.order }}</span>
              <span v-if="r.phone" class="font-mono">{{ r.phone }}</span>
              <span class="inline-flex items-center gap-1"><Icon name="clock" :size="11" />{{ ageLabel(r.ageH) }}</span>
              <span v-if="r.agent" :class="r.mine ? 'text-violet-600 font-semibold' : 'text-stone-400'">{{ r.agent }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1.5">
            <a v-if="r.phone" :href="'tel:' + r.phone" :title="r.phone" class="cs-contact cs-tel"><Icon name="phone" :size="15" /></a>
            <a v-if="r.phone" :href="'https://wa.me/' + r.phone.replace(/[^0-9]/g, '')" target="_blank" class="cs-contact cs-wa"><Icon name="message-circle" :size="15" /></a>
          </div>
          <div class="flex items-center gap-1.5 flex-wrap">
            <template v-if="tab !== 'resolved'">
              <button v-if="!r.mine" class="cs-act cs-act-soft text-violet-700" :disabled="busy === r.id"
                      :title="t('cs.actTake')" @click="act(r, 'take')"><Icon name="user" :size="15" /></button>
              <button class="cs-act cs-act-soft text-sky-700" :disabled="busy === r.id" :title="t('cs.actReply')"
                      :class="noteFor === r.id && noteAction === 'reply' ? 'ring-2' : ''"
                      @click="openNote(r, 'reply')"><Icon name="corner-down-left" :size="15" /></button>
              <button class="cs-act cs-act-soft text-stone-500" :disabled="busy === r.id" :title="t('cs.actHold')"
                      @click="act(r, 'hold')"><Icon name="circle-pause" :size="15" /></button>
              <button class="cs-act cs-act-main" :disabled="busy === r.id"
                      :class="noteFor === r.id && noteAction === 'resolve' ? 'ring-2 ring-white' : ''"
                      @click="openNote(r, 'resolve')">
                <Icon name="check" :size="14" class="inline -mt-px me-1" />{{ t('cs.actResolve') }}
              </button>
            </template>
            <button v-else class="cs-act cs-act-soft text-amber-700" :disabled="busy === r.id" :title="t('cs.actReopen')"
                    @click="act(r, 'reopen')"><Icon name="rotate-ccw" :size="15" /></button>
          </div>
        </div>
        <Transition name="csslide">
          <div v-if="noteFor === r.id" class="flex items-center gap-2 bg-violet-50/60 rounded-xl p-2.5 mt-3">
            <input v-model="note" :placeholder="noteAction === 'resolve' ? t('cs.resolvePh') : t('cs.replyPh')" maxlength="200"
                   class="flex-1 h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-violet-200 text-[12.5px] focus:outline-none" dir="auto" />
            <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-50 transition-colors"
                    :disabled="!note.trim() || busy === r.id"
                    @click="act(r, noteAction, note)">{{ t('rs.confirmDecision') }}</button>
          </div>
        </Transition>
      </div>
    </TransitionGroup>

    <!-- pager -->
    <div v-if="!loading && total > pageSize" class="flex items-center justify-between px-1">
      <span class="text-[11.5px] text-stone-500 tabular-nums">
        {{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, total) }} / {{ total }}
      </span>
      <div class="flex items-center gap-1">
        <button class="pg-btn" :disabled="page <= 1" @click="page--; load()"><Icon name="chevron-left" :size="13" class="flip-rtl" /></button>
        <button class="pg-btn" :disabled="page * pageSize >= total" @click="page++; load()"><Icon name="chevron-right" :size="13" class="flip-rtl" /></button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const tabs = computed(() => {
  const base = [
    { key: "open", label: "cs.tabOpen", icon: "file-text", onColor: "bg-violet-100 text-violet-700" },
    { key: "mine", label: "cs.tabMine", icon: "user", onColor: "bg-sky-100 text-sky-700" },
    { key: "resolved", label: "cs.tabResolved", icon: "check-circle", onColor: "bg-emerald-100 text-emerald-700" },
  ];
  if (data.value?.hasWhatsapp !== false) {
    base.unshift({ key: "inbox", label: "cs.tabInbox", icon: "message-circle", onColor: "bg-emerald-100 text-emerald-700" });
  }
  return base;
});

// Inline ticket form (create panel + convert-from-WhatsApp) — one tiny
// component so both spots stay identical.
const TicketForm = defineComponent({
  props: ["categories", "busy", "init"],
  emits: ["submit"],
  setup(props, { emit }) {
    const f = ref({
      subject: props.init?.subject || "", phone: props.init?.phone || "",
      order: props.init?.order || "", category: "",
      description: "", channel: props.init?.channel || "manual",
      waPhone: props.init?.waPhone || "",
    });
    return () => h("div", { class: "space-y-2.5" }, [
      h("div", { class: "flex flex-wrap gap-2" }, [
        h("input", { class: "flex-1 min-w-[260px] h-10 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] focus:outline-none", dir: "auto",
                     placeholder: t("cs.fSubject"), value: f.value.subject, maxlength: 140,
                     onInput: (e) => (f.value.subject = e.target.value) }),
        h("input", { class: "w-[160px] h-10 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] font-mono focus:outline-none",
                     placeholder: t("cf.phonePh"), value: f.value.phone, maxlength: 20,
                     onInput: (e) => (f.value.phone = e.target.value) }),
        h("input", { class: "w-[150px] h-10 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] font-mono focus:outline-none",
                     placeholder: t("cs.fOrder"), value: f.value.order, maxlength: 30,
                     onInput: (e) => (f.value.order = e.target.value) }),
      ]),
      h("div", { class: "flex flex-wrap gap-1.5" }, (props.categories || []).map((c) =>
        h("button", { class: "h-7 px-2.5 rounded-full text-[11.5px] font-medium ring-1 transition-all " +
                        (f.value.category === c ? "text-white bg-violet-600 ring-violet-600" : "text-violet-700 bg-white ring-violet-200 hover:bg-violet-50"),
                      onClick: () => (f.value.category = c) }, c))),
      h("div", { class: "flex items-center gap-2" }, [
        h("input", { class: "flex-1 h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none", dir: "auto",
                     placeholder: t("cs.fDesc"), value: f.value.description, maxlength: 500,
                     onInput: (e) => (f.value.description = e.target.value) }),
        h("button", { class: "h-9 px-4 rounded-lg text-[12px] font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-50 transition-colors",
                      disabled: props.busy || !f.value.subject.trim(),
                      onClick: () => emit("submit", { ...f.value }) },
          props.busy ? "…" : t("cs.fCreate")),
      ]),
    ]);
  },
});

const tab = ref("inbox");
const q = ref("");
const page = ref(1);
const pageSize = 30;
const data = ref(null);
const rows = ref([]);
const total = ref(0);
const loading = ref(true);
const busy = ref("");
const createFor = ref("");
const creating = ref(false);
const noteFor = ref("");
const noteAction = ref("");
const note = ref("");
const loadError = ref("");

let qTimer = null;
function debouncedLoad() {
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { page.value = 1; load(); }, 350);
}

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const res = await api("tickets.board", {
      tab: tab.value, q: q.value, limit: pageSize,
      offset: (page.value - 1) * pageSize,
    });
    data.value = res;
    rows.value = res.rows || [];
    total.value = res.total || 0;
    if (tab.value === "inbox" && res.hasWhatsapp === false) {
      tab.value = "open";
      return load();
    }
  } catch (e) {
    loadError.value = String(e.message || e);
    warn(t("cf.loadFail"), loadError.value);
    rows.value = [];
  } finally {
    loading.value = false;
  }
}
onMounted(load);

function resetForm() { /* form state lives inside TicketForm per mount */ }

function openCreateFromWa(r) {
  createFor.value = createFor.value === r.id ? "" : r.id;
}

const threadFor = ref("");
const thread = ref([]);
const threadLoading = ref(false);

async function openThread(r) {
  if (threadFor.value === r.id) { threadFor.value = ""; return; }
  threadFor.value = r.id;
  thread.value = [];
  threadLoading.value = true;
  try {
    const res = await api("tickets.wa_thread", { phone: r.phone });
    if (threadFor.value === r.id) thread.value = res.messages || [];
  } catch (e) {
    warn(t("cf.loadFail"), String(e.message || e));
    threadFor.value = "";
  } finally {
    threadLoading.value = false;
  }
}

async function submitCreate(f) {
  creating.value = true;
  try {
    const res = await apiPost("tickets.create_ticket", {
      subject: f.subject, phone: f.phone, order: f.order, category: f.category,
      description: f.description, channel: f.channel, wa_phone: f.waPhone,
    });
    success(t("cs.created"), res.ticket);
    if (f.waPhone) {
      rows.value = rows.value.filter((x) => x.id !== f.waPhone);
      if (data.value?.counts) data.value.counts.inbox = Math.max(0, data.value.counts.inbox - 1);
    }
    if (data.value?.counts) data.value.counts.open++;
    if (data.value?.mine) data.value.mine.create++;
    createFor.value = "";
  } catch (e) {
    warn(t("cs.createFail"), String(e.message || e));
  } finally {
    creating.value = false;
  }
}

async function dismiss(r) {
  busy.value = r.id;
  try {
    await apiPost("tickets.wa_dismiss", { phone: r.phone });
    rows.value = rows.value.filter((x) => x.id !== r.id);
    total.value = Math.max(0, total.value - 1);
    if (data.value?.counts) data.value.counts.inbox = Math.max(0, data.value.counts.inbox - 1);
    success(t("cs.dismissed"), r.phone);
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

function openNote(r, action) {
  if (noteFor.value === r.id && noteAction.value === action) { noteFor.value = ""; return; }
  noteFor.value = r.id;
  noteAction.value = action;
  note.value = "";
}

async function act(r, action, n) {
  busy.value = r.id;
  try {
    const res = await apiPost("tickets.act", { name: r.id, action, note: n });
    if (action === "resolve") {
      rows.value = rows.value.filter((x) => x.id !== r.id);
      total.value = Math.max(0, total.value - 1);
      if (data.value?.counts) {
        data.value.counts[tab.value] = Math.max(0, (data.value.counts[tab.value] || 1) - 1);
        data.value.counts.resolved++;
      }
      if (data.value?.mine) data.value.mine.resolve++;
    } else if (action === "reopen") {
      rows.value = rows.value.filter((x) => x.id !== r.id);
      if (data.value?.counts) { data.value.counts.resolved--; data.value.counts.open++; }
    } else {
      const row = rows.value.find((x) => x.id === r.id);
      if (row) {
        row.status = res.status;
        if (action === "take") { row.mine = true; row.agent = "me"; }
        if (action === "reply") row.respBreached = false;
      }
      if (action === "reply" && data.value?.mine) data.value.mine.reply++;
    }
    noteFor.value = "";
    note.value = "";
    success(t(`cs.done_${action}`), r.id);
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

function statusClass(s) {
  if (s === "Open") return "text-violet-700 bg-violet-50";
  if (s === "Replied") return "text-sky-700 bg-sky-50";
  if (s === "On Hold") return "text-stone-600 bg-stone-100";
  if (s === "Resolved") return "text-emerald-700 bg-emerald-50";
  return "text-stone-600 bg-stone-100";
}
function ageLabel(hs) {
  return hs < 48 ? `${hs}${t('cf.hrs')}` : `${Math.round(hs / 24)}${t('cf.days')}`;
}
</script>

<style scoped>
.cs-hero {
  background: linear-gradient(135deg, rgb(245 243 255) 0%, #fff 45%, #fff 70%, rgb(245 243 255) 100%);
  box-shadow: inset 0 0 0 1px rgb(221 214 254 / 0.7), 0 1px 2px rgb(0 0 0 / 0.03);
}
.cs-hero-icon {
  width: 52px; height: 52px; border-radius: 16px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  color: white;
  background: linear-gradient(135deg, rgb(139 92 246), rgb(109 40 217));
  box-shadow: 0 6px 16px -6px rgb(139 92 246 / 0.55);
}
.cs-stat {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-width: 78px; padding: 8px 14px; border-radius: 14px;
  background: rgb(255 255 255 / 0.75); backdrop-filter: blur(4px);
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.9), 0 1px 2px rgb(0 0 0 / 0.03);
}
.cs-stat-n { font-size: 21px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.cs-stat-l { font-size: 10px; font-weight: 600; color: rgb(168 162 158); margin-top: 4px; white-space: nowrap; }
.cs-new {
  height: 40px; padding: 0 16px; border-radius: 12px;
  font-size: 12.5px; font-weight: 700; color: white;
  background: linear-gradient(135deg, rgb(139 92 246), rgb(109 40 217));
  box-shadow: 0 4px 12px -4px rgb(139 92 246 / 0.45);
  transition: all .15s ease;
}
.cs-new:hover { transform: translateY(-1px); box-shadow: 0 6px 16px -4px rgb(139 92 246 / 0.55); }

.cs-seg { display: inline-flex; gap: 2px; padding: 4px; background: rgb(231 229 228 / 0.55); border-radius: 14px; }
.cs-seg-btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 36px; padding: 0 12px; border-radius: 11px;
  font-size: 12.5px; font-weight: 600; color: rgb(120 113 108);
  transition: all .18s ease;
}
.cs-seg-btn:hover { color: rgb(41 37 36); }
.cs-seg-on { background: white; color: rgb(28 25 23); box-shadow: 0 1px 3px rgb(0 0 0 / 0.08), 0 1px 2px rgb(0 0 0 / 0.04); }
.cs-seg-count { font-size: 11px; font-weight: 700; font-variant-numeric: tabular-nums; padding: 1px 7px; border-radius: 999px; }

.cs-card {
  background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8), 0 1px 2px rgb(0 0 0 / 0.02);
  transition: box-shadow .18s ease, transform .18s ease;
}
.cs-card:hover {
  box-shadow: inset 0 0 0 1px rgb(214 211 209), 0 8px 24px -12px rgb(0 0 0 / 0.14);
  transform: translateY(-1px);
}
.cs-card-breach { box-shadow: inset 0 0 0 1.5px rgb(253 164 175), 0 4px 16px -8px rgb(244 63 94 / 0.2); }
.cs-avatar {
  width: 42px; height: 42px; border-radius: 999px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  color: rgb(109 40 217);
  background: linear-gradient(135deg, rgb(245 243 255), rgb(237 233 254));
  box-shadow: inset 0 0 0 1px rgb(221 214 254);
}
.cs-avatar-wa {
  color: rgb(22 163 74);
  background: linear-gradient(135deg, rgb(240 253 244), rgb(220 252 231));
  box-shadow: inset 0 0 0 1px rgb(187 247 208);
}
.cs-avatar-breach {
  color: rgb(225 29 72);
  background: linear-gradient(135deg, rgb(255 241 242), rgb(255 228 230));
  box-shadow: inset 0 0 0 1px rgb(253 164 175);
}
.cs-chip {
  font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 999px;
}
.cs-breach {
  font-size: 10px; font-weight: 800; letter-spacing: .02em;
  color: white; background: rgb(244 63 94);
  padding: 2px 8px; border-radius: 999px;
  animation: cs-pulse 2s ease-in-out infinite;
}
@keyframes cs-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .55; } }

.cs-contact {
  width: 38px; height: 38px; border-radius: 12px;
  display: inline-flex; align-items: center; justify-content: center;
  background: white; box-shadow: inset 0 0 0 1px rgb(231 229 228);
  transition: all .15s ease;
}
.cs-contact:hover { transform: scale(1.06); }
.cs-tel { color: rgb(87 83 78); }
.cs-tel:hover { color: rgb(4 120 87); box-shadow: inset 0 0 0 1px rgb(110 231 183); }
.cs-wa { color: rgb(22 163 74); }
.cs-wa:hover { box-shadow: inset 0 0 0 1px rgb(134 239 172); background: rgb(240 253 244); }
.cs-act {
  height: 38px; border-radius: 12px; font-size: 12.5px; font-weight: 700;
  transition: all .15s ease; white-space: nowrap;
}
.cs-act:disabled { opacity: .5; }
.cs-act-main {
  padding: 0 16px; color: white;
  background: linear-gradient(135deg, rgb(139 92 246), rgb(109 40 217));
  box-shadow: 0 4px 12px -4px rgb(139 92 246 / 0.4);
}
.cs-act-main:hover { box-shadow: 0 6px 16px -4px rgb(139 92 246 / 0.55); transform: translateY(-1px); }
.cs-act-soft {
  width: 38px; background: rgb(250 250 249);
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  display: inline-flex; align-items: center; justify-content: center;
}
.cs-act-soft:hover { background: white; transform: scale(1.06); box-shadow: inset 0 0 0 1px currentColor; }

.cs-empty { background: linear-gradient(180deg, white, rgb(250 250 249)); box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8); }
.cs-shimmer {
  background: linear-gradient(90deg, rgb(245 245 244) 25%, rgb(231 229 228 / 0.6) 50%, rgb(245 245 244) 75%);
  background-size: 200% 100%;
  animation: cs-shimmer 1.4s ease-in-out infinite;
}
@keyframes cs-shimmer { to { background-position: -200% 0; } }
.pg-btn {
  width: 32px; height: 32px; border-radius: 10px; background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  display: inline-flex; align-items: center; justify-content: center;
}
.pg-btn:disabled { opacity: .4; }

.csrow-leave-active { transition: all .28s ease; position: relative; }
.csrow-leave-to { opacity: 0; transform: translateX(24px) scale(.98); }
.csrow-enter-active { transition: all .25s ease; }
.csrow-enter-from { opacity: 0; transform: translateY(6px); }
.csrow-move { transition: transform .28s ease; }
.csslide-enter-active, .csslide-leave-active { transition: all .2s ease; }
.csslide-enter-from, .csslide-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
