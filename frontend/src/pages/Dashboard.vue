<template>
  <PageContainer>
    <div class="max-w-[820px] mx-auto py-10">
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[var(--yol-v2-accent-50)] mb-4">
          <Icon name="truck" :size="32" class="text-[var(--yol-v2-accent-600)]" />
        </div>
        <h1 class="text-[28px] font-semibold text-stone-900 tracking-tight">Justyol Logistics Portal</h1>
        <p class="text-[13.5px] text-stone-500 mt-2 max-w-md mx-auto">
          Scaffold is up. Modules will land here as they're built — warehouse ops, inbound shipments,
          customs status, returns, and lead-time analytics.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div class="card">
          <div class="flex items-center gap-3 mb-2">
            <div class="w-9 h-9 rounded-lg bg-sky-50 text-sky-700 flex items-center justify-center">
              <Icon name="package" :size="18" />
            </div>
            <h3 class="text-[14px] font-semibold text-stone-900">Warehouse</h3>
          </div>
          <ul class="text-[12.5px] text-stone-600 space-y-1.5 pl-1">
            <li>· Receiving + putaway suggestions</li>
            <li>· Picking & packing waves</li>
            <li>· Cycle counts + variance</li>
            <li>· Inter-warehouse transfers</li>
            <li>· Bin map & utilization</li>
          </ul>
        </div>

        <div class="card">
          <div class="flex items-center gap-3 mb-2">
            <div class="w-9 h-9 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center">
              <Icon name="truck" :size="18" />
            </div>
            <h3 class="text-[14px] font-semibold text-stone-900">Logistics</h3>
          </div>
          <ul class="text-[12.5px] text-stone-600 space-y-1.5 pl-1">
            <li>· Inbound shipments tracker</li>
            <li>· Customs status (China / Turkey)</li>
            <li>· Lead-time analytics</li>
            <li>· Carrier performance</li>
            <li>· Document vault (BL, packing lists)</li>
          </ul>
        </div>

        <div class="card">
          <div class="flex items-center gap-3 mb-2">
            <div class="w-9 h-9 rounded-lg bg-rose-50 text-rose-700 flex items-center justify-center">
              <Icon name="rotate-cw" :size="18" />
            </div>
            <h3 class="text-[14px] font-semibold text-stone-900">Returns</h3>
          </div>
          <ul class="text-[12.5px] text-stone-600 space-y-1.5 pl-1">
            <li>· RMA tracking</li>
            <li>· Damage log + write-offs</li>
            <li>· Restocking queue</li>
          </ul>
        </div>

        <div class="card relative overflow-hidden">
          <div class="absolute -right-4 -top-4 w-24 h-24 rounded-full bg-emerald-100 opacity-50 blur-2xl pointer-events-none" />
          <div class="relative">
            <div class="flex items-center gap-3 mb-2">
              <div class="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
                <Icon name="check-circle" :size="18" />
              </div>
              <h3 class="text-[14px] font-semibold text-stone-900">Status</h3>
            </div>
            <p class="text-[12.5px] text-stone-700">
              Shell is wired to Frappe auth, role gate, and shared design tokens. Build the
              first module by adding a page under <code class="font-mono text-[11px] bg-stone-100 px-1 rounded">src/pages</code>
              and a route in <code class="font-mono text-[11px] bg-stone-100 px-1 rounded">router.js</code>.
            </p>
          </div>
        </div>
      </div>

      <div class="mt-8 text-center text-[11.5px] text-stone-400">
        v{{ version }} · scaffold ·
        <a href="https://github.com/ahmedbadran2017/logistics_portal" target="_blank" rel="noopener noreferrer" class="text-stone-500 hover:text-[var(--yol-v2-accent-700)]">repo</a>
      </div>
    </div>
  </PageContainer>
</template>

<script setup>
import PageContainer from "@/components/PageContainer.vue";
import Icon from "@/components/Icon.vue";

const version = "0.0.1";
</script>
