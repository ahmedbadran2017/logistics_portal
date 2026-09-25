/**
 * Carrier return handover sheet — renders returns.return_sheet into a
 * printable window. French, like the outbound manifest: it is signed by the
 * Cathedis driver at the door.
 *
 * The sheet exists for the argument, not the record. A parcel the return
 * expected and the van did not carry prints on its own line, in bold, with a
 * count at the top — so the shortage is settled while the driver is still
 * standing there rather than discovered on the shelf a week later.
 */
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

export function printReturnSheet(sheet) {
  const rows = (sheet.rows || []).map((r, i) => {
    const short = Number(r.missing || 0) > 0;
    const lines = (r.lines || []).map((l) => {
      const lm = Number(l.missing || 0) > 0;
      return `<div class="ln${lm ? " lnshort" : ""}">`
        + `<span class="mono">${esc(l.sku)}</span> ${esc(l.name)}`
        + ` — ${Number(l.actual || 0)}/${Number(l.ordered || 0)}`
        + (lm ? ` <b>(manque ${Number(l.missing)})</b>` : "")
        + `</div>`;
    }).join("");
    return `
    <tr class="${short ? "short" : ""}">
      <td class="n">${i + 1}</td>
      <td class="mono">${esc(r.awb) || "—"}</td>
      <td class="mono">${esc(r.order) || esc(r.dn) || "—"}</td>
      <td>${esc(r.customer) || "—"}<div class="sub">${esc(r.city)}</div></td>
      <td class="lines">${lines}</td>
      <td class="n">${Number(r.ordered || 0)}</td>
      <td class="n">${Number(r.actual || 0)}</td>
      <td class="n ${short ? "bad" : ""}">${Number(r.missing || 0) || "—"}</td>
      <td class="box"></td>
    </tr>`;
  }).join("");

  const missing = Number(sheet.missing || 0);
  const html = `<!doctype html><html><head><meta charset="utf-8">
<title>${esc(sheet.batch)} — Retours</title>
<style>
  * { box-sizing: border-box; font-family: -apple-system, "Segoe UI", Arial, sans-serif; }
  body { margin: 24px; color: #1c1917; font-size: 12px; }
  h1 { font-size: 16px; margin: 0 0 2px; }
  .sub { color: #57534e; font-size: 10.5px; }
  .head { color: #57534e; margin-bottom: 6px; }
  .draft { color: #b45309; font-weight: 700; }
  .alert { margin: 8px 0 14px; padding: 7px 10px; border: 1.5px solid #b91c1c;
           color: #b91c1c; font-weight: 700; border-radius: 4px; }
  .ok { margin: 8px 0 14px; padding: 7px 10px; border: 1px solid #a8a29e;
        color: #44403c; border-radius: 4px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { border: 1px solid #d6d3d1; padding: 5px 7px; text-align: left;
           vertical-align: top; }
  th { background: #f5f5f4; font-size: 10.5px; text-transform: uppercase; letter-spacing: .03em; }
  .n { text-align: right; font-variant-numeric: tabular-nums; }
  .mono { font-family: ui-monospace, Menlo, monospace; font-size: 11px; }
  .lines { font-size: 10.5px; color: #44403c; }
  .ln { padding: 1px 0; }
  .lnshort { color: #b91c1c; }
  tr.short { background: #fef2f2; }
  .bad { color: #b91c1c; font-weight: 700; }
  .box { width: 26px; }
  tfoot td { font-weight: 700; background: #fafaf9; }
  .sig { display: flex; gap: 40px; margin-top: 36px; }
  .sig div { flex: 1; border-top: 1px solid #a8a29e; padding-top: 6px; color: #57534e; }
  @media print { body { margin: 10mm; } tr { page-break-inside: avoid; } }
</style></head><body>
  <h1>Justyol — Retours ${esc(sheet.carrier)}</h1>
  <div class="head">
    ${esc(sheet.batch)} · ${esc(sheet.date)} ·
    ${sheet.parcels} colis · ${Number(sheet.actual || 0)}/${Number(sheet.ordered || 0)} pièces
    ${sheet.status === "draft" ? '<span class="draft"> · EN COURS — réception non clôturée</span>' : ""}
  </div>
  ${missing > 0
    ? `<div class="alert">${missing} pièce(s) attendue(s) et non reçue(s) — à signer avec le chauffeur avant son départ.</div>`
    : `<div class="ok">Aucun écart : tout ce qui était attendu a été scanné.</div>`}
  <table>
    <thead><tr>
      <th>#</th><th>AWB</th><th>Commande</th><th>Client / Ville</th>
      <th>Articles (reçu / attendu)</th>
      <th>Att.</th><th>Reçu</th><th>Manque</th><th>✓</th>
    </tr></thead>
    <tbody>${rows}</tbody>
    <tfoot><tr>
      <td colspan="5">Total — ${sheet.parcels} colis</td>
      <td class="n">${Number(sheet.ordered || 0)}</td>
      <td class="n">${Number(sheet.actual || 0)}</td>
      <td class="n ${missing ? "bad" : ""}">${missing || "—"}</td>
      <td></td>
    </tr></tfoot>
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
