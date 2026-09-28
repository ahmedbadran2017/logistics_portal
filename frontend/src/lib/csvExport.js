/**
 * CSV export for Excel.
 *
 * Two details decide whether the file opens as a spreadsheet or as one useless
 * column of text, and both are about Excel rather than about CSV:
 *
 *  - The UTF-8 BOM. Without it Excel reads the bytes as the local codepage and
 *    every Arabic customer name and French city arrives as mojibake. The three
 *    hand-rolled exports already in this app all learned that one.
 *  - The `sep=,` directive on the first line. Excel picks its delimiter from
 *    the machine's list separator, which on a French or Arabic Windows is a
 *    semicolon — so a comma file lands entirely in column A on exactly the
 *    machines this team uses. `sep=` overrides that. Excel consumes the line;
 *    it is visible only to tools that are not Excel, which is the right way
 *    round for a button labelled Excel.
 *
 * Real .xlsx would need a library; nothing here needs formatting or formulas,
 * so it would be a dependency bought for a file icon.
 */
function cell(v) {
  if (v === null || v === undefined) return '""';
  // A leading =, +, - or @ makes Excel treat the value as a formula, and
  // customer names are free text from the storefront. But nearly every row
  // here carries a phone starting with +212, and blanket-prefixing those
  // leaves a stray apostrophe in the cell on the Excel versions that do not
  // strip it on import. So: = and @ are never anything but a formula, while
  // + and - are only escaped when what follows is not a phone number.
  let s = String(v);
  const phoneish = /^[+\-][\d\s()\-.]+$/.test(s);
  if (/^[=@]/.test(s) || (/^[+\-]/.test(s) && !phoneish)) s = "'" + s;
  return '"' + s.replace(/"/g, '""') + '"';
}

/**
 * @param {string} filename  without extension
 * @param {Array<{key:string,label:string}>} columns
 * @param {Array<object>} rows
 * @returns {number} rows written
 */
export function downloadCsv(filename, columns, rows) {
  const body = [
    "sep=,",
    columns.map((c) => cell(c.label)).join(","),
    ...(rows || []).map((r) => columns.map((c) => cell(r[c.key])).join(",")),
  ].join("\r\n");   // CRLF: Excel on Windows keeps rows together

  const blob = new Blob(["﻿" + body], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Revoking immediately can cancel the download in Safari.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return (rows || []).length;
}

/** `handover-gaps-2026-09-28` — a date in the name, so two exports never
 *  overwrite each other in the Downloads folder. */
export function stampName(base) {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${base}-${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
