<template>
  <!-- A server refusal, explained in French (lib/explainError). Mounted once,
       next to the toast layer; useToast diverts server errors here. -->
  <Teleport to="body">
    <transition name="errpop">
      <div v-if="cur" class="fixed inset-0 z-[210] flex items-center justify-center p-4 bg-black/45" @click.self="close">
        <div class="w-full max-w-[520px] rounded-2xl bg-white dark:bg-stone-900 ring-1 ring-stone-200 dark:ring-stone-700 shadow-2xl overflow-hidden"
             role="alertdialog" aria-modal="true" lang="fr">
          <div class="px-5 pt-5 pb-4 flex items-start gap-3.5" :class="tone.head">
            <span class="w-11 h-11 rounded-full bg-white dark:bg-stone-900 flex items-center justify-center shrink-0">
              <Icon :name="cur.icon" :size="22" :class="tone.icon" />
            </span>
            <div class="min-w-0">
              <div class="text-[16px] font-bold leading-snug" :class="tone.title">{{ cur.title }}</div>
              <div v-if="cur.context" class="text-[11.5px] mt-0.5 opacity-70" :class="tone.title">{{ cur.context }}</div>
            </div>
          </div>

          <div class="px-5 pt-4 pb-2 space-y-3.5">
            <p class="text-[13.5px] text-stone-700 dark:text-stone-200 leading-relaxed">{{ cur.what }}</p>

            <!-- Where the item really is: the part the English message never said. -->
            <div v-if="cur.stock" class="rounded-xl bg-stone-50 dark:bg-stone-800 ring-1 ring-stone-200/70 dark:ring-stone-700 p-3">
              <div v-if="loadingStock" class="h-10 rounded-lg bg-stone-100 dark:bg-stone-700 animate-pulse" />
              <template v-else-if="where && where.ok">
                <div class="flex items-center gap-3">
                  <img v-if="where.image" :src="where.image" alt="" class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 shrink-0" />
                  <div class="min-w-0">
                    <div class="text-[12.5px] font-semibold text-stone-900 dark:text-stone-100 truncate">{{ where.name }}</div>
                    <div class="font-mono text-[11px] text-stone-500">{{ where.sku || where.itemCode }}</div>
                  </div>
                  <div class="ms-auto text-end shrink-0">
                    <div class="text-[18px] font-extrabold tabular-nums" :class="where.freeToPick ? 'text-emerald-600' : 'text-rose-600'">{{ where.freeToPick }}</div>
                    <div class="text-[10px] uppercase font-semibold text-stone-400">libre au picking</div>
                  </div>
                </div>
                <div class="text-[11px] font-semibold text-stone-400 mt-3 mb-1.5">Où il est</div>
                <div v-if="where.bins.length" class="flex flex-wrap gap-1.5">
                  <span v-for="b in where.bins" :key="b.warehouse"
                        class="text-[11.5px] font-semibold rounded-lg px-2 py-1 tabular-nums"
                        :class="b.pickable ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200' : 'bg-amber-50 text-amber-800 ring-1 ring-amber-200'">
                    {{ b.bin }} · {{ b.qty }}<span class="font-normal opacity-70"> · {{ b.pickable ? 'picking' : 'réserve' }}</span>
                  </span>
                </div>
                <div v-else class="text-[12px] font-semibold text-rose-700">Aucune pièce nulle part dans le stock.</div>
                <p class="text-[12px] mt-2.5 font-medium" :class="verdict.cls">{{ verdict.text }}</p>
              </template>
            </div>

            <div>
              <div class="text-[11px] font-semibold text-stone-400 mb-1.5">Quoi faire</div>
              <ol class="space-y-2">
                <li v-for="(s, i) in cur.steps" :key="i" class="flex items-start gap-2.5">
                  <span class="w-[22px] h-[22px] rounded-full bg-sky-50 text-sky-700 text-[11.5px] font-bold flex items-center justify-center shrink-0 mt-px">{{ i + 1 }}</span>
                  <span class="text-[13.5px] text-stone-800 dark:text-stone-200 leading-snug">{{ s }}</span>
                </li>
              </ol>
            </div>
          </div>

          <div class="px-5 pt-3 pb-4 flex flex-wrap gap-2">
            <button v-if="moveAction" class="flex-1 min-w-[200px] h-11 rounded-xl text-[13.5px] font-bold text-white bg-sky-600 hover:bg-sky-700 flex items-center justify-center gap-2"
                    @click="go(moveAction.route)">
              <Icon name="move" :size="16" /> {{ moveAction.label }}
            </button>
            <button v-else-if="cur.action" class="flex-1 min-w-[200px] h-11 rounded-xl text-[13.5px] font-bold text-white bg-sky-600 hover:bg-sky-700"
                    @click="go(cur.action.route)">{{ cur.action.label }}</button>
            <button class="h-11 px-5 rounded-xl text-[13.5px] font-semibold text-stone-700 dark:text-stone-200 bg-white dark:bg-stone-800 ring-1 ring-stone-200 dark:ring-stone-700 hover:bg-stone-50"
                    :class="moveAction || cur.action ? '' : 'flex-1'" @click="close">Fermer</button>
          </div>

          <div class="border-t border-stone-100 dark:border-stone-800 px-5 py-2.5 flex items-center gap-2">
            <Icon name="file-text" :size="13" class="text-stone-400 shrink-0" />
            <span class="font-mono text-[10.5px] text-stone-400 truncate flex-1 min-w-0" :title="cur.raw" dir="ltr">{{ cur.raw }}</span>
            <button class="h-7 px-2.5 rounded-lg text-[11px] font-semibold text-stone-600 dark:text-stone-300 ring-1 ring-stone-200 dark:ring-stone-700 hover:bg-stone-50 dark:hover:bg-stone-800 flex items-center gap-1 shrink-0"
                    @click="copy">
              <Icon :name="copied ? 'check' : 'copy'" :size="12" /> {{ copied ? 'Copié' : 'Copier pour le manager' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import Icon from "./Icon.vue";
import { api } from "@/lib/resource";
import { useErrorPopup } from "@/composables/useErrorPopup";

const { current: cur, close } = useErrorPopup();
const router = useRouter();

const TONES = {
  warn: { head: "bg-amber-50 dark:bg-amber-950/40", icon: "text-amber-600", title: "text-amber-900 dark:text-amber-200" },
  info: { head: "bg-sky-50 dark:bg-sky-950/40", icon: "text-sky-600", title: "text-sky-900 dark:text-sky-200" },
};
const tone = computed(() => TONES[cur.value?.tone] || TONES.warn);

const where = ref(null);
const loadingStock = ref(false);
watch(cur, async (c) => {
  where.value = null;
  copied.value = false;
  if (!c || !c.stock) return;
  loadingStock.value = true;
  try { where.value = await api("inventory.where_is", { code: c.stock }); }
  catch { where.value = null; }
  finally { loadingStock.value = false; }
});

// The reserve bin holding the most: where a move should come from.
const reserve = computed(() => (where.value?.bins || []).filter((b) => !b.pickable && b.movable && b.qty > 0)
  .sort((a, b) => b.qty - a.qty)[0] || null);

const verdict = computed(() => {
  const w = where.value;
  if (!w || !w.ok) return { text: "", cls: "" };
  if (w.freeToPick > 0) return { text: "Le stock est revenu entre-temps : refais la pick list maintenant.", cls: "text-emerald-700" };
  if (reserve.value) return { text: `Rien de libre au picking, mais ${reserve.value.qty} en ${reserve.value.bin} : déplace des pièces vers une étagère.`, cls: "text-amber-800" };
  if ((w.bins || []).length) return { text: "Les pièces au picking sont déjà prises par d'autres commandes ou pick lists.", cls: "text-amber-800" };
  return { text: "Rupture réelle : préviens la confirmation, la commande doit attendre.", cls: "text-rose-700" };
});

const moveAction = computed(() => {
  const w = where.value;
  if (!w || !w.ok || w.freeToPick > 0 || !reserve.value) return null;
  return { label: "Déplacer le stock",
           route: { name: "MoveStock", query: { item: w.sku || w.itemCode, from: reserve.value.warehouse } } };
});

function go(route) {
  close();
  router.push(route).catch(() => {});
}

const copied = ref(false);
async function copy() {
  const c = cur.value;
  if (!c) return;
  const text = [c.context, c.raw, c.method, c.at].filter(Boolean).join("\n");
  try { await navigator.clipboard.writeText(text); copied.value = true; } catch { copied.value = false; }
}

function onKey(e) { if (e.key === "Escape" && cur.value) close(); }
onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
</script>

<style scoped>
.errpop-enter-from, .errpop-leave-to { opacity: 0; }
.errpop-enter-active, .errpop-leave-active { transition: opacity 0.15s ease; }
</style>
