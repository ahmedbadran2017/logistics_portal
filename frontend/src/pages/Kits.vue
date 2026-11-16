<template>
  <!-- Kits: a product the floor assembles from other products (MCH09178 =
       one set each of MCH009884 + MCH09176 + MCH09177 → 3 kits). Assemble
       records ERPNext's Repack — components out at their cost, kits in at
       exactly that cost — and prints one SKU label per kit. Backend: kits.py -->
  <div class="max-w-[980px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('kit.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[680px]">{{ t('kit.intro') }}</p>
      </div>
      <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12.5px] font-semibold text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
              :disabled="loading" @click="load">
        <Icon name="rotate-ccw" :size="14" />{{ t('hgap.refresh') }}
      </button>
    </header>

    <div v-if="loading && !data" class="space-y-3">
      <div v-for="n in 2" :key="n" class="h-[220px] rounded-2xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
    </div>

    <div v-else-if="data && !data.kits.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-10 text-center text-[13px] text-stone-500">
      {{ t('kit.none') }}
    </div>

    <!-- one card per kit -->
    <section v-for="k in data?.kits || []" :key="k.kit" class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="p-4 flex items-start gap-3">
        <img v-if="k.image" :src="k.image" class="w-14 h-14 rounded-xl object-cover ring-1 ring-stone-200 flex-shrink-0" alt="" @error="hideImg" />
        <div class="min-w-0 flex-1">
          <div class="text-[15px] font-bold text-stone-900 font-mono">{{ k.sku }}</div>
          <div class="text-[12px] text-stone-500 truncate">{{ k.name }}</div>
          <div class="text-[11.5px] text-stone-500 mt-1">
            {{ t('kit.recipe') }}:
            <span v-for="(c, i) in k.components" :key="c.itemCode" class="font-mono text-stone-700">
              {{ i ? ' + ' : '' }}{{ c.perBatch }} × {{ c.sku }}
            </span>
            → <b class="text-stone-900">{{ k.yield }} × {{ k.sku }}</b>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-3 border-y border-stone-100 text-center">
        <div class="py-3">
          <div class="text-[10.5px] font-semibold uppercase tracking-wide text-stone-400">{{ t('kit.onShelf') }}</div>
          <div class="text-[22px] font-extrabold tabular-nums text-stone-900">{{ fmt(k.onShelf) }}</div>
        </div>
        <div class="py-3 border-x border-stone-100">
          <div class="text-[10.5px] font-semibold uppercase tracking-wide text-stone-400">{{ t('kit.waiting') }}</div>
          <div class="text-[22px] font-extrabold tabular-nums" :class="k.waiting > k.onShelf ? 'text-rose-600' : 'text-stone-900'">{{ fmt(k.waiting) }}</div>
        </div>
        <div class="py-3">
          <div class="text-[10.5px] font-semibold uppercase tracking-wide text-stone-400">{{ t('kit.buildable') }}</div>
          <div class="text-[22px] font-extrabold tabular-nums text-emerald-700">{{ fmt(k.buildable) }}</div>
        </div>
      </div>

      <!-- assemble -->
      <div class="p-4 space-y-3">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-[12.5px] font-semibold text-stone-700 me-1">{{ t('kit.howMany') }}</span>
          <button class="w-10 h-10 rounded-xl ring-1 ring-stone-200 text-[18px] font-bold text-stone-600 hover:bg-stone-50"
                  @click="step(k, -1)">−</button>
          <input v-model.number="form[k.kit].qty" type="number" inputmode="numeric" :step="k.yield" min="0"
                 class="w-[96px] h-10 rounded-xl ring-1 ring-stone-200 text-center text-[16px] font-bold tabular-nums" />
          <button class="w-10 h-10 rounded-xl ring-1 ring-stone-200 text-[18px] font-bold text-stone-600 hover:bg-stone-50"
                  @click="step(k, 1)">+</button>
          <button v-for="n in quick(k)" :key="n"
                  class="h-10 px-3 rounded-xl ring-1 ring-stone-200 text-[12.5px] font-semibold text-stone-600 hover:bg-stone-50 tabular-nums"
                  @click="form[k.kit].qty = n">{{ n }}</button>
          <span class="text-[11.5px] text-stone-400">{{ t('kit.batchHint').replace('{n}', k.yield) }}</span>
        </div>
        <p v-if="form[k.kit].qty && form[k.kit].qty % k.yield" class="text-[12px] text-rose-600">
          {{ t('kit.notWhole').replace('{n}', k.yield) }}
        </p>

        <!-- where each component comes from -->
        <div class="rounded-xl ring-1 ring-stone-200/70 divide-y divide-stone-100">
          <div v-for="c in k.components" :key="c.itemCode" class="px-3 py-2.5 flex items-center gap-3 flex-wrap">
            <img v-if="c.image" :src="c.image" class="w-9 h-9 rounded-lg object-cover ring-1 ring-stone-200" alt="" @error="hideImg" />
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] font-bold font-mono text-stone-900">{{ c.sku }}</div>
              <div class="text-[11px] text-stone-500 truncate">{{ c.name }}</div>
            </div>
            <div class="text-[12px] tabular-nums" :class="short(k, c) ? 'text-rose-600 font-semibold' : 'text-stone-600'">
              {{ t('kit.takes') }} <b>{{ need(k, c) }}</b>
            </div>
            <select v-model="form[k.kit].sources[c.itemCode]"
                    class="h-9 rounded-lg ring-1 ring-stone-200 text-[12px] px-2 min-w-[190px] bg-white">
              <option v-for="s in c.sources" :key="s.warehouse" :value="s.warehouse">
                {{ shortWh(s.warehouse) }} · {{ s.free }} {{ t('kit.free') }}
              </option>
            </select>
          </div>
        </div>

        <div class="flex items-center gap-3 flex-wrap">
          <label class="text-[12.5px] font-semibold text-stone-700">{{ t('kit.putOn') }}</label>
          <select v-model="form[k.kit].target" class="h-9 rounded-lg ring-1 ring-stone-200 text-[12px] px-2 min-w-[180px] bg-white">
            <option v-for="w in data.targets" :key="w" :value="w">{{ shortWh(w) }}</option>
          </select>
          <label class="inline-flex items-center gap-1.5 text-[12.5px] text-stone-600 ms-auto">
            <input v-model="form[k.kit].labels" type="checkbox" class="rounded" />{{ t('kit.printLabels') }}
          </label>
        </div>

        <button class="w-full h-12 rounded-xl text-[14px] font-bold text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40"
                :disabled="!canAssemble(k) || busy" @click="assemble(k)">
          {{ t('kit.assemble').replace('{n}', form[k.kit].qty || 0).replace('{sku}', k.sku) }}
        </button>
      </div>
    </section>

    <!-- history -->
    <section v-if="data?.recent?.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 text-[12.5px] font-semibold text-stone-900">{{ t('kit.history') }}</div>
      <div class="divide-y divide-stone-100">
        <div v-for="r in data.recent" :key="r.entry" class="px-4 py-2 flex items-center gap-3 text-[12px]" :class="r.cancelled ? 'opacity-50 line-through' : ''">
          <span class="font-mono text-stone-500">{{ r.entry }}</span>
          <span class="font-bold tabular-nums text-stone-900">{{ r.qty }} × {{ r.sku }}</span>
          <span class="text-stone-500 tabular-nums">{{ r.rate }} MAD/u</span>
          <span class="text-stone-400 truncate flex-1">{{ r.note }}</span>
          <span class="text-stone-400 tabular-nums">{{ r.at }} · {{ r.by }}</span>
        </div>
      </div>
    </section>

    <!-- recipes (manager) -->
    <section v-if="data?.isManager" class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
      <button class="w-full px-4 py-3 flex items-center gap-2 text-[12.5px] font-semibold text-stone-900" @click="editOpen = !editOpen">
        <Icon name="settings" :size="14" class="text-stone-400" />{{ t('kit.recipes') }}
        <Icon :name="editOpen ? 'chevron-up' : 'chevron-down'" :size="14" class="ms-auto text-stone-400" />
      </button>
      <div v-if="editOpen" class="px-4 pb-4 space-y-3 border-t border-stone-100 pt-3">
        <p class="text-[11.5px] text-stone-500">{{ t('kit.recipesHint') }}</p>
        <div v-for="(r, ri) in draft" :key="ri" class="rounded-xl ring-1 ring-stone-200/70 p-3 space-y-2">
          <div class="flex items-center gap-2 flex-wrap">
            <input v-model.trim="r.kit" :placeholder="t('kit.kitSku')" class="h-9 rounded-lg ring-1 ring-stone-200 px-2 text-[12.5px] font-mono w-[200px]" />
            <span class="text-[12px] text-stone-500">{{ t('kit.yieldLbl') }}</span>
            <input v-model.number="r.yield" type="number" min="1" class="h-9 w-[70px] rounded-lg ring-1 ring-stone-200 px-2 text-[12.5px] text-center" />
            <select v-model="r.target" class="h-9 rounded-lg ring-1 ring-stone-200 text-[12px] px-2 bg-white">
              <option v-for="w in data.targets" :key="w" :value="w">{{ shortWh(w) }}</option>
            </select>
            <button class="ms-auto text-[12px] text-rose-600 font-semibold" @click="draft.splice(ri, 1)">{{ t('kit.remove') }}</button>
          </div>
          <div v-for="(c, ci) in r.components" :key="ci" class="flex items-center gap-2">
            <input v-model.trim="c.item_code" :placeholder="t('kit.componentSku')" class="h-9 rounded-lg ring-1 ring-stone-200 px-2 text-[12.5px] font-mono flex-1" />
            <span class="text-[12px] text-stone-500">×</span>
            <input v-model.number="c.qty" type="number" min="1" class="h-9 w-[70px] rounded-lg ring-1 ring-stone-200 px-2 text-[12.5px] text-center" />
            <button class="text-stone-400 hover:text-rose-600" @click="r.components.splice(ci, 1)"><Icon name="x" :size="14" /></button>
          </div>
          <button class="text-[12px] font-semibold text-stone-600" @click="r.components.push({ item_code: '', qty: 1 })">+ {{ t('kit.addComponent') }}</button>
        </div>
        <div class="flex items-center gap-2">
          <button class="h-9 px-3 rounded-lg ring-1 ring-stone-200 text-[12.5px] font-semibold text-stone-700"
                  @click="draft.push({ kit: '', yield: 1, target: 'PLT - JM', components: [{ item_code: '', qty: 1 }] })">+ {{ t('kit.addKit') }}</button>
          <button class="ms-auto h-9 px-4 rounded-lg text-[12.5px] font-bold text-white bg-stone-900 disabled:opacity-40"
                  :disabled="busy" @click="saveRecipes">{{ t('kit.save') }}</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const data = ref(null);
const loading = ref(true);
const busy = ref(false);
const form = reactive({});
const editOpen = ref(false);
const draft = ref([]);

const fmt = (n) => Number(n || 0).toLocaleString("fr-FR");
const shortWh = (w) => (w || "").replace(/ - JM$/, "");
function hideImg(e) { if (e && e.target) e.target.style.display = "none"; }

const batches = (k) => Math.floor((Number(form[k.kit]?.qty) || 0) / k.yield);
const need = (k, c) => batches(k) * c.perBatch;
function freeAt(c, wh) { return (c.sources.find((s) => s.warehouse === wh) || {}).free || 0; }
const short = (k, c) => need(k, c) > freeAt(c, form[k.kit]?.sources?.[c.itemCode]);

function canAssemble(k) {
  const q = Number(form[k.kit]?.qty) || 0;
  return q > 0 && q % k.yield === 0 && form[k.kit].target
    && k.components.every((c) => form[k.kit].sources[c.itemCode] && !short(k, c));
}
function step(k, dir) {
  const q = Number(form[k.kit].qty) || 0;
  form[k.kit].qty = Math.max(0, (Math.round(q / k.yield) + dir) * k.yield);
}
// Quick picks: whole batches, the biggest ones bounded by what can be built.
function quick(k) {
  return [10, 33, 100].map((b) => b * k.yield).filter((n) => n <= k.buildable);
}

function initForms() {
  for (const k of data.value.kits) {
    const prev = form[k.kit];
    const sources = {};
    for (const c of k.components) {
      const keep = prev?.sources?.[c.itemCode];
      sources[c.itemCode] = (keep && c.sources.some((s) => s.warehouse === keep)) ? keep
        : (c.sources.find((s) => s.free > 0) || c.sources[0] || {}).warehouse || "";
    }
    form[k.kit] = { qty: prev?.qty || 0, target: prev?.target || k.target || "PLT - JM",
                    labels: prev ? prev.labels : true, sources };
  }
  draft.value = data.value.kits.map((k) => ({
    kit: k.kit, yield: k.yield, target: k.target,
    components: k.components.map((c) => ({ item_code: c.itemCode, qty: c.perBatch })),
  }));
}

async function load() {
  loading.value = true;
  try {
    data.value = await api("kits.boot");
    initForms();
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

async function assemble(k) {
  const f = form[k.kit];
  const parts = k.components.map((c) => `${need(k, c)} × ${c.sku} (${shortWh(f.sources[c.itemCode])})`).join(" + ");
  if (!window.confirm(t("kit.confirm").replace("{n}", f.qty).replace("{sku}", k.sku).replace("{parts}", parts))) return;
  busy.value = true;
  try {
    const r = await apiPost("kits.assemble", {
      kit: k.kit, qty: f.qty, target: f.target, sources: JSON.stringify(f.sources), print_labels: f.labels ? 1 : 0,
    });
    success(t("kit.done").replace("{n}", r.qty).replace("{sku}", k.sku),
            `${r.entry} · ${r.rate} MAD/u` + (r.labels ? ` · ${r.labels} ${t("kit.labels")}` : ""));
    f.qty = 0;
    await load();
  } catch (e) {
    warn(t("cfs.saveFail"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

async function saveRecipes() {
  busy.value = true;
  try {
    await apiPost("kits.save_recipes", { recipes_json: JSON.stringify(draft.value) });
    success(t("kit.saved"));
    editOpen.value = false;
    await load();
  } catch (e) {
    warn(t("cfs.saveFail"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

onMounted(load);
</script>
