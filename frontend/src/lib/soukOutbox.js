// The buyer's outbox. Derb Omar's connection drops between two stalls; a
// purchase entered then must not be lost, and must not be made twice when
// the phone retries. So a write the buyer makes is a JOB kept on the phone
// (IndexedDB, photos included as blobs) until the server has it:
//
//   basket    create_basket → each product's ref photo → receipt photo →
//             finish_basket until the PO exists (one stall, N products)
//   buy       create_buy → ref photo → receipt photo → finish_buy until 'bought'
//   rebuy     create_rebuy → receipt photo
//   transport set_transport (+ the taxi receipt photo)
//   voucher   voucher photo → set_voucher
//   photo     one upload_photo (a receipt added later from the custody screen)
//
// Every job carries a clientKey (a uuid made when the buyer pressed the
// button). The server keeps it on the product / PO and answers a retry with
// the record it already made — a lost answer never becomes a second PO and a
// second deduction from the custody. Each step's result is saved on the job
// before the next step runs, so a retry resumes where it stopped.
//
// A job that the SERVER refused (validation: "custody left is 300 MAD") is
// not retried by itself: it is marked failed and shown, the buyer retries or
// discards it. Only network-shaped failures retry on their own.

import { reactive } from "vue";
import { apiPost } from "@/lib/resource";
import { postPhoto } from "@/lib/soukPhoto";

const DB = "lp-souk-outbox";
const STORE = "jobs";

export const outbox = reactive({
  online: typeof navigator === "undefined" ? true : navigator.onLine !== false,
  jobs: [],          // [{id, kind, label, created, tries, error, failed, state}]
  flushing: false,
  ready: false,
});

let dbp = null;
function db() {
  if (dbp) return dbp;
  dbp = new Promise((ok, ko) => {
    if (typeof indexedDB === "undefined") { ko(new Error("no IndexedDB")); return; }
    const r = indexedDB.open(DB, 1);
    r.onupgradeneeded = () => r.result.createObjectStore(STORE, { keyPath: "id" });
    r.onsuccess = () => ok(r.result);
    r.onerror = () => ko(r.error);
  });
  return dbp;
}

async function tx(mode, fn) {
  const d = await db();
  return new Promise((ok, ko) => {
    const t = d.transaction(STORE, mode);
    const st = t.objectStore(STORE);
    const out = fn(st);
    t.oncomplete = () => ok(out && "result" in out ? out.result : undefined);
    t.onerror = () => ko(t.error);
    t.onabort = () => ko(t.error);
  });
}

const put = (job) => tx("readwrite", (st) => st.put(job));
const del = (id) => tx("readwrite", (st) => st.delete(id));
const all = () => tx("readonly", (st) => st.getAll());

export function newKey() {
  try { if (crypto && crypto.randomUUID) return crypto.randomUUID(); } catch (_) { /* old webview */ }
  return "k" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 12);
}

function summary(j) {
  return { id: j.id, kind: j.kind, label: j.label || "", created: j.created, tries: j.tries || 0,
           error: j.error || "", failed: !!j.failed, state: { ...(j.state || {}) } };
}

async function refresh() {
  try {
    const rows = await all();
    rows.sort((a, b) => a.created - b.created);
    outbox.jobs = rows.map(summary);
  } catch (_) {
    outbox.jobs = [];
  }
  outbox.ready = true;
}

/** Network-shaped: the request may never have reached the server, or its
 *  answer was lost. Safe to retry because every job is keyed. */
export function isTransient(e) {
  if (!e) return false;
  if (e instanceof TypeError) return true;                    // fetch: Failed to fetch / Load failed
  const m = String(e.message || e);
  return /(→|HTTP)\s*(0|408|429|500|502|503|504)\b/.test(m) || /network|timed? ?out|aborted/i.test(m)
    || (typeof navigator !== "undefined" && navigator.onLine === false);
}

const listeners = new Set();
/** fn(job, result) after a job finished — the page that queued it updates. */
export function onDone(fn) { listeners.add(fn); return () => listeners.delete(fn); }

// ── the steps ────────────────────────────────────────────────────────────────

async function save(job) { await put(job); }

async function photo(job, step, kind, target, blob) {
  if (!blob || (job.state || {})[step]) return;
  await postPhoto("upload_photo", { kind, target }, blob);
  job.state = { ...(job.state || {}), [step]: 1 };
  await save(job);
}

const RUN = {
  async basket(job) {
    const key = job.payload.clientKey;
    if (!(job.state || {}).name) {
      const r = await apiPost("souk.create_basket", { payload: JSON.stringify(job.payload) });
      job.state = { ...(job.state || {}), name: key, po: r.po || "", cards: (r.cards || []).map((c) => c.name),
                    result: r.pending ? null : r };
      await save(job);
    }
    const cards = job.state.cards || [];
    for (let i = 0; i < (job.refs || []).length; i++) {
      if (cards[i]) await photo(job, "ref" + i, "ref", cards[i], job.refs[i]);
    }
    if (!job.state.refs) { job.state = { ...job.state, refs: 1 }; await save(job); }
    // On the PO when it exists; else on the first card, which hands it to
    // the PO when finish_basket makes it.
    const rt = job.state.po || cards[0];
    if (rt) await photo(job, "receipt", "receipt", rt, job.receipt);
    if (job.state.result) return job.state.result;
    // Each product's Shopify Draft and items take a few seconds; then the PO.
    for (let i = 0; i < 15; i++) {
      const r = await apiPost("souk.finish_basket", { key });
      if (!r.pending) return r;
      if (r.error) {
        const e = new Error(r.error);
        e.pending = key;
        throw e;
      }
      await new Promise((ok) => setTimeout(ok, 4000));
    }
    const e = new Error("pending");
    e.wait = true;
    throw e;
  },
  async buy(job) {
    const st = job.state || {};
    if (!st.name) {
      const r = await apiPost("souk.create_buy", { payload: JSON.stringify(job.payload) });
      job.state = { ...st, name: r.name, result: r.pending ? null : r };
      await save(job);
    }
    await photo(job, "ref", "ref", job.state.name, job.ref);
    await photo(job, "receipt", "receipt", job.state.name, job.receipt);
    if (job.state.result) return job.state.result;
    // The Shopify Draft and its items take a few seconds; then the PO.
    for (let i = 0; i < 12; i++) {
      const r = await apiPost("souk.finish_buy", { name: job.state.name });
      if (!r.pending) return r;
      if (r.error) {
        const e = new Error(r.error);
        e.pending = job.state.name;
        throw e;
      }
      await new Promise((ok) => setTimeout(ok, 4000));
    }
    const e = new Error("pending");
    e.wait = true;
    throw e;
  },
  async rebuy(job) {
    if (!(job.state || {}).po) {
      const r = await apiPost("souk.create_rebuy", { payload: JSON.stringify(job.payload) });
      job.state = { ...(job.state || {}), po: r.po, result: r };
      await save(job);
    }
    await photo(job, "receipt", "receipt", job.state.po, job.receipt);
    return job.state.result;
  },
  async transport(job) {
    if (!(job.state || {}).amount) {
      const r = await apiPost("souk.set_transport", { trip: job.trip, amount: job.amount });
      job.state = { ...(job.state || {}), amount: 1, result: r };
      await save(job);
    }
    await photo(job, "photo", "transport", job.trip, job.receipt);
    return job.state.result;
  },
  async voucher(job) {
    let url = (job.state || {}).url || "";
    if (job.photo && !url) {
      const r = await postPhoto("upload_photo", { kind: "voucher", target: job.po }, job.photo);
      url = (r && r.url) || "";
      job.state = { ...(job.state || {}), url: url || "-" };
      await save(job);
    }
    return apiPost("souk.set_voucher", { po: job.po, phone: job.phone, stall_name: job.stallName || "",
                                         photo: url === "-" ? "" : url });
  },
  async photo(job) {
    return postPhoto("upload_photo", { kind: job.photoKind, target: job.target }, job.blob);
  },
};

// ── public ───────────────────────────────────────────────────────────────────

/**
 * Keep a job and try it now. Resolves with the server's answer when it went
 * through at once, or with {queued: true} when it is waiting for the line.
 * Rejects only when the server refused it (the caller shows why).
 */
export async function enqueue(job) {
  const j = { id: job.id || newKey(), created: Date.now(), tries: 0, state: {}, ...job };
  let stored = true;
  try { await put(j); } catch (_) { stored = false; }   // private mode: run it live, unkept
  await refresh();
  return runOne(j, stored);
}

// A job runs once at a time: enqueue() runs it at once while flush() may
// pick the same row from IndexedDB — two create_buy at the same instant.
const running = new Set();

async function runOne(j, stored = true) {
  if (running.has(j.id)) return { queued: true };
  running.add(j.id);
  try {
    return await runOneInner(j, stored);
  } finally {
    running.delete(j.id);
  }
}

async function runOneInner(j, stored) {
  try {
    j.tries = (j.tries || 0) + 1;
    const res = await RUN[j.kind](j);
    if (stored) await del(j.id).catch(() => {});
    await refresh();
    for (const fn of listeners) { try { fn(j, res); } catch (_) { /* a page gone */ } }
    return res;
  } catch (e) {
    if (e && e.wait) {
      // Still being created on Shopify — not an error, just not done.
      j.error = "";
      if (stored) await put(j).catch(() => {});
      await refresh();
      return { queued: true, pending: j.state && j.state.name };
    }
    if (isTransient(e) && stored) {
      j.error = String(e.message || e);
      await put(j).catch(() => {});
      await refresh();
      return { queued: true };
    }
    if (stored) {
      j.failed = true;
      j.error = String((e && e.message) || e);
      await put(j).catch(() => {});
      await refresh();
    }
    throw e;
  }
}

let flushP = null;
/** Send every waiting job, oldest first (a buy before its receipt). */
export function flush() {
  if (flushP) return flushP;
  flushP = (async () => {
    outbox.flushing = true;
    try {
      let rows = [];
      try { rows = await all(); } catch (_) { return; }
      rows.sort((a, b) => a.created - b.created);
      for (const j of rows) {
        if (j.failed) continue;
        try { await runOne(j); } catch (_) { /* marked failed, keep going */ }
        if (typeof navigator !== "undefined" && navigator.onLine === false) break;
      }
    } finally {
      outbox.flushing = false;
      flushP = null;
    }
  })();
  return flushP;
}

/** Retry a job the server refused (after fixing what it said). */
export async function retry(id) {
  const rows = await all();
  const j = rows.find((x) => x.id === id);
  if (!j) return null;
  j.failed = false;
  j.error = "";
  await put(j);
  await refresh();
  return runOne(j);
}

export async function discard(id) {
  await del(id).catch(() => {});
  await refresh();
}

let started = false;
/** Once per app: listen for the line coming back, and sweep now and then. */
export function startOutbox() {
  if (started || typeof window === "undefined") return;
  started = true;
  const go = () => { outbox.online = navigator.onLine !== false; if (outbox.online) flush(); };
  window.addEventListener("online", go);
  window.addEventListener("offline", () => { outbox.online = false; });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") go(); });
  setInterval(() => { if (outbox.jobs.some((j) => !j.failed)) go(); }, 30000);
  refresh().then(go);
}
