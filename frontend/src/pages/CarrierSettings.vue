<template>
  <!-- Transporteurs: which carrier each parcel goes to. The label stays
       automatic (pick-list submit); these settings only choose the carrier.
       Backend: logistics_portal.api.carriers / api.sendit. -->
  <div class="p-5 sm:p-6 space-y-5 max-w-[980px] mx-auto">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div class="min-w-0">
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('crs.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[680px]">{{ t('crs.intro') }}</p>
      </div>
      <button class="h-10 px-5 rounded-xl text-[13px] font-bold text-white bg-stone-900 hover:bg-stone-800 disabled:opacity-50"
              :disabled="saving || !cfg" @click="save">{{ saving ? t('crs.saving') : t('crs.save') }}</button>
    </header>

    <div v-if="!cfg" class="h-[300px] rounded-2xl bg-stone-100 animate-pulse" />

    <template v-else>
      <!-- Kill switch -->
      <section class="rounded-2xl p-4 flex items-center gap-3 flex-wrap ring-1"
               :class="cfg.settings.kill ? 'bg-rose-50 ring-rose-200' : 'bg-white ring-stone-200/70'">
        <Icon name="shield-alert" :size="18" :class="cfg.settings.kill ? 'text-rose-600' : 'text-stone-400'" />
        <div class="min-w-0 flex-1">
          <div class="text-[13px] font-semibold text-stone-900">{{ t('crs.kill') }}</div>
          <div class="text-[11.5px] text-stone-500">{{ t('crs.killHint') }}</div>
        </div>
        <label class="inline-flex items-center gap-2 text-[12.5px] font-semibold select-none">
          <input v-model="cfg.settings.kill" type="checkbox" class="w-5 h-5 accent-rose-600" />
          {{ cfg.settings.kill ? t('crs.killOn') : t('crs.killOff') }}
        </label>
      </section>

      <!-- Sendit connection -->
      <section class="rounded-2xl p-4 bg-white ring-1 ring-stone-200/70 space-y-3.5">
        <div class="flex items-center gap-2 flex-wrap">
          <Icon name="truck" :size="16" class="text-stone-400" />
          <span class="text-[14px] font-bold text-stone-900">Sendit</span>
          <span class="text-[10.5px] font-bold rounded-full px-2 py-0.5"
                :class="cfg.keysSet ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200' : 'bg-amber-50 text-amber-700 ring-1 ring-amber-200'">
            {{ cfg.keysSet ? t('crs.keysSet') + (cfg.publicKeyHint ? ' · ' + cfg.publicKeyHint : '') : t('crs.keysMissing') }}
          </span>
          <span class="text-[11px] text-stone-400 tabular-nums">{{ cfg.districts }} {{ t('crs.districts') }}</span>
          <button class="ms-auto h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 ring-stone-200 hover:bg-stone-50 disabled:opacity-50"
                  :disabled="testing || !cfg.keysSet" @click="testConn">{{ testing ? t('crs.testing') : t('crs.test') }}</button>
        </div>
        <div v-if="conn" class="text-[12px] rounded-lg px-3 py-2"
             :class="conn.ok ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-800'">
          {{ conn.ok ? t('crs.connOk').replace('{n}', String(conn.districts)) : conn.error }}
        </div>

        <div class="grid sm:grid-cols-2 gap-2.5">
          <input v-model="keys.pub" type="password" autocomplete="off" :placeholder="t('crs.publicKey')"
                 class="h-10 px-3 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12.5px]" dir="ltr" />
          <input v-model="keys.sec" type="password" autocomplete="off" :placeholder="t('crs.secretKey')"
                 class="h-10 px-3 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12.5px]" dir="ltr" />
        </div>
        <button class="h-8 px-3 rounded-lg text-[12px] font-semibold text-white bg-sky-600 hover:bg-sky-700 disabled:opacity-50"
                :disabled="!keys.pub && !keys.sec" @click="saveKeys">{{ t('crs.saveKeys') }}</button>

        <div class="grid sm:grid-cols-2 gap-2.5 pt-1">
          <label class="text-[11.5px] text-stone-500 space-y-1">
            <span>{{ t('crs.pickupCity') }}</span>
            <select v-model.number="cfg.settings.sendit.pickup_district_id" class="w-full h-10 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12.5px] text-stone-900">
              <option :value="null">—</option>
              <option v-for="c in pickupCities" :key="c.id" :value="c.id">{{ c.name }}</option>
              <option v-if="cfg.settings.sendit.pickup_district_id && !pickupCities.some((c) => c.id === cfg.settings.sendit.pickup_district_id)"
                      :value="cfg.settings.sendit.pickup_district_id">#{{ cfg.settings.sendit.pickup_district_id }}</option>
            </select>
          </label>
          <label class="text-[11.5px] text-stone-500 space-y-1">
            <span>{{ t('crs.labelFormat') }}</span>
            <select v-model.number="cfg.settings.sendit.label_format" class="w-full h-10 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12.5px] text-stone-900">
              <option :value="1">{{ t('crs.thermal') }}</option>
              <option :value="0">A4</option>
            </select>
          </label>
          <input v-model="cfg.settings.sendit.pickup_name" :placeholder="t('crs.pickupName')" class="h-10 px-3 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12.5px]" />
          <input v-model="cfg.settings.sendit.pickup_phone" :placeholder="t('crs.pickupPhone')" class="h-10 px-3 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12.5px]" dir="ltr" />
          <input v-model="cfg.settings.sendit.pickup_address" :placeholder="t('crs.pickupAddress')" class="sm:col-span-2 h-10 px-3 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12.5px]" />
        </div>
        <div class="flex items-center gap-5 flex-wrap text-[12.5px] text-stone-700">
          <label class="inline-flex items-center gap-2"><input v-model="openFlag" type="checkbox" class="w-4 h-4" /> {{ t('crs.allowOpen') }}</label>
          <label class="inline-flex items-center gap-2"><input v-model="tryFlag" type="checkbox" class="w-4 h-4" /> {{ t('crs.allowTry') }}</label>
        </div>
        <div class="text-[11.5px] text-stone-500">
          {{ t('crs.webhook') }}
          <div class="mt-1 flex items-center gap-2">
            <code class="font-mono text-[11px] bg-stone-50 ring-1 ring-stone-200 rounded px-2 py-1 truncate" dir="ltr">{{ cfg.webhookUrl }}</code>
            <button class="h-7 px-2 rounded-lg text-[11px] font-semibold ring-1 ring-stone-200 hover:bg-stone-50" @click="copy(cfg.webhookUrl)">{{ t('crs.copy') }}</button>
          </div>
        </div>
      </section>

      <!-- Mode -->
      <section class="rounded-2xl p-4 bg-white ring-1 ring-stone-200/70 space-y-3">
        <div class="text-[13px] font-semibold text-stone-900">{{ t('crs.mode') }}</div>
        <div class="grid sm:grid-cols-3 gap-2">
          <button v-for="m in ['off', 'test', 'on']" :key="m"
                  class="text-start rounded-xl p-3 ring-1 transition-colors"
                  :class="cfg.settings.sendit.mode === m ? 'ring-2 ring-sky-500 bg-sky-50/50' : 'ring-stone-200 hover:ring-stone-300'"
                  @click="cfg.settings.sendit.mode = m">
            <div class="text-[13px] font-bold text-stone-900">{{ t('crs.mode_' + m) }}</div>
            <div class="text-[11.5px] text-stone-500 mt-0.5">{{ t('crs.modeHint_' + m) }}</div>
          </button>
        </div>

        <div v-if="cfg.settings.sendit.mode !== 'off'" class="space-y-1.5">
          <div class="text-[12px] font-semibold text-stone-700">{{ t('crs.testOrders') }}</div>
          <textarea v-model="testOrdersText" rows="2" :placeholder="t('crs.testOrdersPh')"
                    class="w-full px-3 py-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12.5px] font-mono" dir="ltr" />
          <div class="text-[11px] text-stone-400">{{ t('crs.testOrdersHint') }}</div>
        </div>

        <div v-if="cfg.settings.sendit.mode === 'on'" class="space-y-2">
          <div class="text-[12px] font-semibold text-stone-700">{{ t('crs.rules') }}</div>
          <div class="text-[11px] text-stone-400">{{ t('crs.rulesHint') }}</div>
          <div v-for="(r, i) in cfg.settings.rules" :key="i" class="flex items-center gap-2 flex-wrap rounded-xl bg-stone-50 ring-1 ring-stone-200 p-2.5">
            <span class="text-[11px] font-bold text-stone-400 w-5">{{ i + 1 }}</span>
            <input v-model="r.citiesText" :placeholder="t('crs.ruleCities')" class="flex-1 min-w-[180px] h-9 px-2.5 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px]" />
            <select v-model="r.carrier" class="h-9 px-2 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px]">
              <option value="Sendit">Sendit</option>
              <option value="Cathedis">Cathedis</option>
            </select>
            <label v-if="r.carrier === 'Sendit'" class="text-[11.5px] text-stone-500">%
              <input v-model.number="r.share" type="number" min="0" max="100" class="ms-1 w-16 h-9 px-2 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] tabular-nums" />
            </label>
            <label v-if="r.carrier === 'Sendit'" class="text-[11.5px] text-stone-500">{{ t('crs.maxDay') }}
              <input v-model.number="r.max_per_day" type="number" min="0" class="ms-1 w-16 h-9 px-2 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] tabular-nums" />
            </label>
            <button class="w-8 h-8 rounded-lg text-stone-400 hover:text-rose-600 hover:bg-white" @click="cfg.settings.rules.splice(i, 1)"><Icon name="x" :size="14" /></button>
          </div>
          <button class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 ring-stone-200 hover:bg-stone-50"
                  @click="cfg.settings.rules.push({ citiesText: '', carrier: 'Sendit', share: 30, max_per_day: 0 })">+ {{ t('crs.addRule') }}</button>
        </div>
      </section>

      <!-- Preview -->
      <section class="rounded-2xl p-4 bg-white ring-1 ring-stone-200/70 space-y-2">
        <div class="text-[13px] font-semibold text-stone-900">{{ t('crs.preview') }}</div>
        <div class="text-[11.5px] text-stone-500">{{ t('crs.previewHint') }}</div>
        <div class="flex gap-2">
          <input v-model="pv.order" :placeholder="t('crs.orderPh')" class="flex-1 h-10 px-3 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12.5px] font-mono" dir="ltr" @keyup.enter="preview" />
          <button class="h-10 px-4 rounded-lg text-[12.5px] font-semibold ring-1 ring-stone-200 hover:bg-stone-50" @click="preview">{{ t('crs.check') }}</button>
        </div>
        <div v-if="pv.res" class="text-[12.5px] rounded-lg px-3 py-2.5 bg-stone-50 ring-1 ring-stone-200 space-y-2">
          <div>
            <b class="font-mono">{{ pv.res.order }}</b> · {{ pv.res.city || '—' }} →
            <b :class="pv.res.carrier === 'Sendit' ? 'text-sky-700' : 'text-stone-900'">{{ pv.res.carrier }}</b>
            <span class="text-stone-500"> — {{ pv.res.why }}</span>
          </div>
          <div v-if="pv.res.awb" class="text-[11.5px] text-stone-500">
            {{ t('crs.alreadyLabelled') }} <b>{{ pv.res.current || '—' }}</b>
            <span class="font-mono">{{ pv.res.awb }}</span> · {{ pv.res.status }}
          </div>
          <div class="flex flex-wrap gap-2">
            <button v-if="pv.res.canTest && !pv.res.isTest" class="h-8 px-3 rounded-lg text-[12px] font-semibold text-white bg-sky-600 hover:bg-sky-700 disabled:opacity-50"
                    :disabled="pv.busy" @click="addTest">{{ t('crs.addTest') }}</button>
            <span v-if="pv.res.isTest" class="text-[11.5px] font-semibold text-sky-700">{{ t('crs.isTest') }}</span>
            <button v-if="pv.res.canRelabel" class="h-8 px-3 rounded-lg text-[12px] font-semibold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50"
                    :disabled="pv.busy" @click="relabel">{{ pv.busy ? t('crs.working') : t('crs.relabel') }}</button>
          </div>
          <div v-if="pv.res.canTest && !pv.res.isTest && cfg.settings.sendit.mode === 'off'" class="text-[11px] text-amber-700">{{ t('crs.modeOffHint') }}</div>
          <div v-for="b in (pv.res.blockers || [])" :key="b.code" class="text-[11.5px] text-amber-800 bg-amber-50 rounded-lg px-2.5 py-1.5">
            {{ t('crs.block_' + b.code).replace('{ref}', b.ref || '') }}
          </div>
          <div v-if="pv.msg" class="text-[12px] rounded-lg px-2.5 py-1.5" :class="pv.ok ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-800'">{{ pv.msg }}</div>
        </div>
      </section>

      <!-- Cities -->
      <section class="rounded-2xl bg-white ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-3 flex items-center gap-2 border-b border-stone-100">
          <span class="text-[13px] font-semibold text-stone-900">{{ t('crs.cities') }}</span>
          <span class="text-[11px] text-stone-400">{{ t('crs.citiesHint') }}</span>
          <button class="ms-auto h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 ring-stone-200 hover:bg-stone-50" @click="loadCities">{{ t('crs.load') }}</button>
        </div>
        <div v-if="cities" class="divide-y divide-stone-50 max-h-[360px] overflow-y-auto">
          <div v-for="c in cities.rows" :key="c.city" class="px-4 py-2 flex items-center gap-3 text-[12.5px]">
            <span class="font-semibold text-stone-900 w-[150px] truncate">{{ c.city || '—' }}</span>
            <span class="tabular-nums text-stone-400 w-14">{{ c.orders }}</span>
            <!-- One open list at a time: hundreds of districts on every row
                 is tens of thousands of nodes and a frozen page. -->
            <select v-if="editing === c.city" :value="override(c.city) || c.districtId || ''"
                    class="flex-1 min-w-0 h-8 px-2 rounded-lg ring-1 ring-sky-300 bg-white text-[12px]"
                    @change="setOverride(c.city, $event.target.value); editing = ''">
              <option value="">{{ t('crs.notServed') }}</option>
              <option v-for="d in cities.districts" :key="d.id" :value="d.id">{{ d.label }}{{ d.delay ? ' · ' + d.delay : '' }}</option>
            </select>
            <button v-else class="flex-1 min-w-0 h-8 px-2 rounded-lg ring-1 text-[12px] text-start truncate"
                    :class="c.districtId || override(c.city) ? 'bg-white ring-stone-200 text-stone-700' : 'bg-rose-50 ring-rose-200 text-rose-700'"
                    @click="editing = c.city">
              {{ labelOf(override(c.city)) || c.district || t('crs.notServed') }}
            </button>
          </div>
        </div>
      </section>

      <!-- Sendit parcels -->
      <section class="rounded-2xl bg-white ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-3 flex items-center gap-2 flex-wrap border-b border-stone-100">
          <span class="text-[13px] font-semibold text-stone-900">{{ t('crs.parcels') }}</span>
          <span class="text-[11px] text-stone-400 tabular-nums">{{ parcels.length }}</span>
          <button class="ms-auto h-8 px-3 rounded-lg text-[12px] font-semibold text-white bg-sky-600 hover:bg-sky-700 disabled:opacity-50"
                  :disabled="busy || !waiting" @click="pickup">{{ t('crs.pickup') }} · {{ waiting }}</button>
          <button class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 ring-stone-200 hover:bg-stone-50" @click="loadParcels">{{ t('crs.load') }}</button>
        </div>
        <p v-if="!parcels.length" class="px-4 py-6 text-center text-[12.5px] text-stone-400">{{ t('crs.noParcels') }}</p>
        <div v-else class="divide-y divide-stone-50 max-h-[360px] overflow-y-auto">
          <div v-for="p in parcels" :key="p.order" class="px-4 py-2 flex items-center gap-2.5 flex-wrap text-[12px]">
            <span class="font-mono font-semibold text-stone-900">{{ p.order }}</span>
            <span class="font-mono text-stone-500">{{ p.code }}</span>
            <span class="text-stone-500 truncate max-w-[160px]" dir="auto">{{ p.customer }}</span>
            <span class="text-[10.5px] font-semibold rounded px-1.5 py-0.5 bg-stone-100 text-stone-600">{{ p.status }}</span>
            <span class="text-[10.5px] font-semibold rounded px-1.5 py-0.5 bg-sky-50 text-sky-700">{{ p.track }}</span>
            <span v-if="!p.label" class="text-[10.5px] font-bold text-rose-600">{{ t('crs.noLabel') }}</span>
            <span class="ms-auto flex items-center gap-1">
              <button class="h-7 px-2 rounded-lg ring-1 ring-stone-200 hover:bg-stone-50" @click="act(p, 'refresh')">{{ t('crs.refresh') }}</button>
              <button class="h-7 px-2 rounded-lg ring-1 ring-stone-200 hover:bg-stone-50" @click="act(p, 'label')">{{ t('crs.label') }}</button>
              <button class="h-7 px-2 rounded-lg ring-1 ring-rose-200 text-rose-700 hover:bg-rose-50" @click="act(p, 'cancel')">{{ t('crs.cancel') }}</button>
            </span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const cfg = ref(null);
const saving = ref(false);
const testing = ref(false);
const conn = ref(null);
const pickupCities = ref([]);
const keys = reactive({ pub: "", sec: "" });
const testOrdersText = ref("");
const pv = reactive({ order: "", res: null, busy: false, msg: "", ok: true });
const cities = ref(null);
const editing = ref("");
const labelOf = (id) => (id ? ((cities.value?.districts || []).find((d) => d.id === Number(id)) || {}).label || "" : "");
const parcels = ref([]);
const busy = ref(false);

const openFlag = computed({
  get: () => !!cfg.value?.settings.sendit.allow_open,
  set: (v) => { cfg.value.settings.sendit.allow_open = v ? 1 : 0; },
});
const tryFlag = computed({
  get: () => !!cfg.value?.settings.sendit.allow_try,
  set: (v) => { cfg.value.settings.sendit.allow_try = v ? 1 : 0; },
});
const waiting = computed(() => parcels.value.filter((p) => ["Label Generated", "Label Printed"].includes(p.status)).length);

async function load() {
  const r = await api("carriers.get_config");
  r.settings.rules = (r.settings.rules || []).map((x) => ({ ...x, citiesText: (x.cities || []).join(", ") }));
  testOrdersText.value = (r.settings.test_orders || []).join("\n");
  cfg.value = r;
}

async function save() {
  saving.value = true;
  try {
    const s = cfg.value.settings;
    const payload = {
      ...s,
      rules: s.rules.map((r) => ({ ...r, cities: String(r.citiesText || "").split(/[,\n]/).map((x) => x.trim()).filter(Boolean) })),
      test_orders: testOrdersText.value.split(/[\s,]+/).map((x) => x.trim()).filter(Boolean),
    };
    await apiPost("carriers.save_config", { config: JSON.stringify(payload) });
    success(t("crs.saved"), "");
    await load();
  } catch (e) {
    warn(t("crs.save"), String(e.message || e));
  } finally { saving.value = false; }
}

async function saveKeys() {
  try {
    await apiPost("carriers.set_sendit_keys", { public_key: keys.pub, secret_key: keys.sec });
    keys.pub = ""; keys.sec = "";
    success(t("crs.keysSaved"), "");
    await load();
  } catch (e) { warn(t("crs.saveKeys"), String(e.message || e)); }
}

async function testConn() {
  testing.value = true;
  try {
    conn.value = await apiPost("carriers.test_connection");
    if (conn.value.ok) {
      pickupCities.value = conn.value.pickupCities || [];
      cfg.value.districts = conn.value.districts;
    }
  } catch (e) { conn.value = { ok: false, error: String(e.message || e) }; }
  finally { testing.value = false; }
}

async function preview(keepMsg) {
  if (!pv.order.trim()) return;
  if (!keepMsg) pv.msg = "";
  try { pv.res = await api("carriers.preview", { order: pv.order.trim() }); }
  catch (e) { pv.res = null; warn(t("crs.preview"), String(e.message || e)); }
}
async function addTest() {
  pv.busy = true;
  try {
    const r = await apiPost("carriers.add_test_order", { order: pv.res.order });
    testOrdersText.value = (r.tests || []).join("\n");
    cfg.value.settings.test_orders = r.tests || [];
    pv.ok = true; pv.msg = t("crs.testAdded").replace("{o}", r.order);
    await preview(true);
  } catch (e) { pv.ok = false; pv.msg = String(e.message || e); }
  finally { pv.busy = false; }
}
async function relabel() {
  if (!window.confirm(t("crs.relabelConfirm").replace("{o}", pv.res.order).replace("{awb}", pv.res.awb))) return;
  pv.busy = true;
  try {
    const r = await apiPost("carriers.relabel_sendit", { order: pv.res.order });
    pv.ok = !!r.ok;
    pv.msg = r.ok ? t("crs.relabelled").replace("{code}", r.code || "").replace("{d}", r.district || "")
                    .replace("{amt}", String(r.amount)).replace("{awb}", r.oldAwb || "")
                  : (r.error || "");
    await preview(true);
    loadParcels();
  } catch (e) { pv.ok = false; pv.msg = String(e.message || e); }
  finally { pv.busy = false; }
}

// Same key as sendit._norm: accents dropped, letters and digits only.
function norm(s) { return String(s || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/[^A-Z0-9]/g, ""); }
function override(city) { return (cfg.value?.settings.city_map || {})[norm(city)] || ""; }
function setOverride(city, id) {
  const m = { ...(cfg.value.settings.city_map || {}) };
  if (id) m[norm(city)] = Number(id); else delete m[norm(city)];
  cfg.value.settings.city_map = m;
}
async function loadCities() {
  try { cities.value = await api("carriers.city_coverage", { days: 30 }); }
  catch (e) { warn(t("crs.cities"), String(e.message || e)); }
}

async function loadParcels() {
  try { parcels.value = (await api("carriers.sendit_parcels")).rows || []; } catch { parcels.value = []; }
}
async function act(p, action) {
  if (action === "cancel" && !window.confirm(t("crs.cancelConfirm").replace("{o}", p.order))) return;
  try {
    const r = await apiPost("carriers.sendit_action", { order: p.order, action });
    if (r.ok) success(t("crs.done"), p.order); else warn(p.order, r.error || "");
    await loadParcels();
  } catch (e) { warn(p.order, String(e.message || e)); }
}
async function pickup() {
  if (!window.confirm(t("crs.pickupConfirm").replace("{n}", String(waiting.value)))) return;
  busy.value = true;
  try {
    const r = await apiPost("carriers.sendit_pickup");
    if (r.ok) success(t("crs.pickupDone").replace("{n}", String(r.parcels)), r.pickup || "");
    else warn(t("crs.pickup"), r.error || "");
    await loadParcels();
  } catch (e) { warn(t("crs.pickup"), String(e.message || e)); }
  finally { busy.value = false; }
}

async function copy(text) {
  try { await navigator.clipboard.writeText(text); success(t("crs.copied"), ""); } catch {}
}

onMounted(async () => { await load(); loadParcels(); });
</script>
