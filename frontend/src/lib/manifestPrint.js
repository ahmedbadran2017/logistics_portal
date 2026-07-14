/**
 * Driver handover sheet — renders shipping.manifest_sheet into a printable
 * window (French labels: it's signed by the Cathedis driver in Casablanca).
 */
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

export function printManifestSheet(sheet) {
  const rows = (sheet.rows || []).map((r, i) => `
    <tr>
      <td class="n">${i + 1}</td>
      <td class="mono">${esc(r.awb) || "—"}</td>
      <td class="mono">${esc(r.order)}</td>
      <td>${esc(r.customer)}</td>
      <td class="mono">${esc(r.phone)}</td>
      <td>${esc(r.city)}</td>
      <td class="n">${Number(r.cod || 0).toFixed(2)}</td>
    </tr>`).join("");

  const html = `<!doctype html><html><head><meta charset="utf-8">
<title>${esc(sheet.shipment)} — Manifeste</title>
<style>
  * { box-sizing: border-box; font-family: -apple-system, "Segoe UI", Arial, sans-serif; }
  body { margin: 24px; color: #1c1917; font-size: 12px; }
  h1 { font-size: 16px; margin: 0 0 2px; }
  .sub { color: #57534e; margin-bottom: 14px; }
  .draft { color: #b45309; font-weight: 700; }
  table { width: 100%; border-collapse: collapse; }
  th, td { border: 1px solid #d6d3d1; padding: 5px 7px; text-align: left; }
  th { background: #f5f5f4; font-size: 10.5px; text-transform: uppercase; letter-spacing: .03em; }
  .n { text-align: right; font-variant-numeric: tabular-nums; }
  .mono { font-family: ui-monospace, Menlo, monospace; font-size: 11px; }
  tfoot td { font-weight: 700; background: #fafaf9; }
  .sig { display: flex; gap: 40px; margin-top: 36px; }
  .sig div { flex: 1; border-top: 1px solid #a8a29e; padding-top: 6px; color: #57534e; }
  @media print { body { margin: 10mm; } }
</style></head><body>
  <h1>Justyol — Manifeste ${esc(sheet.carrier)}</h1>
  <div class="sub">
    ${esc(sheet.shipment)} · ${esc(sheet.date)} ·
    ${sheet.count} colis · COD total ${Number(sheet.codTotal || 0).toFixed(2)} MAD
    ${sheet.status === "draft" ? '<span class="draft"> · BROUILLON — non remis</span>' : ""}
  </div>
  <table>
    <thead><tr>
      <th>#</th><th>AWB</th><th>Commande</th><th>Client</th>
      <th>Téléphone</th><th>Ville</th><th>COD (MAD)</th>
    </tr></thead>
    <tbody>${rows}</tbody>
    <tfoot><tr><td colspan="6">Total — ${sheet.count} colis</td>
      <td class="n">${Number(sheet.codTotal || 0).toFixed(2)}</td></tr></tfoot>
  </table>
  <div class="sig">
    <div>Signature chauffeur ${esc(sheet.carrier)}</div>
    <div>Signature entrepôt Justyol</div>
    <div>Date / heure</div>
  </div>
  <script>window.onload = function () { window.print(); };</` + `script>
</body></html>`;

  const w = window.open("", "_blank");
  if (!w) return false;
  w.document.write(html);
  w.document.close();
  return true;
}
