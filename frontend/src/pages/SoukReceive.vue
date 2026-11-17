<template>
  <!-- Souk receiving, at the door when the taxi arrives. Per variant: good,
       broken by WHERE it broke (at the stall → the stall owes it; in transport
       or in our warehouse → our loss, each in its own account), and the rest
       is short (the stall owes it). Good pieces go onto a real shelf (sellable,
       on Shopify) minus the studio samples; ours broken go to Defective Items.
       One receiving per purchase, then the PO closes. Backend:
       souk.receive_queue / receive_boot / receive. -->
  <div class="max-w-[560px] mx-auto px-4 pt-4 pb-40 space-y-4">
    <header class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="text-[11.5px] font-semibold text-stone-500">{{ t('souk.recvKicker') }}</div>
        <h1 class="text-[18px] font-bold text-stone-900 truncate">{{ b ? (b.title || b.po) : t('souk.recvTitle') }}</h1>
        <div v-if="b" class="text-[11.5px] text-stone-500 font-mono" dir="ltr">{{ b.po }} · {{ b.stall }} · {{ t('souk.tripNo').replace('{n}', b.trip) }}</div>
      </div>
      <router-link v-if="po" :to="{ name: 'SoukReceive' }" class="shrink-0 h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center">{{ t('souk.recvList') }}</router-link>
    </header>

    <div v-if="loading" class="h-[280px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <!-- queue -->
    <template v-else-if="!po">
      <div v-if="!queue.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-8 text-center text-[13px] text-stone-500">{{ t('souk.recvNone') }}</div>
      <router-link v-for="r in queue" :key="r.po" :to="{ name: 'SoukReceive', params: { po: r.po } }"
                   class="flex items-center gap-3 bg-white ring-1 ring-stone-200/70 rounded-2xl p-3 hover:ring-stone-400">
        <img v-if="r.image" :src="r.image" class="w-12 h-12 rounded-xl object-cover ring-1 ring-stone-200" alt="" />
        <div v-else class="w-12 h-12 rounded-xl bg-stone-100" />
        <div class="min-w-0 flex-1">
          <div class="text-[13px] font-semibold truncate">{{ r.title || r.po }}</div>
          <div class="text-[11.5px] text-stone-500 truncate">{{ r.stall }} · {{ r.units }} {{ t('souk.pcs') }} · {{ r.date }}</div>
        </div>
        <Icon :name="isRTL ? 'chevron-left' : 'chevron-right'" :size="16" class="text-stone-400" />
      </router-link>
    </template>

    <!-- done -->
    <section v-else-if="result" class="space-y-3">
      <div class="bg-emerald-50 ring-1 ring-emerald-200 rounded-2xl p-4 space-y-1">
        <div class="text-[15px] font-bold text-emerald-900">{{ t('souk.recvDone').replace('{n}', result.good) }}</div>
        <div class="text-[12.5px] text-emerald-800 font-mono">{{ result.receipt }}<span v-if="result.debitNote"> · {{ result.debitNote }}</span></div>
        <div v-if="result.labels" class="text-[12.5px] text-emerald-800">{{ t('souk.labelsQueued').replace('{n}', result.labels) }}</div>
      </div>
      <div v-if="result.owed" class="bg-amber-50 ring-1 ring-amber-200 rounded-2xl p-4 text-[13px] text-amber-900">
        {{ t('souk.owedLine').replace('{n}', fmt(result.owed)).replace('{s}', b.stall) }}
      </div>
      <div v-for="(n, i) in result.notes" :key="i" class="bg-stone-50 ring-1 ring-stone-200 rounded-xl p-3 text-[12px] text-stone-700">{{ n }}</div>
      <div class="grid grid-cols-2 gap-2">
        <router-link :to="{ name: 'SoukReceive' }" class="h-12 rounded-xl bg-white ring-1 ring-stone-300 text-[13px] font-bold inline-flex items-center justify-center">{{ t('souk.recvNext') }}</router-link>
        <router-link v-if="result.product" :to="{ name: 'SoukProduct', params: { name: result.product } }" class="h-12 rounded-xl bg-stone-900 text-white text-[13px] font-bold inline-flex items-center justify-center">{{ t('souk.toProduct') }}</router-link>
      </div>
    </section>

    <div v-else-if="b && b.done" class="bg-stone-50 ring-1 ring-stone-200 rounded-2xl p-5 text-[13px] text-stone-700">
      {{ t('souk.recvAlready').replace('{pr}', b.done) }}
    </div>

    <template v-else-if="b">
      <!-- per variant -->
      <section v-for="l in b.lines" :key="l.itemCode" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
        <div class="flex items-center justify-between gap-2">
          <div class="min-w-0">
            <div class="font-mono text-[14px] font-bold">{{ l.sku }}</div>
            <div class="text-[11.5px] text-stone-500 truncate">{{ l.label }}</div>
          </div>
          <div class="text-end">
            <div class="text-[11px] text-stone-500">{{ t('souk.bought') }}</div>
            <div class="text-[18px] font-extrabold tabular-nums">{{ pending(l) }}</div>
          </div>
        </div>

        <div class="grid grid-cols-[1fr_auto] gap-2 items-center">
          <label class="text-[12.5px] font-semibold text-emerald-800">{{ t('souk.good') }}</label>
          <Stepper v-model="c[l.itemCode].good" :max="pending(l)" tone="good" />
        </div>

        <button class="text-[12px] font-semibold" :class="open[l.itemCode] || brokenOf(l) ? 'text-rose-700' : 'text-stone-500'"
                @click="open[l.itemCode] = !open[l.itemCode]">
          {{ t('souk.brokenQ') }}<span v-if="brokenOf(l)"> · {{ brokenOf(l) }}</span>
        </button>
        <div v-if="open[l.itemCode] || brokenOf(l)" class="rounded-xl bg-rose-50/60 ring-1 ring-rose-100 p-3 space-y-2">
          <div v-for="w in WHERE" :key="w" class="grid grid-cols-[1fr_auto] gap-2 items-center">
            <div>
              <div class="text-[12.5px] font-semibold text-stone-800">{{ t('souk.br_' + w) }}</div>
              <div class="text-[10.5px] text-stone-500">{{ t('souk.brh_' + w) }}</div>
            </div>
            <Stepper v-model="c[l.itemCode][w]" :max="pending(l)" tone="bad" />
          </div>
        </div>

        <div class="flex items-center justify-between text-[12px] rounded-lg px-3 py-2"
             :class="over(l) ? 'bg-rose-100 text-rose-800' : shortOf(l) ? 'bg-amber-50 text-amber-900' : 'bg-stone-50 text-stone-600'">
          <span>{{ over(l) ? t('souk.tooMany') : t('souk.short') }}</span>
          <b class="tabular-nums">{{ over(l) ? '' : shortOf(l) }}</b>
        </div>

        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="text-[11.5px] font-semibold text-stone-600">{{ t('souk.weightG') }}</label>
            <input v-model.number="c[l.itemCode].grams" type="number" inputmode="numeric" placeholder="g"
                   class="w-full h-10 rounded-lg ring-1 ring-stone-300 px-3 text-[14px] tabular-nums" />
          </div>
          <div v-if="b.studioSamples">
            <label class="text-[11.5px] font-semibold text-stone-600">{{ t('souk.toStudio') }}</label>
            <input v-model.number="studio[l.itemCode]" type="number" inputmode="numeric" min="0"
                   class="w-full h-10 rounded-lg ring-1 ring-stone-300 px-3 text-[14px] tabular-nums" />
          </div>
        </div>
      </section>

      <!-- broken photo -->
      <section v-if="anyBroken" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 flex items-center gap-3">
        <label class="w-14 h-14 shrink-0 rounded-xl ring-1 ring-stone-300 bg-stone-50 flex items-center justify-center overflow-hidden cursor-pointer">
          <img v-if="brokenPreview" :src="brokenPreview" class="w-full h-full object-cover" alt="" />
          <Icon v-else name="image" :size="20" class="text-stone-400" />
          <input type="file" accept="image/*" capture="environment" class="hidden" @change="pickBroken" />
        </label>
        <div class="text-[12px] text-stone-600">{{ t('souk.brokenPhoto') }}</div>
      </section>

      <!-- where -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
        <label class="text-[12px] font-semibold text-stone-600">{{ t('souk.shelf') }}</label>
        <select v-model="target" class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-2 text-[14px] bg-white">
          <option value="">—</option>
          <option v-for="w in b.shelves" :key="w" :value="w">{{ shortWh(w) }}</option>
        </select>
        <p class="text-[11px] text-stone-500">{{ t('souk.shelfHint') }}</p>
        <label class="flex items-center gap-2 text-[12.5px] text-stone-700 pt-1">
          <input v-model="labels" type="checkbox" class="rounded" />{{ t('souk.printLabels').replace('{n}', totalGood) }}
        </label>
        <input v-model="note" :placeholder="t('souk.note')" class="w-full h-10 rounded-lg ring-1 ring-stone-300 px-3 text-[13px]" />
      </section>

      <!-- money summary -->
      <section v-if="owed > 0" class="bg-amber-50 ring-1 ring-amber-200 rounded-2xl p-4 text-[12.5px] text-amber-900 space-y-1">
        <div class="font-bold">{{ t('souk.owedLine').replace('{n}', fmt(owed)).replace('{s}', b.stall) }}</div>
        <div>{{ b.hasInvoice ? t('souk.owedDebit') : t('souk.owedNoBooks') }}</div>
      </section>
      <section v-if="ourBroken.transport && !b.lossAccounts.transport || ourBroken.warehouse && !b.lossAccounts.warehouse"
               class="bg-stone-50 ring-1 ring-stone-200 rounded-2xl p-3 text-[12px] text-stone-600">
        {{ t('souk.lossWaits') }}
      </section>
    </template>

    <footer v-if="b && !b.done && !result" class="fixed inset-x-0 bottom-0 bg-white border-t border-stone-200 px-4 pt-3 pb-5 z-20">
      <div class="max-w-[560px] mx-auto space-y-2">
        <div class="flex items-center justify-between text-[12.5px] text-stone-600 tabular-nums">
          <span>{{ t('souk.good') }} <b class="text-stone-900">{{ totalGood }}</b></span>
          <span>{{ t('souk.brokenShort') }} <b class="text-rose-700">{{ totalBroken }}</b></span>
          <span>{{ t('souk.short') }} <b class="text-amber-800">{{ totalShort }}</b></span>
        </div>
        <button class="w-full h-12 rounded-xl bg-emerald-600 text-white text-[14px] font-bold disabled:opacity-40"
                :disabled="busy || !canPost" @click="post">
          {{ busy ? t('souk.sending') : nothingCame ? t('souk.allShort') : t('souk.recvPost') }}
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, defineComponent, h } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { uploadPhoto } from "@/lib/soukPhoto";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

// − n + with big targets: counted with a thumb, often with gloves on.
const Stepper = defineComponent({
  props: { modelValue: { type: Number, default: 0 }, max: { type: Number, default: 9999 }, tone: String },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const set = (v) => emit("update:modelValue", Math.max(0, Math.min(props.max, Number(v) || 0)));
    return () => h("div", { class: "flex items-center gap-1.5" }, [
      h("button", { class: "w-11 h-11 rounded-xl ring-1 ring-stone-300 text-[18px] font-bold", onClick: () => set(props.modelValue - 1) }, "−"),
      h("input", {
        type: "number", inputmode: "numeric", value: props.modelValue,
        class: "w-[68px] h-11 rounded-xl ring-1 ring-stone-300 text-center text-[17px] font-extrabold tabular-nums "
          + (props.tone === "good" ? "text-emerald-800" : "text-rose-700"),
        onInput: (e) => set(e.target.value),
      }),
      h("button", { class: "w-11 h-11 rounded-xl ring-1 ring-stone-300 text-[18px] font-bold", onClick: () => set(props.modelValue + 1) }, "+"),
    ]);
  },
});

const WHERE = ["supplier", "transport", "warehouse"];
const { t, isRTL } = useI18n();
const { warn } = useToast();
const route = useRoute();
const po = computed(() => route.params.po || "");
const loading = ref(true);
const busy = ref(false);
const queue = ref([]);
const b = ref(null);
const c = reactive({});
const open = reactive({});
const studio = reactive({});
const target = ref("");
const labels = ref(true);
const note = ref("");
const result = ref(null);
const brokenFile = ref(null);
const brokenPreview = ref("");

const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const shortWh = (w) => (w || "").replace(/ - JM$/, "");
const pending = (l) => Math.max(0, Math.round(l.ordered - l.already));
const brokenOf = (l) => WHERE.reduce((s, w) => s + (Number(c[l.itemCode]?.[w]) || 0), 0);
const arrived = (l) => (Number(c[l.itemCode]?.good) || 0) + brokenOf(l);
const over = (l) => arrived(l) > pending(l);
const shortOf = (l) => Math.max(0, pending(l) - arrived(l));
const lines = computed(() => b.value?.lines || []);
const totalGood = computed(() => lines.value.reduce((s, l) => s + (Number(c[l.itemCode]?.good) || 0), 0));
const totalBroken = computed(() => lines.value.reduce((s, l) => s + brokenOf(l), 0));
const totalShort = computed(() => lines.value.reduce((s, l) => s + shortOf(l), 0));
const anyBroken = computed(() => totalBroken.value > 0);
const ourBroken = computed(() => ({
  transport: lines.value.some((l) => Number(c[l.itemCode]?.transport) > 0),
  warehouse: lines.value.some((l) => Number(c[l.itemCode]?.warehouse) > 0),
}));
const owed = computed(() => lines.value.reduce(
  (s, l) => s + (shortOf(l) + (Number(c[l.itemCode]?.supplier) || 0)) * l.rate, 0));
const nothingCame = computed(() => lines.value.length > 0 && totalGood.value + totalBroken.value === 0);
const needsShelf = computed(() => lines.value.some((l) => {
  const x = c[l.itemCode] || {};
  return (Number(x.good) || 0) + (Number(x.transport) || 0) + (Number(x.warehouse) || 0) > 0;
}));
const canPost = computed(() => (!needsShelf.value || !!target.value) && lines.value.length
  && !lines.value.some(over)
  && lines.value.every((l) => (Number(studio[l.itemCode]) || 0) <= (Number(c[l.itemCode]?.good) || 0)));

function pickBroken(e) {
  const f = e.target.files?.[0];
  if (!f) return;
  brokenFile.value = f;
  brokenPreview.value = URL.createObjectURL(f);
}

function initForm() {
  for (const l of b.value.lines) {
    c[l.itemCode] = { good: pending(l), supplier: 0, transport: 0, warehouse: 0, grams: l.grams || null };
    studio[l.itemCode] = 0;
  }
  // The studio takes its samples from the first variant (the main colour).
  if (b.value.studioSamples && b.value.studioDefault) {
    studio[b.value.studioDefault] = Math.min(b.value.studioSamples, pending(b.value.lines[0]));
  }
}

async function load() {
  loading.value = true;
  result.value = null;
  try {
    if (!po.value) {
      queue.value = (await api("souk.receive_queue")).rows;
      b.value = null;
    } else {
      b.value = await api("souk.receive_boot", { po: po.value });
      initForm();
    }
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

async function post() {
  const msg = nothingCame.value ? t("souk.allShortConfirm").replace("{n}", fmt(owed.value)) : t("souk.recvConfirm").replace("{g}", totalGood.value).replace("{b}", totalBroken.value)
    .replace("{s}", totalShort.value).replace("{w}", shortWh(target.value));
  if (!window.confirm(msg)) return;
  busy.value = true;
  try {
    if (brokenFile.value) {
      try { await uploadPhoto("broken", b.value.po, brokenFile.value); } catch (_) { /* proof is secondary */ }
    }
    result.value = await apiPost("souk.receive", { po: b.value.po, payload: JSON.stringify({
      target: target.value, labels: labels.value ? 1 : 0, note: note.value, nothingCame: nothingCame.value ? 1 : 0,
      studio: { ...studio },
      lines: b.value.lines.map((l) => ({
        itemCode: l.itemCode, good: c[l.itemCode].good, grams: c[l.itemCode].grams,
        broken: { supplier: c[l.itemCode].supplier, transport: c[l.itemCode].transport, warehouse: c[l.itemCode].warehouse },
      })),
    }) });
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

// Broken pieces come out of the good count, never on top of it.
watch(() => lines.value.map((l) => WHERE.map((w) => c[l.itemCode]?.[w]).join(",")).join("|"), () => {
  for (const l of lines.value) {
    const x = c[l.itemCode];
    if (x && arrived(l) > pending(l)) x.good = Math.max(0, pending(l) - brokenOf(l));
  }
});
watch(po, load);
onMounted(load);
</script>
