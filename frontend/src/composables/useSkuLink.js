import { useRouter } from "vue-router";

/**
 * One place to jump to the SKU Finder from any SKU or item_code shown in the UI.
 * The team works by SKU, so every code on screen should be clickable → open the
 * lookup for it (SkuLookup deep-links via ?q=, and its backend matches either
 * the real SKU or the item_code). Pass the real SKU when available, else the
 * item_code — both resolve.
 *
 *   const openSku = useSkuLink();
 *   <button @click.stop="openSku(item.realSku || item.sku)">…</button>
 */
export function useSkuLink() {
  const router = useRouter();
  return (q) => {
    const v = q == null ? "" : String(q).trim();
    if (v) router.push({ name: "SkuLookup", query: { q: v } });
  };
}
