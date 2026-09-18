<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto">
    <!-- hero: the floor, live -->
    <header class="rounded-2xl p-5 sm:p-6 bg-white ring-1 ring-stone-200/70">
      <div class="flex items-start justify-between gap-5 flex-wrap">
        <div class="flex items-center gap-3.5 min-w-0">
          <span class="w-[52px] h-[52px] rounded-2xl inline-flex items-center justify-center text-white flex-shrink-0"
                style="background: linear-gradient(135deg, rgb(234 88 12), rgb(194 65 12)); box-shadow: 0 6px 16px -6px rgb(234 88 12 / .5)"><Icon name="activity" :size="22" /></span>
          <div class="min-w-0">
            <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('pulse.title') }}</h1>
            <p class="text-[12.5px] text-stone-500 mt-1.5 max-w-[640px]">{{ t('pulse.intro') }}</p>
            <div class="mt-2 flex items-center gap-2 text-[11px] tabular-nums" :class="loadError ? 'text-rose-600' : 'text-stone-400'" dir="ltr">
              <span class="w-1.5 h-1.5 rounded-full" :class="loadError ? 'bg-rose-500' : refreshing ? 'bg-amber-400 animate-pulse' : 'bg-emerald-500'" />
              <span>{{ d?.now }}</span>
              <span v-if="loadError && d" dir="auto">{{ t('oclk.staleWarn') }}</span>
            </div>
          </div>
        </div>
        <div v-if="d" class="flex items-stretch gap-2 flex-wrap">
          <div class="sh-stat"><span class="sh-stat-n text-stone-900">{{ d.total }}</span><span class="sh-stat-l">{{ t('pulse.lists') }}</span></div>
          <div class="sh-stat"><span class="sh-stat-n" :class="stuckTotal ? 'text-rose-600' : 'text-emerald-600'">{{ stuckTotal }}</span><span class="sh-stat-l">{{ t('pulse.stuck') }}</span></div>
          <div class="sh-stat"><span class="sh-stat-n text-stone-900">{{ activePeople }}</span><span class="sh-stat-l">{{ t('pulse.active') }}</span></div>
        </div>
      </div>
    </header>

    <!-- the seven doors: how many lists stand at each, the oldest, the stuck -->
    <section v-if="d" class="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-7 gap-2">
      <button v-for="s in STAGES" :key="s.key" type="button" class="rounded-2xl p-3 text-start ring-1 transition-all"
              :class="stageF === s.key ? 'bg-stone-900 text-white ring-stone-900' : d.stages[s.key].stuck ? 'bg-rose-50/70 ring-rose-200 hover:ring-rose-300' : 'bg-white ring-stone-200/70 hover:ring-stone-300'"
              :aria-pressed="stageF === s.key" @click="stageF = stageF === s.key ? '' : s.key">
        <span class="flex items-center gap-1.5 text-[10.5px] font-bold uppercase tracking-wide" :class="stageF === s.key ? 'text-white/70' : 'text-stone-400'">
          <Icon :name="s.icon" :size="12" />{{ t('pulse.st_' + s.key) }}
        </span>
        <span class="mt-1.5 flex items-end gap-2">
          <span class="text-[24px] font-extrabold tabular-nums leading-none">{{ d.stages[s.key].n }}</span>
          <span v-if="d.stages[s.key].stuck" class="text-[11px] font-bold tabular-nums mb-0.5" :class="stageF === s.key ? 'text-rose-300' : 'text-rose-600'">{{ d.stages[s.key].stuck }} {{ t('pulse.stuckShort') }}</span>
        </span>
        <span class="block mt-1 text-[10.5px] tabular-nums" :class="stageF === s.key ? 'text-white/60' : 'text-stone-400'" dir="ltr">
          <template v-if="d.stages[s.key].n">{{ t('pulse.oldest') }} {{ mins(d.stages[s.key].oldestMin) }}</template><template v-else>—</template>
        </span>
      </button>
    </section>

    <!-- who is on the floor right now -->
    <section v-if="d && d.people.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 px-4 py-3 flex items-center gap-2 flex-wrap">
      <span class="text-[11px] font-bold uppercase tracking-wide text-stone-400 me-1">{{ t('pulse.people') }}</span>
      <button v-for="p in d.people" :key="p.user" type="button" class="lp-tap h-8 ps-1 pe-2.5 rounded-full text-[11.5px] font-semibold ring-1 inline-flex items-center gap-1.5 transition-colors"
              :class="whoF === p.user ? 'bg-stone-900 text-white ring-stone-900' : idleCls(p)" :aria-pressed="whoF === p.user" :title="peopleTitle(p)" @click="whoF = whoF === p.user ? '' : p.user">
        <span class="w-6 h-6 rounded-full grid place-items-center text-[10px] font-bold" :class="whoF === p.user ? 'bg-white/20' : 'bg-white/70'">{{ initials(p.name) }}</span>
        <span class="truncate max-w-[120px]" dir="auto">{{ p.name }}</span>
        <span class="tabular-nums opacity-80" dir="ltr">{{ p.idleMin != null ? mins(p.idleMin) : '—' }}</span>
        <span v-if="p.current" class="font-mono text-[10px] opacity-70" dir="ltr">{{ p.current }}</span>
        <span class="w-6 h-6 rounded-full grid place-items-center hover:bg-black/10" role="button" :title="t('pulse.nudgeHint') + ' ' + p.name" @click.stop="doNudgePerson(p)"><Icon name="bell" :size="11" /></span>
      </button>
    </section>

    <!-- filters -->
    <div v-if="d" class="flex items-center gap-2 flex-wrap">
      <div class="sh-seg">
        <button v-for="h in [8, 24, 48]" :key="h" class="sh-seg-btn" :class="hours === h ? 'sh-seg-on' : ''" :aria-pressed="hours === h" @click="hours = h; load()">{{ h }}{{ t('oclk.hShort') }}</button>
      </div>
      <button class="lp-tap h-8 px-3 rounded-full text-[11.5px] font-semibold ring-1 transition-colors inline-flex items-center gap-1.5"
              :class="stuckOnly ? 'bg-rose-600 text-white ring-rose-600' : 'bg-white text-rose-700 ring-rose-200 hover:bg-rose-50'" :aria-pressed="stuckOnly" @click="stuckOnly = !stuckOnly">
        <Icon name="alert-triangle" :size="12" />{{ t('pulse.stuckOnly') }}
      </button>
      <button v-if="stageF || whoF" class="lp-tap h-8 px-3 rounded-full text-[11.5px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50" @click="stageF = ''; whoF = ''">{{ t('pulse.clearFilters') }}</button>
      <div class="relative ms-auto">
        <Icon name="search" :size="13" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input v-model="q" :placeholder="t('pulse.searchPh')" class="h-8 w-[220px] ps-8 pe-3 rounded-full bg-white ring-1 ring-stone-200 text-[12px] focus:outline-none focus:ring-stone-400" dir="ltr" />
      </div>
      <button class="lp-tap h-8 px-3 rounded-full text-[11.5px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50 inline-flex items-center gap-1.5" :aria-expanded="showCfg" @click="showCfg = !showCfg; if (showCfg) loadMeasure()">
        <Icon name="settings" :size="12" />{{ t('pulse.thresholds') }}
      </button>
    </div>

    <!-- thresholds: when a door counts as stuck -->
    <section v-if="showCfg && cfg" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
      <div class="flex items-center gap-2 flex-wrap mb-3">
        <p class="text-[11.5px] text-stone-500 flex-1 min-w-[260px]">{{ t('pulse.thresholdsHint') }}</p>
        <span v-if="meas" class="text-[11px] text-stone-400 tabular-nums">{{ t('pulse.measuredOver') }} {{ meas.days }}{{ t('oclk.dShort') }} · {{ meas.lists }} {{ t('pulse.lists') }}</span>
        <button v-if="meas" class="lp-tap h-8 px-3 rounded-lg text-[11px] font-bold text-amber-800 bg-amber-50 ring-1 ring-amber-200 hover:bg-amber-100" @click="useAll('p90')">{{ t('pulse.useAllP90') }}</button>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-7 gap-3">
        <label v-for="k in CFG_KEYS" :key="k" class="block">
          <span class="block text-[10.5px] font-bold uppercase tracking-wide text-stone-400 mb-1">{{ t('pulse.cfg_' + k) }}</span>
          <span class="flex items-center gap-1.5">
            <input v-model.number="cfg[k]" type="number" min="1" max="1440" dir="ltr" class="h-9 w-full px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums text-center" />
            <span class="text-[11px] text-stone-400">{{ t('pulse.minShort') }}</span>
          </span>
          <!-- what the floor actually does at this door: the evidence next to the setting -->
          <span v-if="meas && meas.keys[k] && meas.keys[k].n" class="mt-1 flex items-center gap-1 text-[10px] tabular-nums text-stone-400" dir="ltr">
            p50 <b class="text-stone-600">{{ meas.keys[k].p50 }}</b> · p75 <b class="text-stone-600">{{ meas.keys[k].p75 }}</b> ·
            <button class="font-bold rounded px-1 ring-1" :class="cfg[k] === meas.keys[k].p90 ? 'text-stone-500 bg-stone-100 ring-stone-200' : 'text-amber-800 bg-amber-50 ring-amber-200 hover:bg-amber-100'" :title="t('pulse.useP90')" @click.prevent="cfg[k] = meas.keys[k].p90">p90 {{ meas.keys[k].p90 }}</button>
            <span class="text-stone-300">n{{ meas.keys[k].n }}</span>
          </span>
          <span v-else-if="meas" class="mt-1 block text-[10px] text-stone-300">{{ t('pulse.noHistory') }}</span>
        </label>
      </div>
      <div class="mt-3 flex items-center gap-2">
        <button class="h-9 px-4 rounded-xl text-[12.5px] font-bold text-white disabled:opacity-50" style="background: linear-gradient(135deg, rgb(234 88 12), rgb(194 65 12))" :disabled="saving" @click="saveCfg">{{ saving ? t('oclk.saving') : t('common.save') }}</button>
        <span class="text-[11px] text-stone-400">{{ t('pulse.measured') }}</span>
        <span class="ms-auto text-[11px] text-stone-400">{{ t('pulse.bellHint') }}</span>
      </div>
    </section>

    <!-- the lists -->
    <div v-if="!d && loading" class="space-y-2.5"><div v-for="n in 6" :key="n" class="h-[96px] rounded-2xl sh-shimmer" /></div>
    <div v-else-if="loadError && !d" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ t('common.loadFail') }}</div>
      <div class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button class="mt-3 h-9 px-4 rounded-xl text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>
    <section v-else-if="d && shown.length" class="space-y-2.5">
      <div class="flex items-center gap-2 px-1">
        <span class="text-[13px] font-bold text-stone-900">{{ stageF ? t('pulse.st_' + stageF) : t('pulse.allLists') }}</span>
        <span class="text-[11px] text-stone-400 tabular-nums">{{ shown.length }}</span>
        <span class="ms-auto text-[10.5px] text-stone-400 hidden md:inline">{{ t('pulse.sortHint') }}</span>
      </div>
      <article v-for="r in shown" :key="r.name" class="bg-white rounded-2xl ring-1 px-4 py-3 transition-shadow" :class="r.reason ? 'ring-rose-300 shadow-[0_4px_16px_-8px_rgb(244_63_94/.35)]' : 'ring-stone-200/70'">
        <div class="flex items-start gap-4 flex-wrap lg:flex-nowrap">
          <!-- who and what -->
          <div class="min-w-0 basis-[220px] flex-shrink-0">
            <div class="flex items-center gap-2 flex-wrap">
              <a :href="'/app/pick-list/' + encodeURIComponent(r.name)" target="_blank" rel="noopener" class="font-mono text-[13px] font-bold text-stone-900 hover:underline" dir="ltr">{{ r.name }}</a>
              <span class="text-[10px] font-bold rounded-full px-2 py-0.5 ring-1 whitespace-nowrap" :class="STAGE_CLS[r.stage]">{{ t('pulse.st_' + r.stage) }}</span>
            </div>
            <div class="text-[11px] text-stone-500 mt-1 tabular-nums" dir="auto">
              {{ r.orders }} {{ t('pulse.orders') }} · {{ r.qty }} {{ t('pulse.units') }} · <span dir="ltr">{{ local(r.createdAt).slice(11) }}</span> {{ t('pulse.by') }} {{ r.createdByName }}
            </div>
            <div class="mt-1.5 flex items-center gap-1.5 flex-wrap">
              <span v-if="r.pickerName" class="inline-flex items-center gap-1 text-[10.5px] font-semibold rounded-full px-2 py-0.5 bg-amber-50 text-amber-800 ring-1 ring-amber-200" :title="t('pulse.picker')"><Icon name="user" :size="10" />{{ r.pickerName }}</span>
              <span v-if="r.sorterName" class="inline-flex items-center gap-1 text-[10.5px] font-semibold rounded-full px-2 py-0.5 bg-sky-50 text-sky-800 ring-1 ring-sky-200" :title="t('pulse.sorter')"><Icon name="layout-grid" :size="10" />{{ r.sorterName }}</span>
              <span v-if="r.packerName" class="inline-flex items-center gap-1 text-[10.5px] font-semibold rounded-full px-2 py-0.5 bg-violet-50 text-violet-800 ring-1 ring-violet-200" :title="t('pulse.packer')"><Icon name="package-check" :size="10" />{{ r.packerName }}</span>
            </div>
          </div>

          <!-- the seven doors as a stepper, each with its time and its count -->
          <div class="flex-1 min-w-0 overflow-x-auto" style="scrollbar-width: none">
            <ol class="flex items-start min-w-[640px]">
              <li v-for="(s, i) in STAGES" :key="s.key" class="flex-1 min-w-0 relative">
                <div class="flex items-center">
                  <span v-if="i" class="flex-1 h-[3px]" :class="r.doors[s.key].done || r.stage === s.key ? (r.reason && r.stage === s.key ? 'bg-rose-300' : 'bg-emerald-300') : 'bg-stone-200'" />
                  <span v-else class="flex-1" />
                  <span class="w-7 h-7 rounded-full grid place-items-center ring-4 ring-white flex-shrink-0 z-10"
                        :class="doorCls(r, s.key)"><Icon :name="doorIcon(r, s.key)" :size="12" /></span>
                  <span v-if="i < STAGES.length - 1" class="flex-1 h-[3px]" :class="r.doors[s.key].done ? 'bg-emerald-300' : 'bg-stone-200'" />
                  <span v-else class="flex-1" />
                </div>
                <div class="text-center mt-1 px-0.5">
                  <div class="text-[10px] font-bold uppercase tracking-wide truncate" :class="r.stage === s.key ? (r.reason ? 'text-rose-600' : 'text-emerald-700') : r.doors[s.key].done ? 'text-stone-600' : 'text-stone-300'">{{ t('pulse.st_' + s.key) }}</div>
                  <div class="text-[10.5px] tabular-nums text-stone-400" dir="ltr">
                    <template v-if="r.doors[s.key].skip">{{ t('pulse.skip') }}</template>
                    <template v-else-if="r.doors[s.key].at">{{ local(r.doors[s.key].at).slice(11) }}</template>
                    <template v-else>—</template>
                    <template v-if="r.doors[s.key].of != null && !r.doors[s.key].skip"> · {{ r.doors[s.key].n }}/{{ r.doors[s.key].of }}</template>
                    <template v-if="r.doors[s.key].min != null && r.doors[s.key].min > 0"> · {{ mins(r.doors[s.key].min) }}</template>
                  </div>
                  <div v-if="s.key === 'picking' && r.doors.picking.of" class="mt-1 mx-2 h-1 rounded-full bg-stone-100 overflow-hidden"><span class="block h-full bg-amber-400" :style="{ width: pct(r.doors.picking.n, r.doors.picking.of) }" /></div>
                  <div v-else-if="s.key === 'sorting' && !r.doors.sorting.skip && r.doors.sorting.of" class="mt-1 mx-2 h-1 rounded-full bg-stone-100 overflow-hidden"><span class="block h-full bg-sky-400" :style="{ width: pct(r.doors.sorting.n, r.doors.sorting.of) }" /></div>
                </div>
              </li>
            </ol>
          </div>

          <!-- where it stands, for how long, and why that is a problem -->
          <div class="flex-shrink-0 text-end basis-[170px]">
            <div class="text-[20px] font-extrabold tabular-nums leading-none" :class="r.reason ? 'text-rose-600' : 'text-stone-900'" dir="ltr">{{ mins(r.ageMin) }}</div>
            <div class="text-[10.5px] text-stone-400 mt-0.5">{{ t('pulse.inStage') }} <span dir="ltr">{{ local(r.since).slice(11) }}</span></div>
            <div v-if="r.reason" class="mt-1.5 inline-flex items-center gap-1 text-[10.5px] font-bold rounded-full px-2 py-0.5 bg-rose-50 text-rose-700 ring-1 ring-rose-200">
              <Icon name="alert-triangle" :size="10" />{{ reasonText(r) }}
            </div>
            <div v-else-if="r.snoozedUntil" class="mt-1.5 inline-flex items-center gap-1 text-[10.5px] font-bold rounded-full px-2 py-0.5 bg-stone-100 text-stone-500 ring-1 ring-stone-200" :title="local(r.snoozedUntil)"><Icon name="circle-pause" :size="10" />{{ t('pulse.snoozedTill') }} <span dir="ltr">{{ local(r.snoozedUntil).slice(11) }}</span></div>
            <div v-else-if="r.stage === 'shipped'" class="mt-1.5 inline-flex items-center gap-1 text-[10.5px] font-bold rounded-full px-2 py-0.5 bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"><Icon name="check" :size="10" />{{ t('pulse.done') }}</div>
            <!-- the actions: hand it over, tap the shoulder, mark it handled, open the door's own screen -->
            <div class="mt-2 flex items-center justify-end gap-1 flex-wrap">
              <template v-if="r.docstatus === 0">
                <select v-if="reassignFor === r.name" class="h-8 rounded-lg text-[11px] font-semibold bg-white ring-1 ring-amber-300 px-2" :disabled="busy === r.name" @change="doReassign(r, $event.target.value)">
                  <option value="">{{ t('pulse.pickPicker') }}</option>
                  <option v-for="pk in d.pickers" :key="pk.email" :value="pk.email" :selected="pk.email === r.picker">{{ pk.name }} · {{ pk.load }}</option>
                  <option value="__none__">{{ t('pulse.unassign') }}</option>
                </select>
                <button v-else class="lp-tap h-8 px-2.5 rounded-lg text-[11px] font-semibold text-amber-800 bg-amber-50 ring-1 ring-amber-200 hover:bg-amber-100 inline-flex items-center gap-1" :title="t('pulse.reassignHint')" @click="reassignFor = r.name"><Icon name="user" :size="11" />{{ t('pulse.reassign') }}</button>
              </template>
              <button v-if="responsible(r)" class="lp-tap h-8 px-2.5 rounded-lg text-[11px] font-semibold text-orange-800 bg-orange-50 ring-1 ring-orange-200 hover:bg-orange-100 inline-flex items-center gap-1 disabled:opacity-50" :disabled="busy === r.name" :title="t('pulse.nudgeHint') + ' ' + responsibleName(r)" @click="doNudge(r)"><Icon name="bell" :size="11" />{{ t('pulse.nudge') }}</button>
              <button v-if="r.reason" class="lp-tap h-8 px-2.5 rounded-lg text-[11px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50 inline-flex items-center gap-1 disabled:opacity-50" :disabled="busy === r.name" :title="t('pulse.snoozeHint')" @click="doSnooze(r)"><Icon name="circle-pause" :size="11" />{{ t('pulse.snooze') }}</button>
              <RouterLink v-if="r.stage === 'manifest'" :to="{ name: 'Manifest' }" class="lp-tap h-8 px-2.5 rounded-lg text-[11px] font-semibold text-sky-700 bg-sky-50 ring-1 ring-sky-200 hover:bg-sky-100 inline-flex items-center gap-1"><Icon name="send" :size="11" />{{ t('pulse.st_manifest') }}</RouterLink>
              <RouterLink v-else-if="r.stage === 'packed' || r.stage === 'label'" :to="{ name: 'PackStation' }" class="lp-tap h-8 px-2.5 rounded-lg text-[11px] font-semibold text-violet-700 bg-violet-50 ring-1 ring-violet-200 hover:bg-violet-100 inline-flex items-center gap-1"><Icon name="tag" :size="11" />{{ t('pulse.packStation') }}</RouterLink>
              <RouterLink :to="{ name: 'PickLists', query: { q: r.name } }" class="lp-tap h-8 px-2.5 rounded-lg text-[11px] font-semibold text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 inline-flex items-center gap-1"><Icon name="package" :size="11" />{{ t('pulse.openList') }}</RouterLink>
              <a v-if="r.doors.manifest.shipments && r.doors.manifest.shipments.length" :href="'/app/shipment/' + encodeURIComponent(r.doors.manifest.shipments[0])" target="_blank" rel="noopener" class="lp-tap h-8 px-2.5 rounded-lg text-[11px] font-semibold text-sky-700 bg-sky-50 ring-1 ring-sky-200 hover:bg-sky-100 inline-flex items-center gap-1"><Icon name="send" :size="11" />{{ r.doors.manifest.shipments[0] }}</a>
            </div>
          </div>
        </div>
      </article>
    </section>
    <div v-else-if="d" class="sh-empty rounded-2xl p-12 text-center">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center mb-3 bg-emerald-50 text-emerald-500"><Icon name="check-circle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ stuckOnly || stageF || whoF || q ? t('pulse.noneHere') : t('pulse.quiet') }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { RouterLink } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { local } from "@/lib/clock";
import { api, apiPost } from "@/lib/resource";
import { readStale, writeStale } from "@/lib/swr";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const STAGES = [
  { key: "to_pick", icon: "list-checks" }, { key: "picking", icon: "scan-barcode" }, { key: "sorting", icon: "layout-grid" },
  { key: "label", icon: "tag" }, { key: "packed", icon: "package-check" }, { key: "manifest", icon: "send" }, { key: "shipped", icon: "truck" },
];
const STAGE_CLS = {
  to_pick: "text-rose-700 bg-rose-50 ring-rose-200", picking: "text-amber-700 bg-amber-50 ring-amber-200", sorting: "text-sky-700 bg-sky-50 ring-sky-200",
  label: "text-violet-700 bg-violet-50 ring-violet-200", packed: "text-violet-700 bg-violet-50 ring-violet-200", manifest: "text-orange-700 bg-orange-50 ring-orange-200",
  shipped: "text-emerald-700 bg-emerald-50 ring-emerald-200",
};
const CFG_KEYS = ["startMin", "silentMin", "pickMin", "sortMin", "labelMin", "packMin", "manifestMin"];

const d = ref(null);
const cfg = ref(null);
const loading = ref(true);
const refreshing = ref(false);
const loadError = ref("");
const hours = ref(24);
const stageF = ref("");
const whoF = ref("");
const stuckOnly = ref(false);
const q = ref("");
const showCfg = ref(false);
const saving = ref(false);
const busy = ref("");
const meas = ref(null);
async function loadMeasure() {
  if (meas.value) return;
  try { meas.value = await api("pulse.measure", { days: 14 }); } catch (_) { meas.value = null; }
}
function useAll(pk) {
  if (!meas.value) return;
  for (const k of CFG_KEYS) { const v = meas.value.keys[k]; if (v && v.n && v[pk]) cfg.value[k] = v[pk]; }
}
const reassignFor = ref("");
// Who answers for the door a list stands at.
function responsible(r) {
  if (r.stage === "to_pick" || r.stage === "picking") return r.picker;
  if (r.stage === "sorting") return r.sorter || r.picker;
  if (r.stage === "packed") return r.packer;
  return r.createdBy;   // label and manifest are the dispatcher's
}
function responsibleName(r) {
  const u = responsible(r);
  if (u === r.picker) return r.pickerName; if (u === r.sorter) return r.sorterName; if (u === r.packer) return r.packerName;
  return r.createdByName;
}
async function doNudge(r) {
  const user = responsible(r); if (!user) return;
  const note = window.prompt(t("pulse.nudgePrompt").replace("{who}", responsibleName(r)), t("pulse.why_" + (r.reason || "start")).replace("{n}", mins(r.ageMin)));
  if (note === null) return;
  busy.value = r.name;
  try { await apiPost("pulse.nudge", { user, pick_list: r.name, note }); success(t("pulse.nudged"), responsibleName(r)); }
  catch (e) { warn(t("oclk.saveFail"), String(e?.message || e)); }
  busy.value = "";
}
async function doNudgePerson(p) {
  const note = window.prompt(t("pulse.nudgePrompt").replace("{who}", p.name), "");
  if (note === null) return;
  try { await apiPost("pulse.nudge", { user: p.user, pick_list: p.current || "", note }); success(t("pulse.nudged"), p.name); }
  catch (e) { warn(t("oclk.saveFail"), String(e?.message || e)); }
}
async function doReassign(r, picker) {
  if (!picker) { reassignFor.value = ""; return; }
  busy.value = r.name;
  try { await apiPost("pulse.reassign", { pick_list: r.name, picker: picker === "__none__" ? "" : picker }); success(t("pulse.reassigned"), r.name); reassignFor.value = ""; await load(); }
  catch (e) { warn(t("oclk.saveFail"), String(e?.message || e)); }
  busy.value = "";
}
async function doSnooze(r) {
  busy.value = r.name;
  try { const res = await apiPost("pulse.snooze", { pick_list: r.name, minutes: 30 }); success(t("pulse.snoozed"), `${r.name} · ${local(res.until).slice(11)}`); await load(); }
  catch (e) { warn(t("oclk.saveFail"), String(e?.message || e)); }
  busy.value = "";
}
let seq = 0;

const stuckTotal = computed(() => d.value ? Object.values(d.value.stages).reduce((a, s) => a + s.stuck, 0) : 0);
const activePeople = computed(() => d.value ? d.value.people.filter((p) => p.idleMin != null && p.idleMin <= 30).length : 0);
const shown = computed(() => {
  let rows = d.value?.rows || [];
  if (stageF.value) rows = rows.filter((r) => r.stage === stageF.value);
  if (whoF.value) rows = rows.filter((r) => [r.picker, r.sorter, r.packer, r.createdBy].includes(whoF.value));
  if (stuckOnly.value) rows = rows.filter((r) => r.reason);
  const qq = q.value.trim().toLowerCase();
  if (qq) rows = rows.filter((r) => r.name.toLowerCase().includes(qq) || (r.orderNames || []).some((o) => (o || "").toLowerCase().includes(qq)));
  return rows;
});

function mins(m) {
  m = Number(m || 0);
  if (m < 60) return m + t("oclk.mShort");
  if (m < 48 * 60) return Math.floor(m / 60) + t("oclk.hShort") + " " + String(m % 60).padStart(2, "0") + t("oclk.mShort");
  return Math.floor(m / 1440) + t("oclk.dShort");
}
function pct(n, of) { return of ? Math.min(100, Math.round(100 * n / of)) + "%" : "0%"; }
function initials(name) { const p = String(name || "?").trim().split(/\s+/); return ((p[0]?.[0] || "") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase(); }
function idleCls(p) {
  if (p.idleMin == null) return "bg-stone-50 text-stone-600 ring-stone-200";
  if (p.idleMin > (cfg.value?.silentMin || 10) * 3) return "bg-stone-50 text-stone-400 ring-stone-200";
  if (p.idleMin > (cfg.value?.silentMin || 10)) return "bg-amber-50 text-amber-800 ring-amber-200";
  return "bg-emerald-50 text-emerald-800 ring-emerald-200";
}
function peopleTitle(p) {
  return Object.entries(p.stations || {}).map(([s, n]) => `${t('pulse.stn_' + s, s)} ${n}`).join(" · ") + (p.lastAt ? ` · ${t('pulse.lastScan')} ${local(p.lastAt).slice(11)}` : "");
}
function doorCls(r, key) {
  const door = r.doors[key];
  if (r.stage === key && r.reason) return "bg-rose-500 text-white";
  if (r.stage === key) return "bg-emerald-500 text-white animate-pulse";
  if (door.skip) return "bg-stone-100 text-stone-300";
  if (door.done) return "bg-emerald-100 text-emerald-700";
  return "bg-white ring-1 ring-stone-300 text-stone-300";
}
function doorIcon(r, key) {
  const door = r.doors[key];
  if (r.stage === key && r.reason) return "alert-triangle";
  if (door.done && r.stage !== key) return "check";
  return STAGES.find((s) => s.key === key).icon;
}
function reasonText(r) {
  const key = "pulse.why_" + r.reason;
  const base = t(key);
  if (r.reason === "silent" && r.silentMin != null) return base.replace("{n}", mins(r.silentMin));
  return base.replace("{n}", mins(r.ageMin));
}

async function load() {
  const my = ++seq;
  if (!d.value) loading.value = true; else refreshing.value = true;
  try {
    const b = await api("pulse.board", { hours: hours.value });
    if (my !== seq) return;
    d.value = b; if (!cfg.value || !showCfg.value) cfg.value = { ...b.settings }; loadError.value = "";
    writeStale("pulse.board." + hours.value, b);
  } catch (e) {
    if (my !== seq) return;
    loadError.value = String(e?.message || e);
  }
  loading.value = false; refreshing.value = false;
}
async function saveCfg() {
  saving.value = true;
  try { cfg.value = await apiPost("pulse.save_settings", { payload: cfg.value }); success(t("oclk.saved"), ""); showCfg.value = false; load(); }
  catch (e) { warn(t("oclk.saveFail"), String(e?.message || e)); }
  saving.value = false;
}
onMounted(() => {
  const stale = readStale("pulse.board." + hours.value);
  if (stale) { d.value = stale; cfg.value = { ...stale.settings }; loading.value = false; }
  load();
});
const tick = setInterval(() => { if (document.visibilityState === "visible") load(); }, 30000);
onUnmounted(() => clearInterval(tick));
</script>
