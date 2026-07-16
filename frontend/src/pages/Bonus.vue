<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1000px] mx-auto">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('bn.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('bn.intro') }}</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <!-- group switch (manager only — the server sends one group otherwise) -->
        <div v-if="(d?.groups || []).length > 1" class="flex items-center gap-1">
          <button v-for="g in d.groups" :key="g"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors"
                  :class="group === g ? 'bg-violet-600 text-white ring-violet-600' : 'bg-white text-stone-600 ring-stone-200'"
                  @click="group = g; load()">{{ t('bn.grp_' + g) }}</button>
        </div>
        <div class="flex items-center gap-1">
          <button v-for="m in months" :key="m.key"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors"
                  :class="month === m.key ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200'"
                  @click="month = m.key; load()">{{ m.label }}</button>
        </div>
      </div>
    </header>

    <div v-if="loading" class="space-y-2">
      <div class="h-[110px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      <div class="h-[220px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="loadError" class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
      <div class="text-[11.5px] text-stone-400 font-mono mt-1 max-w-[420px] mx-auto break-words">{{ loadError }}</div>
    </div>

    <!-- roles whose work has no per-person source yet -->
    <div v-else-if="d && !d.available" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-10 text-center">
      <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-stone-100 text-stone-400 mb-2.5">
        <Icon name="wallet" :size="22" />
      </span>
      <div class="text-[13.5px] font-semibold text-stone-800">{{ t('bn.noScheme') }}</div>
      <div class="text-[12px] text-stone-400 mt-0.5 max-w-[420px] mx-auto">{{ t('bn.noSchemeHint') }}</div>
    </div>

    <template v-else-if="d">
      <!-- my card -->
      <div class="bn-hero rounded-2xl p-5">
        <div class="flex items-center gap-4 flex-wrap">
          <span class="bn-ico"><Icon name="wallet" :size="20" /></span>
          <div class="flex-1 min-w-[220px]">
            <div class="flex items-baseline gap-2 flex-wrap">
              <template v-if="d.me.pay">
                <span class="text-[30px] font-extrabold text-stone-900 tabular-nums leading-none">{{ d.me.pay.total }}</span>
                <span class="text-[12px] font-semibold text-stone-500">{{ d.me.pay.currency }}</span>
                <span class="text-[11px] text-stone-400 tabular-nums">· {{ nPoints }} {{ t('bn.pts') }} / {{ d.target }}</span>
              </template>
              <template v-else>
                <span class="text-[30px] font-extrabold text-stone-900 tabular-nums leading-none">{{ nPoints }}</span>
                <span class="text-[12px] text-stone-500">{{ t('bn.pts') }} / {{ d.target }}</span>
              </template>
              <span v-if="d.me.rank" class="ms-1 text-[11px] font-bold rounded-full px-2.5 py-0.5"
                    :class="d.me.rank === 1 ? 'text-amber-700 bg-amber-50 ring-1 ring-amber-200' : 'text-stone-600 bg-stone-100 ring-1 ring-stone-200'">
                #{{ d.me.rank }}
              </span>
            </div>
            <div class="h-2 rounded-full bg-stone-100 overflow-hidden mt-2.5 max-w-[420px]">
              <div class="h-full rounded-full transition-all duration-700"
                   :class="d.me.points >= d.target ? 'bg-emerald-500' : 'bg-amber-500'"
                   :style="{ width: pct + '%' }" />
            </div>
            <div class="text-[11px] text-stone-400 mt-1.5 tabular-nums">
              {{ d.me.actions }} {{ t('bn.actions') }} · {{ pct }}% {{ t('bn.ofTarget') }}
            </div>
            <!-- how the payout was reached — never a black box -->
            <div v-if="d.me.pay" class="flex flex-wrap items-center gap-1.5 mt-2">
              <span class="bn-part">{{ t('bn.pBase') }} <b class="tabular-nums">{{ d.me.pay.base }}</b></span>
              <span v-if="d.me.pay.streakPct" class="bn-part bn-part-good">
                <Icon name="zap" :size="10" />{{ d.me.pay.streakDays }}{{ t('cf.days') }} +{{ d.me.pay.streakPct }}%
              </span>
              <span v-if="d.me.pay.kicker" class="bn-part bn-part-good">
                <Icon name="users" :size="10" />{{ t('bn.pKicker') }} +{{ d.me.pay.kicker }}
              </span>
              <span v-if="d.me.pay.gatePct !== null" class="bn-part"
                    :class="d.me.pay.gatePass ? 'bn-part-good' : 'bn-part-bad'">
                <Icon :name="d.me.pay.gatePass ? 'check-circle' : 'shield-alert'" :size="10" />
                {{ t('bn.pGate') }} {{ d.me.pay.gatePct }}%
              </span>
              <span v-if="d.me.pay.capped" class="bn-part bn-part-warn">
                <Icon name="alert-triangle" :size="10" />{{ t('bn.pCapped') }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- team kicker: everyone gets it, or nobody does -->
      <div v-if="d.money?.kickerOn" class="rounded-2xl p-4 flex items-center gap-3.5 flex-wrap"
           :class="d.money.kickerHit ? 'bn-kick-on' : 'bn-kick-off'">
        <span class="w-10 h-10 rounded-xl grid place-items-center text-white shrink-0"
              :class="d.money.kickerHit ? 'bg-emerald-500' : 'bg-amber-500'">
          <Icon name="users" :size="19" />
        </span>
        <div class="flex-1 min-w-[200px]">
          <div class="text-[13.5px] font-bold text-stone-900">
            {{ t('bn.kickTitle') }} · +{{ d.money.kickerAmount }} {{ d.money.currency }}
          </div>
          <div class="text-[12px] text-stone-600 mt-0.5">
            {{ d.money.kickerHit ? t('bn.kickHit') : t('bn.kickMiss') }}
            <b class="tabular-nums">{{ d.money.sameday }}%</b> / {{ d.money.kickerTargetPct }}%
          </div>
        </div>
        <div class="w-[120px] shrink-0">
          <div class="h-2 rounded-full bg-white/70 overflow-hidden">
            <div class="h-full rounded-full transition-all duration-700"
                 :class="d.money.kickerHit ? 'bg-emerald-500' : 'bg-amber-500'"
                 :style="{ width: Math.min(100, (d.money.sameday / d.money.kickerTargetPct) * 100) + '%' }" />
          </div>
        </div>
      </div>

      <!-- leaderboard -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
          <Icon name="trending-up" :size="14" class="text-stone-400" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('cco.leaderboard') }}</span>
          <span class="text-[11px] text-stone-400 tabular-nums">{{ d.month }} · {{ t('bn.grp_' + d.group) }}</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[560px] text-[12.5px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t('cfr.thAgent') }}</th>
                <th v-for="c in d.cols" :key="c" class="text-end px-3 py-2.5">{{ t(c) }}</th>
                <th class="text-end px-4 py-2.5">{{ t('bn.thPoints') }}</th>
                <th v-if="d.money?.on" class="text-end px-4 py-2.5">{{ t('bn.thPay') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="(a, i) in d.agents" :key="a.user" class="hover:bg-stone-50"
                  :class="a.user === d.meUser ? 'bg-amber-50/40' : ''">
                <td class="px-4 py-2.5">
                  <span class="inline-flex items-center gap-2">
                    <span class="w-5 h-5 rounded-full text-[10px] font-bold inline-flex items-center justify-center"
                          :class="i === 0 ? 'bg-amber-100 text-amber-700' : 'bg-stone-100 text-stone-500'">{{ i + 1 }}</span>
                    <span class="font-medium text-stone-900">{{ a.agent }}</span>
                  </span>
                </td>
                <td v-for="(v, ci) in a.cols" :key="ci" class="px-3 py-2.5 text-end tabular-nums text-stone-600">
                  {{ v || '—' }}
                </td>
                <td class="px-4 py-2.5 text-end">
                  <div class="inline-flex items-center gap-2">
                    <div class="w-[56px] h-1.5 rounded-full bg-stone-100 overflow-hidden">
                      <div class="h-full rounded-full transition-all duration-700"
                           :class="a.points >= d.target ? 'bg-emerald-500' : 'bg-amber-500'"
                           :style="{ width: Math.min(100, a.points * 100 / d.target) + '%' }" />
                    </div>
                    <span class="tabular-nums font-bold text-stone-900 w-[52px] text-end">{{ a.points }}</span>
                  </div>
                </td>
                <td v-if="d.money?.on" class="px-4 py-2.5 text-end">
                  <span class="tabular-nums font-bold text-stone-900">{{ a.pay?.total ?? '—' }}</span>
                  <span v-if="a.prize" class="ms-1.5 text-[10px] font-bold text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-full px-1.5 py-0.5">
                    +{{ a.prize }}
                  </span>
                  <Icon v-if="a.pay && !a.pay.gatePass" name="shield-alert" :size="11"
                        class="inline ms-1 text-rose-500" :title="t('bn.pGateFail')" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
            <tfoot v-if="d.money?.on && d.money.pool !== null">
              <tr class="border-t border-stone-200 bg-stone-50/60 text-[12.5px] font-bold">
                <td class="px-4 py-2.5" :colspan="(d.cols?.length || 1) + 2">{{ t('bn.pool') }}</td>
                <td class="px-4 py-2.5 text-end text-stone-900 tabular-nums">
                  {{ d.money.pool }} <span class="text-[10px] font-normal text-stone-400">{{ d.money.currency }}</span>
                </td>
              </tr>
            </tfoot>
        <div v-if="!d.agents.length" class="text-center text-[12.5px] text-stone-400 py-8">{{ t('cfr.noData') }}</div>
      </div>

      <!-- scheme editor (manager) -->
      <div v-if="scheme?.canEdit" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
        <div class="flex items-center gap-2">
          <Icon name="settings" :size="14" class="text-stone-400" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('bn.schemeTitle') }}</span>
          <span class="text-[11px] text-stone-400">{{ t('bn.schemeHint') }}</span>
        </div>
        <div class="flex items-center gap-4 flex-wrap">
          <label v-for="g in scheme.groups" :key="g" class="inline-flex items-center gap-2 text-[12px] text-stone-600">
            {{ t('bn.target') }} — {{ t('bn.grp_' + g) }}
            <input v-model.number="scheme.targets[g]" type="number" min="1"
                   class="w-24 h-9 ps-3 rounded-lg ring-1 ring-stone-200 text-[12.5px] tabular-nums focus:outline-none"
                   @input="dirty = true" />
          </label>
        </div>

        <!-- MONEY. Nothing here is a decision the code gets to make. -->
        <div v-if="scheme.money" class="rounded-xl bg-amber-50/40 ring-1 ring-amber-200/60 p-3.5 space-y-3">
          <label class="flex items-center gap-2.5 cursor-pointer">
            <button type="button" role="switch" :aria-checked="!!scheme.money.on"
                    class="relative w-11 h-6 rounded-full transition-colors shrink-0"
                    :class="scheme.money.on ? 'bg-amber-500' : 'bg-stone-300'"
                    @click="scheme.money.on = scheme.money.on ? 0 : 1; dirty = true">
              <span class="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform"
                    :class="scheme.money.on ? 'translate-x-5' : 'translate-x-0'" />
            </button>
            <span>
              <span class="block text-[12.5px] font-bold text-stone-900">{{ t('bn.mTitle') }}</span>
              <span class="block text-[11px] text-stone-500">{{ t('bn.mHint') }}</span>
            </span>
          </label>

          <template v-if="scheme.money.on">
            <div class="grid sm:grid-cols-2 gap-x-4 gap-y-2.5 pt-1">
              <label v-for="g in scheme.groups" :key="'pp' + g" class="flex items-center justify-between gap-2 text-[12px] text-stone-600">
                <span>{{ t('bn.mPerPoint') }} — {{ t('bn.grp_' + g) }}</span>
                <input v-model.number="scheme.money.perPoint[g]" type="number" min="0" step="0.5"
                       class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
              </label>
              <label v-for="g in scheme.groups" :key="'cap' + g" class="flex items-center justify-between gap-2 text-[12px] text-stone-600">
                <span>{{ t('bn.mCap') }} — {{ t('bn.grp_' + g) }}</span>
                <input v-model.number="scheme.money.monthlyCap[g]" type="number" min="0" step="100"
                       class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
              </label>
              <label class="flex items-center justify-between gap-2 text-[12px] text-stone-600">
                <span>{{ t('bn.mStreakStep') }}</span>
                <input v-model.number="scheme.money.streakStepPct" type="number" min="0" max="50"
                       class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
              </label>
              <label class="flex items-center justify-between gap-2 text-[12px] text-stone-600">
                <span>{{ t('bn.mStreakCap') }}</span>
                <input v-model.number="scheme.money.streakCapPct" type="number" min="0" max="200"
                       class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
              </label>
            </div>

            <!-- quality gate, per group -->
            <div class="pt-2 border-t border-amber-200/60 space-y-2">
              <div class="text-[11.5px] font-bold text-stone-700">{{ t('bn.mGate') }}</div>
              <p class="text-[11px] text-stone-500">{{ t('bn.mGateHint') }}</p>
              <div class="flex flex-wrap gap-3">
                <label v-for="g in scheme.groups" :key="'gate' + g"
                       class="inline-flex items-center gap-2 text-[12px] text-stone-600">
                  <input type="checkbox" class="w-4 h-4" style="accent-color: #d97706"
                         :checked="!!scheme.money.gateOn[g]"
                         @change="scheme.money.gateOn[g] = scheme.money.gateOn[g] ? 0 : 1; dirty = true" />
                  {{ t('bn.grp_' + g) }}
                  <input v-model.number="scheme.money.gatePct[g]" type="number" min="0" max="100"
                         :disabled="!scheme.money.gateOn[g]"
                         class="w-16 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none disabled:bg-stone-100 disabled:text-stone-400"
                         @input="dirty = true" />%
                </label>
              </div>
              <p v-if="!scheme.money.gateOn.floor" class="text-[11px] text-stone-400">{{ t('bn.mGateFloorWhy') }}</p>
            </div>

            <!-- team kicker -->
            <div class="pt-2 border-t border-amber-200/60 space-y-2">
              <label class="inline-flex items-center gap-2 text-[12px] font-bold text-stone-700">
                <input type="checkbox" class="w-4 h-4" style="accent-color: #d97706"
                       :checked="!!scheme.money.kickerOn"
                       @change="scheme.money.kickerOn = scheme.money.kickerOn ? 0 : 1; dirty = true" />
                {{ t('bn.mKicker') }}
              </label>
              <p class="text-[11px] text-stone-500">{{ t('bn.mKickerHint') }}</p>
              <div v-if="scheme.money.kickerOn" class="flex flex-wrap gap-3">
                <label class="inline-flex items-center gap-2 text-[12px] text-stone-600">
                  {{ t('bn.mKickerAmount') }}
                  <input v-model.number="scheme.money.kickerAmount" type="number" min="0" step="10"
                         class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
                </label>
                <label class="inline-flex items-center gap-2 text-[12px] text-stone-600">
                  {{ t('bn.mKickerTarget') }}
                  <input v-model.number="scheme.money.kickerTargetPct" type="number" min="0" max="100"
                         class="w-16 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />%
                </label>
              </div>
            </div>

            <!-- weekly top 3 -->
            <div class="pt-2 border-t border-amber-200/60">
              <div class="text-[11.5px] font-bold text-stone-700 mb-1.5">{{ t('bn.mWeekly') }}</div>
              <div class="flex items-center gap-2">
                <input v-for="(v, i) in scheme.money.weeklyTop" :key="i"
                       v-model.number="scheme.money.weeklyTop[i]" type="number" min="0" step="10"
                       class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
                <span class="text-[11px] text-stone-400">{{ scheme.money.currency }} · 1st / 2nd / 3rd</span>
              </div>
            </div>
          </template>
        </div>
        <div class="grid sm:grid-cols-3 gap-x-4 gap-y-2 pt-1">
          <label v-for="(v, k) in scheme.points" :key="k"
                 class="flex items-center justify-between gap-2 text-[12px] text-stone-600">
            <span class="font-mono text-[11px]">{{ k }}</span>
            <input v-model.number="scheme.points[k]" type="number" min="0" step="0.05"
                   class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none"
                   @input="dirty = true" />
          </label>
        </div>
        <div class="flex justify-end">
          <button class="h-9 px-4 rounded-lg text-[12px] font-bold text-white bg-stone-900 hover:bg-stone-800 disabled:opacity-50 transition-colors"
                  :disabled="!dirty || saving" @click="saveScheme">
            {{ saving ? '…' : t('px.common.save') }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const now = new Date();
const fmt = (dt) => `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}`;
const months = computed(() => {
  const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  return [
    { key: fmt(now), label: t("bn.thisMonth") },
    { key: fmt(prev), label: t("bn.lastMonth") },
  ];
});

const month = ref(fmt(now));
const group = ref("");
const d = ref(null);
const loading = ref(true);
const loadError = ref("");
const scheme = ref(null);
const dirty = ref(false);
const saving = ref(false);

const pct = computed(() => {
  if (!d.value?.target) return 0;
  return Math.round(Math.min(100, (d.value.me.points * 100) / d.value.target));
});

// Count the points up — the number is the point of the page.
const nPoints = ref(0);
watch(d, (v) => {
  if (!v?.available) return;
  const from = nPoints.value;
  const to = v.me.points;
  const t0 = performance.now();
  const step = (now2) => {
    const p = Math.min(1, (now2 - t0) / 900);
    const eased = 1 - Math.pow(1 - p, 3);
    nPoints.value = Math.round((from + (to - from) * eased) * 10) / 10;
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
});

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const res = await api("contact_center.bonus", {
      month: month.value, group: group.value || undefined,
    });
    d.value = res;
    if (res.group) group.value = res.group;
  } catch (e) {
    loadError.value = String(e.message || e);
  } finally {
    loading.value = false;
  }
}

async function loadScheme() {
  try {
    scheme.value = await api("contact_center.bonus_settings");
  } catch {
    scheme.value = null;
  }
}

async function saveScheme() {
  saving.value = true;
  try {
    const res = await apiPost("contact_center.save_bonus_settings", {
      settings: { targets: scheme.value.targets, points: scheme.value.points,
                  money: scheme.value.money },
    });
    Object.assign(scheme.value, res);
    dirty.value = false;
    success(t("cfs.saved"));
    load();
  } catch (e) {
    warn(t("cfs.saveFail"), String(e.message || e));
  } finally {
    saving.value = false;
  }
}

onMounted(() => { load(); loadScheme(); });
</script>

<style scoped>
.bn-hero {
  background: linear-gradient(135deg, rgb(255 251 235) 0%, #fff 50%, rgb(255 251 235) 100%);
  box-shadow: inset 0 0 0 1px rgb(253 230 138 / 0.6), 0 1px 2px rgb(0 0 0 / 0.03);
}
.bn-part {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10.5px; font-weight: 600; color: rgb(87 83 78);
  background: rgb(255 255 255 / .8); border-radius: 999px; padding: 3px 9px;
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
}
.bn-part-good { color: #047857; box-shadow: inset 0 0 0 1px #a7f3d0; }
.bn-part-bad { color: #be123c; box-shadow: inset 0 0 0 1px #fda4af; }
.bn-part-warn { color: #b45309; box-shadow: inset 0 0 0 1px #fcd34d; }
.bn-kick-on {
  background: linear-gradient(90deg, rgb(236 253 245), #fff);
  box-shadow: inset 0 0 0 1px rgb(167 243 208);
}
.bn-kick-off {
  background: linear-gradient(90deg, rgb(255 251 235), #fff);
  box-shadow: inset 0 0 0 1px rgb(253 230 138);
}
.bn-ico {
  width: 48px; height: 48px; border-radius: 14px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  color: white;
  background: linear-gradient(135deg, rgb(251 191 36), rgb(217 119 6));
  box-shadow: 0 6px 16px -6px rgb(217 119 6 / 0.5);
}
</style>
