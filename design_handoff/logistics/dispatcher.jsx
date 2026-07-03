/* global React, I, Badge, Avatar, Button, IconButton, StageBadge, SlaBadge, Panel, CapacityBar */
const { useState, useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// DISPATCHER — Assignment board. Unassigned orders → picker columns.
// ─────────────────────────────────────────────────────────────────────
function STOCK(o) {
  if (o.stage === "oos") return "oos";
  if (o.items >= 4) return "partial";
  return "instock";
}

function Dispatcher({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const pickers = D.TEAM.filter((p) => p.role === "picker");

  // seed loads from orders already assigned + in-progress
  const baseLoad = useMemo(() => {
    const m = {};
    pickers.forEach((p) => { m[p.id] = D.ORDERS.filter((o) => o.picker === p.id && ["picking","picked"].includes(o.stage)).length; });
    return m;
  }, []);

  const [assign, setAssign] = useState({});   // orderNo -> pickerId
  const [sel, setSel] = useState(new Set());
  const capacity = 12;

  const unassigned = D.ORDERS.filter((o) => o.stage === "pending" && !assign[o.no]);
  const loadFor = (pid) => baseLoad[pid] + Object.values(assign).filter((x) => x === pid).length;

  function toggle(no) {
    setSel((s) => { const n = new Set(s); n.has(no) ? n.delete(no) : n.add(no); return n; });
  }
  function doAssign(pid) {
    if (sel.size === 0) return;
    setAssign((a) => { const n = { ...a }; sel.forEach((no) => (n[no] = pid)); return n; });
    onToast?.({ type: "success", text: `${sel.size} ${t("c.orders")} → ${D.byId(pid).short}` });
    setSel(new Set());
  }
  function autoBalance() {
    if (unassigned.length === 0) return;
    setAssign((a) => {
      const n = { ...a };
      const live = {}; pickers.forEach((p) => { live[p.id] = loadFor(p.id); });
      unassigned.forEach((o) => { const pid = pickers.slice().sort((x, y) => live[x.id] - live[y.id])[0].id; n[o.no] = pid; live[pid]++; });
      return n;
    });
    onToast?.({ type: "success", text: `${unassigned.length} ${t("c.orders")} auto-balanced across ${pickers.length} pickers` });
    setSel(new Set());
  }
  function assignedTo(pid) {
    return Object.entries(assign).filter(([, p]) => p === pid).map(([no]) => D.ORDERS.find((o) => o.no === no)).filter(Boolean);
  }

  return (
    <div className="h-full flex flex-col animate-fade-in">
      {/* header */}
      <div className="px-6 py-4 border-b border-stone-200/60 flex items-center justify-between gap-3 flex-wrap bg-white/40">
        <div>
          <h1 className="text-[19px] font-semibold text-stone-900 tracking-[-0.01em]">{t("dp.title")}</h1>
          <p className="text-[12.5px] text-stone-500 mt-0.5">{t("dp.balance")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="md" icon={I.Zap} onClick={autoBalance}>Auto-balance</Button>
          <Button variant="secondary" size="md" icon={I.Layers}>{t("dp.combined")}</Button>
          <Badge tone="neutral" dot>{unassigned.length} {t("c.unassigned").toLowerCase()}</Badge>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[380px_1fr] min-h-0">
        {/* LEFT — ready to assign */}
        <div className="border-e border-stone-200/60 flex flex-col min-h-0 bg-white/30">
          <div className="px-4 py-2.5 flex items-center justify-between border-b border-stone-100">
            <span className="text-[12px] font-semibold text-stone-700">{t("dp.ready")}</span>
            {sel.size > 0 && (
              <button onClick={() => setSel(new Set())} className="text-[11.5px] text-stone-500 hover:text-stone-800">{sel.size} selected · clear</button>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {unassigned.map((o) => {
              const stk = STOCK(o);
              const picked = sel.has(o.no);
              const stkTone = { instock: "green", partial: "yellow", oos: "red" }[stk];
              const stkLabel = { instock: t("dp.instock"), partial: t("dp.partial"), oos: t("dp.oos") }[stk];
              return (
                <button key={o.no} onClick={() => toggle(o.no)}
                  className={`w-full text-start rounded-xl ring-1 p-3 transition-all ${picked ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/50 shadow-[0_2px_12px_-4px_var(--accent-200)]" : "ring-stone-200/70 bg-white hover:ring-stone-300"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`w-4 h-4 rounded-md flex items-center justify-center ring-1 ${picked ? "bg-[var(--accent-600)] ring-[var(--accent-600)] text-white" : "ring-stone-300 bg-white"}`}>
                        {picked && <I.Check width={11} height={11} />}
                      </span>
                      <span className="font-mono text-[12px] font-semibold text-stone-900">{o.no}</span>
                    </div>
                    <Badge tone={stkTone} dot>{stkLabel}</Badge>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[12.5px] text-stone-700 truncate">{o.customer}</span>
                    <span className="text-[12px] font-semibold text-stone-900 tabular-nums">{window.fmtMAD(o.total)} <span className="text-[10px] text-stone-400">MAD</span></span>
                  </div>
                  <div className="mt-1.5 flex items-center gap-2 text-[11px] text-stone-500">
                    <span className="truncate">{o.zone}</span><span className="text-stone-300">·</span><span className="tabular-nums">{o.items} {t("c.items")}</span>
                    <SlaBadge sla={o.sla} size="sm" />
                  </div>
                </button>
              );
            })}
            {unassigned.length === 0 && <div className="text-center text-[12.5px] text-stone-400 py-12">All orders assigned ✓</div>}
          </div>
          {/* assign bar */}
          {sel.size > 0 && (
            <div className="border-t border-stone-200/70 bg-white p-3 animate-fade-in">
              <div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400 mb-1.5">{t("dp.assignTo")}</div>
              <div className="grid grid-cols-2 gap-1.5">
                {pickers.map((p) => (
                  <button key={p.id} onClick={() => doAssign(p.id)}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-lg ring-1 ring-stone-200 hover:ring-[var(--accent-400)] hover:bg-[var(--accent-50)]/40 transition-all">
                    <Avatar name={p.name} size={22} />
                    <span className="text-[12px] font-medium text-stone-800 truncate">{p.short}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT — picker columns */}
        <div className="overflow-x-auto p-4">
          <div className="flex gap-3 min-w-min h-full">
            {pickers.map((p) => {
              const load = loadFor(p.id);
              const fresh = assignedTo(p.id);
              const inProg = D.ORDERS.filter((o) => o.picker === p.id && ["picking","picked"].includes(o.stage));
              return (
                <div key={p.id} className="w-[250px] flex-shrink-0 flex flex-col bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
                  <div className="px-3 py-2.5 border-b border-stone-100">
                    <div className="flex items-center gap-2">
                      <Avatar name={p.name} size={28} />
                      <div className="min-w-0 flex-1 leading-tight">
                        <div className="text-[12.5px] font-semibold text-stone-900 truncate flex items-center gap-1">{p.short}{p.top && <span className="text-[10px]">⭐</span>}</div>
                        <div className="text-[10.5px] text-stone-500 tabular-nums">{load} / {capacity} {t("dp.load")}</div>
                      </div>
                    </div>
                    <CapacityBar load={load} capacity={capacity} />
                  </div>
                  <div className="flex-1 p-2 space-y-1.5 overflow-y-auto bg-stone-50/40 min-h-[300px]">
                    {fresh.map((o) => (
                      <div key={o.no} className="rounded-lg bg-white ring-1 ring-[var(--accent-300)] p-2 animate-scale-in">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[11.5px] font-semibold text-stone-900">{o.no}</span>
                          <Badge tone="brand" dot>{t("c.assigned")}</Badge>
                        </div>
                        <div className="text-[11.5px] text-stone-600 mt-1 truncate">{o.customer}</div>
                      </div>
                    ))}
                    {inProg.map((o) => (
                      <div key={o.no} className="rounded-lg bg-white ring-1 ring-stone-200 p-2">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[11.5px] font-semibold text-stone-700">{o.no}</span>
                          <StageBadge stage={o.stage} size="sm" />
                        </div>
                        <div className="text-[11.5px] text-stone-500 mt-1 truncate">{o.customer}</div>
                      </div>
                    ))}
                    {fresh.length === 0 && inProg.length === 0 && (
                      <div className="text-center text-[11.5px] text-stone-400 py-10">Idle — ready for work</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
window.Dispatcher = Dispatcher;
