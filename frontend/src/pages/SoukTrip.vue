<template>
  <!-- The custody (العهدة). The accountant hands the buyer the cash and opens
       the trip; every purchase is deducted; the buyer closes the day and the
       accountant counts what came back. A purchase without a receipt carries a
       substitute (photo of the goods + the stall's phone) the accountant
       approves before counting. Backend: souk.trips_boot / open_trip /
       set_transport / set_voucher / approve_voucher / close_trip / count_trip. -->
  <div class="max-w-[720px] mx-auto px-4 py-4 space-y-4">
    <header class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-[18px] font-bold text-stone-900">{{ t('souk.custodyTitle') }}</h1>
        <p class="text-[12px] text-stone-500 mt-0.5">{{ t('souk.custodyIntro') }}</p>
      </div>
      <div class="flex gap-2 shrink-0">
        <router-link v-if="data?.canBuy" :to="{ name: 'SoukBuy' }" class="h-9 px-3 rounded-lg bg-[#c4301c] text-white text-[12.5px] font-bold inline-flex items-center">+ {{ t('souk.product') }}</router-link>
        <router-link :to="{ name: 'SoukBoard' }" class="h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center">{{ t('souk.board') }}</router-link>
      </div>
    </header>

    <div v-if="loading && !data" class="h-[260px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <!-- accountant: hand out a custody -->
    <section v-if="data?.isAccountant" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
      <h2 class="text-[13.5px] font-bold">{{ t('souk.handOut') }}</h2>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <select v-model="give.buyer" class="h-11 rounded-lg ring-1 ring-stone-300 px-2 text-[13.5px] bg-white">
          <option value="">{{ t('souk.buyer') }}</option>
          <option v-for="b in data.buyers" :key="b.user" :value="b.user">{{ b.name }}</option>
        </select>
        <input v-model.number="give.cash" type="number" inputmode="decimal" :placeholder="t('souk.amount')" class="h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[15px] tabular-nums" />
        <input v-model="give.place" placeholder="Derb Omar" class="h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[13.5px]" />
      </div>
      <button class="h-11 px-5 rounded-xl bg-stone-900 text-white text-[13px] font-bold disabled:opacity-40"
              :disabled="busy || !give.buyer || !(give.cash > 0)" @click="openTrip">
        {{ t('souk.handOutBtn').replace('{n}', fmt(give.cash || 0)) }}
      </button>
    </section>

    <div v-if="data && !data.open.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-8 text-center text-[13px] text-stone-500">
      {{ data.isAccountant ? t('souk.noOpenTrips') : t('souk.noTrip') }}
    </div>

    <!-- one card per open / closed trip -->
    <section v-for="tr in data?.open || []" :key="tr.name" class="bg-white ring-1 ring-stone-200/70 rounded-2xl overflow-hidden">
      <div class="px-4 pt-3 pb-2 flex items-center justify-between gap-2">
        <div class="min-w-0">
          <div class="text-[11.5px] font-semibold text-stone-500">{{ t('souk.tripNo').replace('{n}', tr.name) }} · {{ tr.buyerName }}</div>
          <div class="text-[14.5px] font-bold">{{ tr.place }} · {{ tr.opened }}</div>
        </div>
        <span class="text-[11px] font-bold rounded-md px-2 py-0.5"
              :class="tr.status === 'Open' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800'">
          {{ tr.status === 'Open' ? t('souk.stOpen') : t('souk.stClosed') }}
        </span>
      </div>

      <div class="mx-4 rounded-xl bg-stone-900 text-white p-4 space-y-3">
        <div>
          <div class="text-[11.5px] text-stone-300">{{ tr.status === 'Open' ? t('souk.shouldHave') : t('souk.toHandBack') }}</div>
          <div class="text-[28px] font-extrabold tabular-nums">{{ fmt(tr.status === 'Open' ? tr.expected : tr.expectedBack) }} <small class="text-[13px] text-stone-300">MAD</small></div>
        </div>
        <div class="grid grid-cols-3 gap-2 text-[11px] text-stone-300 tabular-nums">
          <div>{{ t('souk.fromAccountant') }}<div class="text-[14px] font-bold text-white">{{ fmt(tr.cashGiven) }}</div></div>
          <div>{{ t('souk.goods') }}<div class="text-[14px] font-bold text-white">{{ fmt(tr.goods) }}</div></div>
          <div>{{ t('souk.transport') }}<div class="text-[14px] font-bold text-white">{{ fmt(tr.transport) }}</div></div>
        </div>
      </div>

      <!-- purchases -->
      <div class="px-4 pt-3 text-[12.5px] font-bold">{{ t('souk.purchases') }} · {{ tr.buys.length }}</div>
      <div class="divide-y divide-stone-100">
        <div v-for="b in tr.buys" :key="b.po" class="px-4 py-2.5 flex items-center gap-3">
          <img v-if="b.image" :src="b.image" class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200" alt="" />
          <div v-else class="w-10 h-10 rounded-lg bg-stone-100" />
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-semibold truncate">{{ b.title || b.po }}</div>
            <div class="text-[11px] text-stone-500 truncate">{{ b.supplier }} · {{ b.units }} {{ t('souk.pcs') }} · <span class="font-mono">{{ b.po }}</span></div>
            <div class="text-[11px] mt-0.5">
              <span v-if="b.received" class="text-emerald-700 font-semibold">{{ t('souk.receivedAs').replace('{pr}', b.received) }}</span>
              <router-link v-else-if="data.canReceive" :to="{ name: 'SoukReceive', params: { po: b.po } }" class="font-bold text-emerald-700">{{ t('souk.receiveBtn') }}</router-link>
              <span v-else class="text-stone-400">{{ t('souk.notReceived') }}</span>
              <span v-if="b.owed" class="ms-2 font-semibold text-amber-800">{{ t('souk.owesShort').replace('{n}', fmt(b.owed)) }}<span v-if="b.debitNote" class="font-mono"> · {{ b.debitNote }}</span></span>
            </div>
          </div>
          <div class="flex flex-col items-end gap-1">
            <span class="text-[12.5px] font-bold tabular-nums">{{ fmt(b.amount) }}</span>
            <span class="text-[10.5px] font-bold rounded px-1.5" :class="rcls(b.receipt)">{{ t('souk.rc_' + b.receipt) }}</span>
          </div>
          <div v-if="tr.status === 'Open' && b.receipt === 'missing' && tr.buyer === data.me" class="flex flex-col gap-1">
            <label class="h-8 px-2 rounded-lg ring-1 ring-stone-300 text-[11.5px] font-semibold inline-flex items-center cursor-pointer">
              {{ t('souk.addReceipt') }}<input type="file" accept="image/*" capture="environment" class="hidden" @change="(e) => receipt(b, e)" />
            </label>
            <button class="h-8 px-2 rounded-lg ring-1 ring-amber-300 text-amber-800 text-[11.5px] font-semibold" @click="voucher(b)">{{ t('souk.noReceipt') }}</button>
          </div>
          <button v-if="data.isAccountant && b.receipt === 'voucher_pending'"
                  class="h-8 px-2 rounded-lg bg-emerald-600 text-white text-[11.5px] font-bold" @click="approve(b)">
            {{ t('souk.approve') }} · {{ b.phone }}
          </button>
        </div>
      </div>

      <!-- transport -->
      <div v-if="tr.status === 'Open'" class="px-4 py-3 border-t border-stone-100 flex items-end gap-2">
        <div class="flex-1">
          <label class="text-[11.5px] font-semibold text-stone-600">{{ t('souk.taxi') }}</label>
          <input v-model.number="transport[tr.name]" type="number" inputmode="decimal" class="w-full h-10 rounded-lg ring-1 ring-stone-300 px-3 text-[14px] tabular-nums" @change="saveTransport(tr)" />
        </div>
        <label class="h-10 px-3 rounded-lg ring-1 ring-stone-300 text-[12px] font-semibold inline-flex items-center gap-1 cursor-pointer">
          <Icon name="image" :size="14" />{{ tr.transportReceipt ? '✓' : t('souk.receipt') }}
          <input type="file" accept="image/*" capture="environment" class="hidden" @change="(e) => transportReceipt(tr, e)" />
        </label>
      </div>
      <p v-if="tr.status === 'Open'" class="px-4 pb-2 text-[11px] text-stone-500">{{ t('souk.taxiHint') }}</p>

      <!-- transport by weight (accountant), once everything is received -->
      <div v-if="data.isAccountant && tr.transport > 0" class="px-4 py-2 border-t border-stone-100 flex items-center gap-2 text-[12px]">
        <span v-if="tr.transportLcv" class="text-emerald-700 font-semibold">{{ t('souk.transportDone').replace('{v}', tr.transportLcv) }}</span>
        <template v-else>
          <span class="flex-1 text-stone-600">{{ tr.allReceived ? t('souk.transportReady') : t('souk.transportWait') }}</span>
          <button class="h-8 px-3 rounded-lg bg-stone-900 text-white text-[11.5px] font-bold disabled:opacity-40"
                  :disabled="busy || !tr.allReceived || !data.accounts?.custody" @click="allocate(tr)">{{ t('souk.transportBtn') }}</button>
        </template>
      </div>

      <!-- close (buyer) -->
      <div v-if="tr.status === 'Open' && tr.buyer === data.me" class="px-4 pb-4 pt-1 space-y-1">
        <p v-if="tr.missingReceipts" class="text-[11.5px] text-amber-800 text-center">{{ t('souk.missingN').replace('{n}', tr.missingReceipts) }}</p>
        <button class="w-full h-12 rounded-xl bg-stone-900 text-white text-[14px] font-bold disabled:bg-stone-200 disabled:text-stone-500"
                :disabled="busy || !tr.canClose" @click="close(tr)">
          {{ t('souk.closeBtn').replace('{n}', fmt(tr.expected)) }}
        </button>
      </div>

      <!-- count (accountant) -->
      <div v-if="tr.status === 'Closed' && data.isAccountant" class="px-4 pb-4 pt-3 border-t border-stone-100 space-y-2">
        <h3 class="text-[12.5px] font-bold">{{ t('souk.countTitle').replace('{n}', fmt(tr.expectedBack)) }}</h3>
        <p v-if="tr.pendingVouchers" class="text-[11.5px] text-amber-800">{{ t('souk.approveFirst').replace('{n}', tr.pendingVouchers) }}</p>
        <div class="flex gap-2">
          <input v-model.number="count[tr.name]" type="number" inputmode="decimal" :placeholder="t('souk.counted')" class="flex-1 h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[15px] tabular-nums" />
          <input v-model="countNote[tr.name]" :placeholder="t('souk.note')" class="flex-1 h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[13px]" />
        </div>
        <p v-if="count[tr.name] !== undefined && count[tr.name] !== '' && diff(tr) !== 0" class="text-[12px] font-semibold" :class="diff(tr) < 0 ? 'text-rose-600' : 'text-emerald-700'">
          {{ t('souk.diff').replace('{n}', (diff(tr) > 0 ? '+' : '') + fmt(diff(tr))) }}
        </p>
        <button class="h-11 px-5 rounded-xl bg-emerald-600 text-white text-[13px] font-bold disabled:opacity-40"
                :disabled="busy || tr.pendingVouchers || count[tr.name] === undefined || count[tr.name] === ''" @click="doCount(tr)">
          {{ t('souk.countBtn') }}
        </button>
      </div>
    </section>

    <!-- the accountant's accounts -->
    <section v-if="data?.accounts" class="bg-white ring-1 ring-stone-200/70 rounded-2xl overflow-hidden">
      <button class="w-full px-4 py-3 flex items-center gap-2 text-[12.5px] font-bold" @click="acctOpen = !acctOpen">
        <Icon name="settings" :size="14" class="text-stone-400" />{{ t('souk.accounts') }}
        <span v-if="!data.accounts.custody" class="text-[11px] font-semibold text-amber-700">· {{ t('souk.noBooks') }}</span>
        <Icon :name="acctOpen ? 'chevron-up' : 'chevron-down'" :size="14" class="ms-auto text-stone-400" />
      </button>
      <div v-if="acctOpen" class="px-4 pb-4 space-y-3 border-t border-stone-100 pt-3">
        <p class="text-[11.5px] text-stone-500">{{ t('souk.accountsHint') }}</p>
        <div v-for="k in ['custody', 'transportLoss', 'warehouseLoss']" :key="k" class="space-y-1">
          <label class="text-[12px] font-semibold text-stone-700">{{ t('souk.acct_' + k) }}</label>
          <input v-model="acct[k]" :list="k === 'custody' ? 'souk-cash' : 'souk-exp'" dir="ltr"
                 class="w-full h-10 rounded-lg ring-1 ring-stone-300 px-3 text-[12.5px]" />
        </div>
        <datalist id="souk-cash"><option v-for="a in data.accounts.cashOptions" :key="a" :value="a" /></datalist>
        <datalist id="souk-exp"><option v-for="a in data.accounts.expenseOptions" :key="a" :value="a" /></datalist>
        <button class="h-10 px-4 rounded-lg bg-stone-900 text-white text-[12.5px] font-bold disabled:opacity-40" :disabled="busy" @click="saveAccounts">{{ t('souk.save') }}</button>
      </div>
    </section>

    <!-- counted -->
    <section v-if="data?.counted?.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 text-[12.5px] font-bold">{{ t('souk.counted') }}</div>
      <div class="divide-y divide-stone-100">
        <div v-for="tr in data.counted" :key="tr.name" class="px-4 py-2 flex items-center gap-3 text-[12px]">
          <span class="text-stone-500 font-mono">#{{ tr.name }}</span>
          <span class="flex-1 truncate">{{ tr.buyerName }} · {{ tr.place }}</span>
          <span class="tabular-nums text-stone-600">{{ fmt(tr.counted) }} / {{ fmt(tr.expectedBack) }}</span>
          <span class="tabular-nums font-bold" :class="tr.counted - tr.expectedBack < 0 ? 'text-rose-600' : 'text-stone-400'">
            {{ Math.round(tr.counted - tr.expectedBack) === 0 ? '✓' : fmt(tr.counted - tr.expectedBack) }}
          </span>
          <span class="text-stone-400">{{ tr.countedBy }}</span>
          <button v-if="data.isAccountant && tr.transport > 0 && !tr.transportLcv"
                  class="h-7 px-2 rounded-md bg-stone-900 text-white text-[11px] font-bold disabled:opacity-40"
                  :disabled="busy || !tr.allReceived || !data.accounts?.custody"
                  :title="tr.allReceived ? '' : t('souk.transportWait')" @click="allocate(tr)">{{ t('souk.transportBtn') }}</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { uploadPhoto } from "@/lib/soukPhoto";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const data = ref(null);
const loading = ref(true);
const busy = ref(false);
const give = reactive({ buyer: "", cash: null, place: "Derb Omar" });
const transport = reactive({});
const count = reactive({});
const countNote = reactive({});
const acctOpen = ref(false);
const acct = reactive({ custody: "", transportLoss: "", warehouseLoss: "" });

const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const diff = (tr) => Math.round((Number(count[tr.name]) || 0) - tr.expectedBack);
function rcls(r) {
  return { ok: "bg-emerald-50 text-emerald-700", voucher_ok: "bg-emerald-50 text-emerald-700",
           voucher_pending: "bg-amber-50 text-amber-800", missing: "bg-rose-50 text-rose-700" }[r];
}

async function run(fn, okMsg) {
  busy.value = true;
  try {
    await fn();
    if (okMsg) success(okMsg);
    await load();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}
const openTrip = () => run(async () => {
  await apiPost("souk.open_trip", { buyer: give.buyer, cash: give.cash, place: give.place });
  give.buyer = ""; give.cash = null;
}, t("souk.handedOut"));
const saveTransport = (tr) => run(() => apiPost("souk.set_transport", { trip: tr.name, amount: transport[tr.name] || 0 }));
const transportReceipt = (tr, e) => {
  const file = e.target.files?.[0];
  if (file) run(() => uploadPhoto("transport", tr.name, file));
};
const receipt = (b, e) => {
  const file = e.target.files?.[0];
  if (file) run(() => uploadPhoto("receipt", b.po, file));
};
function voucher(b) {
  const phone = window.prompt(t("souk.voucherAsk"));
  if (phone) run(() => apiPost("souk.set_voucher", { po: b.po, phone }));
}
const approve = (b) => run(() => apiPost("souk.approve_voucher", { po: b.po }));
const allocate = (tr) => run(() => apiPost("souk.allocate_transport", { trip: tr.name }), t("souk.transportOk"));
const saveAccounts = () => run(() => apiPost("souk.save_settings", { settings_json: JSON.stringify({
  custodyAccount: acct.custody, transportLossAccount: acct.transportLoss, warehouseLossAccount: acct.warehouseLoss,
}) }), t("souk.saved"));
function close(tr) {
  if (!window.confirm(t("souk.closeConfirm").replace("{n}", fmt(tr.expected)))) return;
  run(() => apiPost("souk.close_trip", { trip: tr.name }), t("souk.closed"));
}
function doCount(tr) {
  run(() => apiPost("souk.count_trip", { trip: tr.name, counted: count[tr.name], note: countNote[tr.name] || "" }),
      t("souk.countedOk"));
}

async function load() {
  loading.value = true;
  try {
    data.value = await api("souk.trips_boot");
    for (const tr of data.value.open) if (transport[tr.name] === undefined) transport[tr.name] = tr.transport || null;
    if (data.value.accounts) {
      acct.custody = data.value.accounts.custody;
      acct.transportLoss = data.value.accounts.transportLoss;
      acct.warehouseLoss = data.value.accounts.warehouseLoss;
    }
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>
