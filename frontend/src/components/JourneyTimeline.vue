<template>
  <!-- One parcel's whole story, newest first: the order arriving, the
       confirmation lane's decisions, the floor's milestones, the carrier's
       scans and the tracking team's notes. Same face on the order page and
       on Find a parcel. -->
  <div v-if="timeline && timeline.length">
    <div class="flex items-center justify-between mb-2">
      <div class="text-[11px] font-bold uppercase tracking-wide text-stone-400">{{ title || t('od.journeyEvents') }}</div>
      <span class="text-[10.5px] text-stone-400 tabular-nums">{{ timeline.length }}</span>
    </div>
    <ol class="relative ms-3 border-s-2 border-stone-200/80">
      <li v-for="(e, i) in timeline" :key="i" class="ms-5 pb-4 last:pb-0 relative">
        <span class="absolute top-0 w-7 h-7 rounded-full grid place-items-center ring-4 ring-white" style="inset-inline-start: -35px" :class="TL[e.kind]?.cls || TL.other.cls">
          <Icon :name="TL[e.kind]?.icon || 'info'" :size="13" />
        </span>
        <div class="flex items-center gap-2 flex-wrap min-h-[28px]">
          <span class="text-[12.5px] font-semibold" :class="i === 0 ? 'text-stone-900' : 'text-stone-700'">{{ t('od.tl_' + e.kind, e.kind) }}</span>
          <span v-if="i === 0" class="text-[10px] font-bold uppercase tracking-wide rounded-full px-1.5 py-0.5 bg-teal-50 text-teal-700 ring-1 ring-teal-200">{{ t('od.latest') }}</span>
          <span v-if="e.who" class="text-[10.5px] text-stone-500 inline-flex items-center gap-1"><Icon name="user" :size="10" />{{ e.who }}</span>
          <span class="ms-auto text-[10.5px] text-stone-400 tabular-nums" dir="ltr">{{ e.at.slice(5) }}</span>
        </div>
        <div v-if="e.text && !SAME_AS_TITLE.has(e.kind)" class="text-[11.5px] text-stone-500 mt-0.5 leading-snug" dir="auto">{{ tlText(e) }}</div>
      </li>
    </ol>
  </div>
</template>

<script setup>
import Icon from "@/components/ui/Icon.vue";
import { useI18n } from "@/composables/useI18n";
const { t } = useI18n();
defineProps({ timeline: { type: Array, default: () => [] }, title: { type: String, default: "" } });

// Every kind of thing that can happen to a parcel, with its own face.
const TL = {
  created: { icon: "plus", cls: "bg-stone-100 text-stone-500" },
  cfstatus: { icon: "phone", cls: "bg-sky-50 text-sky-600" },
  cfnote: { icon: "message-circle", cls: "bg-sky-50 text-sky-600" },
  confirmed: { icon: "check", cls: "bg-stone-100 text-stone-600" },
  picklist: { icon: "clipboard-check", cls: "bg-amber-50 text-amber-600" },
  closed: { icon: "package", cls: "bg-violet-50 text-violet-600" },
  manifest: { icon: "send", cls: "bg-sky-50 text-sky-600" },
  label: { icon: "tag", cls: "bg-violet-50 text-violet-600" },
  hub: { icon: "warehouse", cls: "bg-sky-50 text-sky-600" },
  ofd: { icon: "truck", cls: "bg-emerald-50 text-emerald-600" },
  appointment: { icon: "clock", cls: "bg-emerald-50 text-emerald-600" },
  unreachable: { icon: "phone-off", cls: "bg-amber-50 text-amber-600" },
  cancelled: { icon: "circle-x", cls: "bg-rose-50 text-rose-600" },
  returned: { icon: "rotate-ccw", cls: "bg-rose-50 text-rose-600" },
  delivered: { icon: "check-circle", cls: "bg-emerald-100 text-emerald-700" },
  mark: { icon: "user", cls: "bg-teal-50 text-teal-700" },
  rescue: { icon: "route", cls: "bg-teal-50 text-teal-700" },
  other: { icon: "info", cls: "bg-stone-100 text-stone-500" },
};
// Milestones read from documents carry no text of their own.
const SAME_AS_TITLE = new Set(["created", "confirmed", "picklist", "closed", "manifest"]);
// The confirmation lane writes its decisions as codes ("dna (attempt 2) — note");
// the reader gets the lane's own label for the code, in their language.
const CF_STATUS = { "Did not Answer": "cf.actDna", "Follow Up": "cf.actFollowup", "On Hold": "cf.actOnhold", "Cancelled": "cf.actCancelled",
  "Duplicated": "cf.tabDuplicated", "Pending": "cf.tabPending", "Not Delivered": "track.notdelivered", "Confirmed": "od.tl_confirmed" };
const CF_ACT = { confirm: "cf.actConfirm", dna: "cf.actDna", followup: "cf.actFollowup", onhold: "cf.actOnhold", cancel: "cf.actCancel", duplicate: "cf.actDuplicate" };
function tlText(e) {
  if (e.kind === "cfstatus") return CF_STATUS[e.text] ? t(CF_STATUS[e.text], e.text) : e.text;
  if (e.kind !== "cfnote") return e.text;
  const m = /^([a-z]+)(.*)$/.exec(e.text || "");
  return m && CF_ACT[m[1]] ? t(CF_ACT[m[1]]) + m[2] : e.text;
}
</script>
