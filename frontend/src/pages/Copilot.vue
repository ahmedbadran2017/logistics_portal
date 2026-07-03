<template>
  <div class="max-w-[900px] mx-auto h-[calc(100vh-52px)] flex flex-col animate-fade-in">
    <!-- Header -->
    <div class="px-5 sm:px-6 pt-5 pb-3 flex items-center gap-3 shrink-0">
      <span class="w-9 h-9 rounded-xl flex items-center justify-center text-white"
            style="background: linear-gradient(135deg, var(--accent-500), var(--accent-700))">
        <Icon name="sparkles" :size="18" />
      </span>
      <div class="flex-1 min-w-0">
        <h1 class="text-[16px] font-semibold text-stone-900 leading-tight">Logistics Copilot</h1>
        <div class="text-[11.5px] text-stone-500 flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Reads live floor data
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div ref="scroll" class="flex-1 overflow-y-auto px-5 sm:px-6 space-y-4 pb-4">
      <div v-for="(m, i) in messages" :key="i" class="flex gap-3" :class="m.role === 'user' ? 'justify-end' : ''">
        <span v-if="m.role === 'assistant'" class="w-7 h-7 rounded-lg flex items-center justify-center text-white flex-shrink-0 mt-0.5"
              style="background: linear-gradient(135deg, var(--accent-500), var(--accent-700))">
          <Icon name="sparkles" :size="14" />
        </span>
        <div :class="m.role === 'user'
          ? 'max-w-[75%] rounded-2xl rounded-ee-md px-3.5 py-2.5 text-white text-[13.5px] leading-relaxed'
          : 'max-w-[80%] bg-white ring-1 ring-stone-200/70 rounded-2xl rounded-es-md px-3.5 py-2.5 text-[13.5px] text-stone-700 leading-relaxed'"
          :style="m.role === 'user' ? { background: 'var(--accent-600)' } : {}"
          v-html="m.html" />
      </div>

      <!-- Suggested prompts -->
      <div v-if="messages.length <= 1" class="flex flex-wrap gap-2 ps-10">
        <button v-for="p in suggestions" :key="p" class="text-[12.5px] text-stone-600 bg-white ring-1 ring-stone-200/70 rounded-full px-3 py-1.5 hover:bg-stone-50 hover:ring-stone-300 transition-colors"
                @click="send(p)">
          {{ p }}
        </button>
      </div>
    </div>

    <!-- Composer -->
    <div class="shrink-0 px-5 sm:px-6 pb-5 pt-2">
      <form class="flex items-end gap-2 bg-white ring-1 ring-stone-200/70 rounded-2xl p-2 shadow-[0_1px_2px_rgba(0,0,0,0.03)] focus-within:ring-stone-300"
            @submit.prevent="send()">
        <input v-model="draft" placeholder="Ask about SLA, pickers, returns, cutoff…"
               class="flex-1 bg-transparent px-2.5 py-1.5 text-[13.5px] text-stone-900 placeholder:text-stone-400 focus:outline-none" />
        <button type="submit" class="w-9 h-9 rounded-xl flex items-center justify-center text-white disabled:opacity-40"
                style="background: var(--accent-600)" :disabled="!draft.trim()">
          <Icon name="send" :size="16" />
        </button>
      </form>
      <div class="text-[10.5px] text-stone-400 text-center mt-2">Copilot answers from today's floor data · a demo shell — wire to logistics_portal.api.audit.copilot_chat</div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from "vue";

const scroll = ref(null);
const draft = ref("");
const messages = ref([
  { role: "assistant", html: "Hi Eman 👋 I'm watching the floor live. Ask me what's slipping, who's ahead, or what's at risk before the 14:00 cutoff." },
]);

const suggestions = [
  "Why are we breaching SLA today?",
  "Who's my slowest picker after 4pm?",
  "Summarize today's returns",
  "What's at risk before cutoff?",
];

// Canned analytical answers grounded in the demo numbers.
const ANSWERS = [
  { m: /sla|breach/i, a: "There are <b>2 breached</b> and <b>4 at-risk</b> orders right now. The breaches sit in <b>Exception</b> — #240682 (Edghir hanane, 2nd failed Cathedis attempt) and #242638 (Mohmad Mohmad, Out of Stock 2h38m in Cosmetic zone, past the 14:00 cutoff). Same-day ship rate is <b>87%</b> vs the 95% target." },
  { m: /picker|slow|4pm|fatigue/i, a: "<b>Said</b> is trending down — his pick time rose ~22% after 16:00 three days running, likely fatigue on the SLOW zone. He's at <b>80% SLA</b> (rank 6). Marouane leads at 94%. Suggestion: rotate a second picker into SLOW after 16:00." },
  { m: /return/i, a: "Returns are led by SKU <b>CSM44021</b> (Sérum éclat) — <b>+40% this week</b>, all flagged <i>defective</i>. Worth a supplier quality check. Overall return rate ~2.4%." },
  { m: /cutoff|risk|ship/i, a: "Cutoff is <b>14:00</b> — currently <b>+07:44</b> past for today's window. <b>3 picked orders</b> aren't labeled yet for SH-000179 (manifest closes soon). 205 orders still to ship; 143/328 made the cutoff (44%)." },
];

function reply(text) {
  const hit = ANSWERS.find((x) => x.m.test(text));
  return hit ? hit.a : "I can break down SLA breaches, picker performance, returns, or the manifest cutoff — try one of those. (This is a demo shell; the production copilot reads live ERPNext data.)";
}

async function send(preset) {
  const text = (preset ?? draft.value).trim();
  if (!text) return;
  messages.value.push({ role: "user", html: escape(text) });
  draft.value = "";
  await scrollDown();
  setTimeout(async () => {
    messages.value.push({ role: "assistant", html: reply(text) });
    await scrollDown();
  }, 400);
}
function escape(s) {
  return s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}
async function scrollDown() {
  await nextTick();
  if (scroll.value) scroll.value.scrollTop = scroll.value.scrollHeight;
}
</script>
