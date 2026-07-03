/* global React, I, Badge, Avatar, Sparkline, Button, IconButton, Panel, KpiCard, PageHead */
const { useState, useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// TEAM MANAGEMENT (Admin) — members · classification · permissions · perf
// ─────────────────────────────────────────────────────────────────────
function TeamAdmin({ onToast, dir }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [members, setMembers] = useState(() => D.TEAM_MEMBERS.map((m) => ({ ...m, perms: [...m.perms] })));
  const [groupBy, setGroupBy] = useState("role");
  const [view, setView] = useState("list");
  const [addOpen, setAddOpen] = useState(false);
  const [openId, setOpenId] = useState(null);

  const activeNow = members.filter((m) => m.status === "active").length;
  const onShift = members.filter((m) => m.status !== "offline").length;
  const avgSla = Math.round(members.filter((m) => m.perf.sla > 0).reduce((a, m) => a + m.perf.sla, 0) / members.filter((m) => m.perf.sla > 0).length);

  const groups = useMemo(() => {
    const keyFn = { role: (m) => t("role." + m.role), tier: (m) => t(D.TIERS[m.tier].label) || D.TIERS[m.tier].label, shift: (m) => m.shift };
    const fn = keyFn[groupBy];
    const map = {};
    members.forEach((m) => { const k = fn(m); (map[k] = map[k] || []).push(m); });
    return Object.entries(map);
  }, [members, groupBy]);

  function updateMember(id, patch) {
    setMembers((ms) => ms.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }

  const open = members.find((m) => m.id === openId);

  if (open) return <MemberProfile member={open} onBack={() => setOpenId(null)} onSave={(patch) => { updateMember(open.id, patch); onToast?.({ type: "success", text: `${D.byId(open.id).short} · synced to ERPNext (Logistics Role Map)`, action: patch.suspended === true ? { label: t("c.undo"), onClick: () => updateMember(open.id, { suspended: false }) } : undefined }); }} dir={dir} />;

  return (
    <div className="max-w-[1320px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("ta.title")} sub={t("ta.sub")}>
        <Button variant="secondary" size="md" icon={I.Download}>Export</Button>
        <Button variant="brand" size="md" icon={I.UserPlus} onClick={() => setAddOpen(true)}>{t("ta.addMember")}</Button>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Users} tone="stone" label={t("ta.members")} value={members.length} />
        <KpiCard icon={I.Dot} tone="emerald" label={t("ta.activeNow")} value={activeNow} />
        <KpiCard icon={I.Clock} tone="violet" label={t("ta.onShift")} value={onShift} />
        <KpiCard icon={I.Shield} tone="amber" label={t("ta.avgSla")} value={avgSla} unit="%" />
      </div>

      {/* controls */}
      <div className="flex items-center justify-between gap-2 mb-4 flex-wrap">
        <div className="flex items-center gap-2 h-7">
          {view === "cards" && <>
            <span className="text-[11.5px] text-stone-500">Group by</span>
            <div className="inline-flex bg-stone-100/80 rounded-lg p-0.5">
              {[["role", t("ta.byRole")], ["tier", t("ta.byTier")], ["shift", t("ta.byShift")]].map(([k, l]) => (
                <button key={k} onClick={() => setGroupBy(k)}
                  className={`px-3 h-7 text-[12px] font-medium rounded-md transition-all ${groupBy === k ? "bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]" : "text-stone-500 hover:text-stone-800"}`}>{l}</button>
              ))}
            </div>
          </>}
        </div>
        <div className="inline-flex bg-stone-100/80 rounded-lg p-0.5">
          {[["list", I.Sort], ["cards", I.Dashboard]].map(([k, Ic]) => (
            <button key={k} onClick={() => setView(k)} title={k}
              className={`w-9 h-7 rounded-md flex items-center justify-center transition-all ${view === k ? "bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]" : "text-stone-400 hover:text-stone-700"}`}><Ic width={15} height={15} /></button>
          ))}
        </div>
      </div>

      {view === "list" ? (
        <MemberTable members={members} onOpen={setOpenId} />
      ) : (
        <div className="space-y-5">
          {groups.map(([label, list]) => (
            <div key={label}>
              <div className="flex items-center gap-2 mb-2 px-1">
                <span className="text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400">{label}</span>
                <span className="text-[11px] text-stone-400">· {list.length}</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {list.map((m) => <MemberCard key={m.id} m={m} onClick={() => setOpenId(m.id)} />)}
              </div>
            </div>
          ))}
        </div>
      )}

      {addOpen && <AddMember onClose={() => setAddOpen(false)} dir={dir} onCreate={(mb) => { setMembers((ms) => [mb, ...ms]); onToast?.({ type: "success", text: `${mb.dispName} · ERPNext User created & role mapped` }); }} />}
    </div>
  );
}
window.TeamAdmin = TeamAdmin;

function MemberCard({ m, onClick }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const st = D.MEMBER_STATUS[m.status];
  const tier = D.TIERS[m.tier];
  return (
    <button onClick={onClick} className="text-start bg-white rounded-xl ring-1 ring-stone-200/70 p-4 hover:ring-stone-300 hover:shadow-[0_4px_16px_-6px_rgba(0,0,0,0.1)] transition-all">
      <div className="flex items-start gap-3">
        <div className="relative flex-shrink-0">
          <Avatar name={D.byId(m.id).name} size={40} />
          <span className={`absolute -bottom-0.5 -end-0.5 w-3 h-3 rounded-full ring-2 ring-white ${m.status === "active" ? "bg-emerald-500" : m.status === "idle" ? "bg-amber-500" : "bg-stone-300"}`} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[13.5px] font-semibold text-stone-900 truncate">{D.byId(m.id).short === D.byId(m.id).name ? D.byId(m.id).name : D.byId(m.id).name}</div>
          <div className="text-[11.5px] text-stone-500">{t("role." + m.role)} · {m.shift}</div>
        </div>
        <I.ChevronDown width={14} height={14} className="text-stone-300 -rotate-90 rtl:rotate-90" />
      </div>
      <div className="flex items-center gap-1.5 mt-3 flex-wrap">
        <Badge tone={tier.tone} dot className="whitespace-nowrap">{tier.label}</Badge>
        <Badge tone={st.tone} className="whitespace-nowrap">{st.label}</Badge>
      </div>
      <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-stone-100">
        <Mini label={m.perf.unit} value={m.perf.count || "—"} />
        <Mini label={t("c.sla")} value={m.perf.sla ? m.perf.sla + "%" : "—"} tone={m.perf.sla >= 90 ? "emerald" : m.perf.sla >= 85 ? "amber" : "stone"} />
        <Mini label={t("ta.permissions")} value={m.perms.length} />
      </div>
    </button>
  );
}
function Mini({ label, value, tone = "stone" }) {
  const c = { stone: "text-stone-900", emerald: "text-emerald-600", amber: "text-amber-600" }[tone];
  return <div><div className={`text-[15px] font-semibold tabular-nums leading-none ${c}`}>{value}</div><div className="text-[10px] text-stone-500 mt-1 truncate">{label}</div></div>;
}

// ── Member table (default listing) ───────────────────────────────────
function MemberTable({ members, onOpen }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  return (
    <Panel bodyClass="p-0">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px]">
          <thead>
            <tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th className="text-start px-4 py-2.5">{t("ta.members")}</th>
              <th className="text-start px-4 py-2.5">{t("ta.role")}</th>
              <th className="text-start px-4 py-2.5">{t("ta.tier")}</th>
              <th className="text-start px-4 py-2.5 hidden md:table-cell">{t("ta.shift")}</th>
              <th className="text-start px-4 py-2.5">{t("ta.status")}</th>
              <th className="text-end px-4 py-2.5 hidden sm:table-cell">Today</th>
              <th className="text-end px-4 py-2.5">{t("c.sla")}</th>
              <th className="text-end px-4 py-2.5 hidden lg:table-cell">{t("ta.permissions")}</th>
              <th className="px-2 py-2.5"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {members.map((m) => {
              const st = D.MEMBER_STATUS[m.status];
              const tier = D.TIERS[m.tier];
              return (
                <tr key={m.id} onClick={() => onOpen(m.id)} className="cursor-pointer hover:bg-stone-50 transition-colors">
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2.5">
                      <div className="relative flex-shrink-0">
                        <Avatar name={D.byId(m.id).name} size={30} />
                        <span className={`absolute -bottom-0.5 -end-0.5 w-2.5 h-2.5 rounded-full ring-2 ring-white ${m.status === "active" ? "bg-emerald-500" : m.status === "idle" ? "bg-amber-500" : "bg-stone-300"}`} />
                      </div>
                      <span className="text-[12.5px] font-medium text-stone-900 truncate max-w-[160px]">{D.byId(m.id).name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-[12px] text-stone-600 whitespace-nowrap">{t("role." + m.role)}</td>
                  <td className="px-4 py-2.5"><Badge tone={tier.tone} dot className="whitespace-nowrap">{tier.label}</Badge></td>
                  <td className="px-4 py-2.5 text-[12px] text-stone-600 hidden md:table-cell whitespace-nowrap">{m.shift}</td>
                  <td className="px-4 py-2.5"><Badge tone={st.tone} className="whitespace-nowrap">{st.label}</Badge></td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] tabular-nums hidden sm:table-cell"><span className="font-semibold text-stone-900">{m.perf.count || "—"}</span> <span className="text-[10.5px] text-stone-400">{m.perf.count ? m.perf.unit : ""}</span></td>
                  <td className="px-4 py-2.5 text-end"><span className={`text-[12.5px] font-semibold tabular-nums ${m.perf.sla >= 90 ? "text-emerald-600" : m.perf.sla >= 85 ? "text-amber-600" : m.perf.sla ? "text-stone-600" : "text-stone-300"}`}>{m.perf.sla ? m.perf.sla + "%" : "—"}</span></td>
                  <td className="px-4 py-2.5 text-end hidden lg:table-cell">
                    <span className="inline-flex items-center gap-1 text-[12px] text-stone-600"><I.Shield width={12} height={12} className="text-stone-400" />{m.perms.length}</span>
                  </td>
                  <td className="px-2 py-2.5 text-end"><I.ChevronDown width={14} height={14} className="text-stone-300 -rotate-90 rtl:rotate-90 inline" /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

// ── Member drawer — classification + permissions + performance ───────
function MemberDrawer({ member, onClose, onSave, dir }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [tier, setTier] = useState(member.tier);
  const [perms, setPerms] = useState([...member.perms]);
  const [shift, setShift] = useState(member.shift);
  const dirty = tier !== member.tier || shift !== member.shift || perms.length !== member.perms.length || perms.some((p) => !member.perms.includes(p));
  const side = dir === "rtl" ? "left-0" : "right-0";
  const anim = dir === "rtl" ? "animate-[drawerInL_.28s_cubic-bezier(.16,1,.3,1)]" : "animate-drawer-in";

  function togglePerm(k) { setPerms((p) => (p.includes(k) ? p.filter((x) => x !== k) : [...p, k])); }

  return (
    <div className="fixed inset-0 z-[140]">
      <div className="absolute inset-0 bg-stone-900/25 backdrop-blur-[1px] animate-fade-in" onClick={onClose} />
      <div className={`absolute top-0 ${side} h-full w-full max-w-[460px] bg-stone-50 shadow-[0_0_60px_-10px_rgba(0,0,0,0.3)] flex flex-col ${anim}`} dir={dir}>
        <header className="bg-white border-b border-stone-200/70 px-4 py-3.5 flex items-center gap-3 flex-shrink-0">
          <div className="relative">
            <Avatar name={D.byId(member.id).name} size={40} />
            <span className={`absolute -bottom-0.5 -end-0.5 w-3 h-3 rounded-full ring-2 ring-white ${member.status === "active" ? "bg-emerald-500" : member.status === "idle" ? "bg-amber-500" : "bg-stone-300"}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[14.5px] font-semibold text-stone-900 truncate">{D.byId(member.id).name}</div>
            <div className="text-[11.5px] text-stone-500">{member.email}</div>
          </div>
          <IconButton icon={I.X} onClick={onClose} />
        </header>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* profile */}
          <div className="grid grid-cols-2 gap-2">
            <Fact2 label={t("ta.role")} value={t("role." + member.role)} />
            <Fact2 label={t("ta.joined")} value={member.joined} />
          </div>

          {/* performance */}
          <div className="bg-gradient-to-br from-[var(--accent-50)] to-white rounded-xl ring-1 ring-[var(--accent-200)]/50 p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">{t("ta.perfTitle")}</div>
            <div className="grid grid-cols-3 gap-3">
              <PerfTile label={member.perf.unit} value={member.perf.count || "—"} />
              <PerfTile label={t("pf.avgTime")} value={member.perf.avg} />
              <PerfTile label={t("c.sla")} value={member.perf.sla ? member.perf.sla + "%" : "—"} />
            </div>
            <div className="mt-3 pt-3 border-t border-[var(--accent-200)]/40 flex items-center justify-between">
              <span className="text-[11px] text-stone-500">{t("pf.trend")}{member.perf.rank ? ` · ${t("c.rank")} #${member.perf.rank}` : ""}</span>
              <Sparkline data={member.perf.trend} width={120} height={26} />
            </div>
          </div>

          {/* classification */}
          <div className="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">{t("ta.classification")}</div>
            <div className="text-[11.5px] text-stone-500 mb-1.5">{t("ta.tier")}</div>
            <div className="inline-flex bg-stone-100/80 rounded-lg p-0.5 w-full mb-3">
              {Object.entries(D.TIERS).map(([k, v]) => (
                <button key={k} onClick={() => setTier(k)} className={`flex-1 h-7 text-[12px] font-medium rounded-md transition-all ${tier === k ? "bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]" : "text-stone-500 hover:text-stone-800"}`}>{v.label}</button>
              ))}
            </div>
            <div className="text-[11.5px] text-stone-500 mb-1.5">{t("ta.shift")}</div>
            <div className="inline-flex bg-stone-100/80 rounded-lg p-0.5 w-full mb-3">
              {["Morning", "Evening", "Full day"].map((s) => (
                <button key={s} onClick={() => setShift(s)} className={`flex-1 h-7 text-[12px] font-medium rounded-md transition-all ${shift === s ? "bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]" : "text-stone-500 hover:text-stone-800"}`}>{s}</button>
              ))}
            </div>
            <div className="text-[11.5px] text-stone-500 mb-1.5">{t("ta.zones")}</div>
            <div className="flex flex-wrap gap-1.5">
              {member.zones.map((z) => <Badge key={z} tone="neutral" className="whitespace-nowrap">{z}</Badge>)}
            </div>
          </div>

          {/* permissions */}
          <div className="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">{t("ta.permissions")} · {t("ta.capabilities")}</div>
            <div className="space-y-1.5">
              {D.CAPS.map((cap) => {
                const on = perms.includes(cap.key);
                const Icon = cap.icon;
                return (
                  <button key={cap.key} onClick={() => togglePerm(cap.key)} className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-stone-50 transition-colors">
                    <span className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${on ? "bg-[var(--accent-50)] text-[var(--accent-700)]" : "bg-stone-100 text-stone-400"}`}><Icon width={14} height={14} /></span>
                    <span className={`flex-1 text-start text-[12.5px] font-medium ${on ? "text-stone-900" : "text-stone-400"}`}>{cap.label}</span>
                    <span className={`w-9 h-5 rounded-full p-0.5 transition-colors flex-shrink-0 ${on ? "bg-[var(--accent-600)]" : "bg-stone-200"}`}>
                      <span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform ${on ? "translate-x-4 rtl:-translate-x-4" : ""}`} />
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <footer className="bg-white border-t border-stone-200/70 px-4 py-3 flex items-center justify-end gap-2 flex-shrink-0">
          <Button variant="ghost" size="md" onClick={onClose}>{t("c.close")}</Button>
          <Button variant="brand" size="md" icon={I.Check} disabled={!dirty} onClick={() => onSave({ tier, perms, shift })}>{t("ta.saveChanges")}</Button>
        </footer>
      </div>
    </div>
  );
}
function Fact2({ label, value }) {
  return <div className="bg-white rounded-lg ring-1 ring-stone-200/70 px-3 py-2"><div className="text-[10px] font-semibold uppercase tracking-wide text-stone-400">{label}</div><div className="text-[13px] font-medium text-stone-900 mt-0.5 truncate">{value}</div></div>;
}
function PerfTile({ label, value }) {
  return <div><div className="text-[17px] font-semibold text-stone-900 tabular-nums leading-none">{value}</div><div className="text-[10px] text-stone-500 mt-1 truncate">{label}</div></div>;
}

// ── shared little inputs ─────────────────────────────────────────────
const ROLE_DEFAULT_PERMS = {
  picker: ["pick"], packer: ["pack_label", "ship"], dispatcher: ["assign", "pick", "reports"],
  returns: ["returns", "inventory"], manager: ["admin", "assign", "ship", "returns", "inventory", "reports"],
};
function Field({ label, children }) {
  return <div><div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{label}</div>{children}</div>;
}
function Seg({ value, onChange, options }) {
  return (
    <div className="inline-flex bg-stone-100/80 rounded-lg p-0.5 w-full">
      {options.map(([v, l]) => (
        <button key={v} onClick={() => onChange(v)} className={`flex-1 h-7 text-[12px] font-medium rounded-md transition-all ${value === v ? "bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]" : "text-stone-500 hover:text-stone-800"}`}>{l}</button>
      ))}
    </div>
  );
}

// ── Add member ───────────────────────────────────────────────────────
function AddMember({ onClose, onCreate, dir }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [name, setName] = useState("");
  const [role, setRole] = useState("picker");
  const [tier, setTier] = useState("steady");
  const [shift, setShift] = useState("Morning");
  const [zones, setZones] = useState([]);
  const roleOpts = ["picker", "packer", "dispatcher", "returns", "manager"];
  function toggleZone(z) { setZones((zs) => (zs.includes(z) ? zs.filter((x) => x !== z) : [...zs, z])); }
  function submit() {
    const nm = name.trim(); if (!nm) return;
    const id = "u" + Date.now();
    const short = nm.split(/\s+/)[0];
    D.TEAM.push({ id, name: nm, short, role });
    const unit = role === "packer" ? "parcels" : role === "returns" ? "returns" : role === "manager" ? "—" : "picks";
    onCreate({ id, dispName: nm, role, tier, shift, zones: zones.length ? zones : ["—"], status: "active", joined: D.TODAY.slice(0, 7), perms: [...(ROLE_DEFAULT_PERMS[role] || [])], suspended: false, perf: { count: 0, unit, avg: "—", sla: 0, rank: 0, trend: [0, 0, 0, 0, 0, 0, 0] } });
    onClose();
  }
  return (
    <window.LgModal title={t("ta.newMember")} sub={t("ta.sub")} onClose={onClose} dir={dir}
      footer={<>
        <Button variant="ghost" size="md" onClick={onClose}>{t("c.close")}</Button>
        <Button variant="brand" size="md" icon={I.Check} disabled={!name.trim()} onClick={submit}>{t("ta.create")}</Button>
      </>}>
      <div className="space-y-4">
        <Field label={t("ta.fullName")}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Yassine Berrada" autoFocus
            className="w-full h-9 px-3 text-[13px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none" />
        </Field>
        <Field label={t("ta.role")}>
          <div className="grid grid-cols-3 gap-1.5">
            {roleOpts.map((r) => (
              <button key={r} onClick={() => setRole(r)} className={`h-8 text-[12px] font-medium rounded-lg ring-1 transition-all ${role === r ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40 text-stone-900" : "ring-stone-200 text-stone-600 hover:ring-stone-300"}`}>{t("role." + r)}</button>
            ))}
          </div>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label={t("ta.tier")}><Seg value={tier} onChange={setTier} options={[["top", "Top"], ["steady", "Steady"], ["coaching", "Coaching"]]} /></Field>
          <Field label={t("ta.shift")}><Seg value={shift} onChange={setShift} options={[["Morning", "AM"], ["Evening", "PM"], ["Full day", "Full"]]} /></Field>
        </div>
        <Field label={t("ta.zones")}>
          <div className="flex flex-wrap gap-1.5">
            {D.ZONES.map((z) => {
              const on = zones.includes(z);
              return <button key={z} onClick={() => toggleZone(z)} className={`px-2 h-7 text-[11px] font-medium rounded-lg ring-1 transition-all ${on ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40 text-stone-900" : "ring-stone-200 text-stone-500 hover:ring-stone-300"}`}>{z.replace(" - JM", "")}</button>;
            })}
          </div>
        </Field>
        <div className="rounded-lg bg-stone-50 ring-1 ring-stone-200/60 p-3 flex items-start gap-2">
          <I.Shield width={14} height={14} className="text-stone-400 mt-0.5 flex-shrink-0" />
          <p className="text-[11.5px] text-stone-500">Default permissions for <span className="font-medium text-stone-700">{t("role." + role)}</span>: {(ROLE_DEFAULT_PERMS[role] || []).map((k) => D.CAPS.find((c) => c.key === k)?.label).join(", ")}. Editable after creating.</p>
        </div>
      </div>
    </window.LgModal>
  );
}

// ── Member profile (full page) ───────────────────────────────────────
function gen30(m) {
  const base = m.perf.count || 18;
  const data = [], labels = [];
  for (let i = 0; i < 30; i++) {
    const wave = 0.82 + 0.32 * (((i * 7) % 5) / 5);
    data.push(Math.round(base * (0.62 + 0.014 * i) * wave));
    labels.push(i === 0 ? "30d" : i === 15 ? "15d" : i === 29 ? "today" : "");
  }
  return { data, labels };
}

function MemberProfile({ member, onBack, onSave, dir }) {
  const { t, askConfirm } = window.useLg();
  const D = window.LG_DATA;
  const person = D.byId(member.id);
  const tier = D.TIERS[member.tier];
  const st = D.MEMBER_STATUS[member.status];
  const susp = !!member.suspended;
  const bonus = window.computeBonus(member);
  const { data: d30, labels: l30 } = useMemo(() => gen30(member), [member.id, member.perf.count]);
  const median = 20;

  // editable classification + perms
  const [tierV, setTierV] = useState(member.tier);
  const [perms, setPerms] = useState([...member.perms]);
  const [shift, setShift] = useState(member.shift);
  const dirty = tierV !== member.tier || shift !== member.shift || perms.length !== member.perms.length || perms.some((p) => !member.perms.includes(p));
  function togglePerm(k) { if (susp) return; setPerms((p) => (p.includes(k) ? p.filter((x) => x !== k) : [...p, k])); }

  const myOrders = D.ORDERS.filter((o) => o.picker === member.id).slice(0, 5);
  const acts = myOrders.length ? myOrders.map((o) => ({ txt: `${o.stage === "delivered" ? "Delivered" : o.stage === "picked" ? "Picked" : "Handled"} ${o.no}`, sub: o.customer, t: `${o.mins || 12}m` }))
    : [{ txt: "Shift started", sub: member.shift, t: "—" }];

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <button onClick={onBack} className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap">
        <I.Back width={15} height={15} className="rtl:rotate-180" />{t("ta.back")}
      </button>

      {/* hero */}
      <div className={`rounded-2xl ring-1 p-5 mb-4 ${susp ? "bg-stone-100 ring-stone-200" : "bg-gradient-to-r from-[var(--accent-50)] to-white ring-[var(--accent-200)]/50"}`}>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3.5">
            <div className="relative flex-shrink-0">
              <Avatar name={person.name} size={60} className={susp ? "opacity-50 saturate-0" : ""} />
              <span className={`absolute -bottom-0.5 -end-0.5 w-4 h-4 rounded-full ring-2 ring-white ${susp ? "bg-rose-500" : member.status === "active" ? "bg-emerald-500" : member.status === "idle" ? "bg-amber-500" : "bg-stone-300"}`} />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{person.name}</h1>
                <Badge tone={tier.tone} dot className="whitespace-nowrap">{tier.label}</Badge>
                {susp ? <Badge tone="red" className="whitespace-nowrap">{t("ta.suspended")}</Badge> : <Badge tone={st.tone} className="whitespace-nowrap">{st.label}</Badge>}
              </div>
              <div className="text-[12.5px] text-stone-600 mt-1">{t("role." + member.role)} · {member.shift} · {t("ta.joined")} {member.joined}</div>
              <div className="text-[12px] text-stone-500 mt-0.5">{member.email || person.email || "—"}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant={susp ? "success" : "secondary"} size="md" icon={susp ? I.CheckCircle : I.Shield} onClick={() => { if (susp) return onSave({ suspended: false }); askConfirm?.({ title: t("ta.suspend") + " — " + D.byId(member.id).short, body: t("ta.suspendedMsg"), confirmLabel: t("ta.suspend"), danger: true, onConfirm: () => onSave({ suspended: true }) }); }}>{susp ? t("ta.restore") : t("ta.suspend")}</Button>
          </div>
        </div>
        {susp && (
          <div className="mt-3 rounded-lg bg-white ring-1 ring-rose-200/70 px-3 py-2 flex items-center gap-2 text-[12px] text-rose-700">
            <I.AlertCircle width={14} height={14} className="text-rose-500 flex-shrink-0" />{t("ta.suspendedMsg")}
          </div>
        )}
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Box} tone="stone" label={`Today · ${member.perf.unit}`} value={member.perf.count || "—"} />
        <KpiCard icon={I.Clock} tone="violet" label={t("pf.avgTime")} value={member.perf.avg} />
        <KpiCard icon={I.Shield} tone={member.perf.sla >= 90 ? "emerald" : "amber"} label={t("c.sla")} value={member.perf.sla ? member.perf.sla + "%" : "—"} />
        <KpiCard icon={I.TrendUp} tone="emerald" label={t("ta.vsMedian")} value={member.perf.count ? "+" + (member.perf.count - median) : "—"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-4">
        {/* LEFT — performance */}
        <div className="space-y-4">
          <Panel title={t("ta.trend30")} right={<Badge tone="brand" dot>{t("c.rank")} #{member.perf.rank || "—"}</Badge>} bodyClass="p-4">
            <window.LineChart data={d30} labels={l30} height={200} />
          </Panel>

          <Panel title={t("ta.thisWeek")} bodyClass="p-4">
            <div className="flex items-end justify-between gap-2 h-[120px]">
              {member.perf.trend.map((v, i) => {
                const max = Math.max(...member.perf.trend, 1);
                const days = ["M", "T", "W", "T", "F", "S", "S"];
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1.5">
                    <div className="w-full flex items-end justify-center" style={{ height: 90 }}>
                      <div className="w-full max-w-[28px] rounded-t-md bg-[var(--accent-500)]" style={{ height: `${(v / max) * 100}%` }} />
                    </div>
                    <span className="text-[10px] text-stone-400 tabular-nums">{v}</span>
                    <span className="text-[10px] text-stone-400">{days[i]}</span>
                  </div>
                );
              })}
            </div>
          </Panel>

          <Panel title={t("ta.activityFeed")} bodyClass="p-2">
            {acts.map((a, i) => (
              <div key={i} className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-stone-50">
                <span className="w-7 h-7 rounded-lg bg-stone-100 text-stone-400 flex items-center justify-center flex-shrink-0"><I.Box width={13} height={13} /></span>
                <div className="min-w-0 flex-1"><div className="text-[12.5px] font-medium text-stone-800 truncate">{a.txt}</div><div className="text-[11px] text-stone-500 truncate">{a.sub}</div></div>
                <span className="text-[11px] text-stone-400 tabular-nums">{a.t}</span>
              </div>
            ))}
          </Panel>
        </div>

        {/* RIGHT — bonus + classification + permissions */}
        <div className="space-y-4">
          {bonus && <BonusCard bonus={bonus} member={member} />}

          <Panel title={t("ta.classification")} bodyClass="p-4 space-y-3">
            <div><div className="text-[11.5px] text-stone-500 mb-1.5">{t("ta.tier")}</div>
              <Seg value={tierV} onChange={susp ? () => {} : setTierV} options={Object.entries(D.TIERS).map(([k, v]) => [k, v.label])} /></div>
            <div><div className="text-[11.5px] text-stone-500 mb-1.5">{t("ta.shift")}</div>
              <Seg value={shift} onChange={susp ? () => {} : setShift} options={[["Morning", "Morning"], ["Evening", "Evening"], ["Full day", "Full day"]]} /></div>
            <div><div className="text-[11.5px] text-stone-500 mb-1.5">{t("ta.zones")}</div>
              <div className="flex flex-wrap gap-1.5">{member.zones.map((z) => <Badge key={z} tone="neutral" className="whitespace-nowrap">{z}</Badge>)}</div></div>
          </Panel>

          <Panel title={`${t("ta.permissions")} · ${t("ta.capabilities")}`} bodyClass="p-3">
            <div className={`space-y-1 ${susp ? "opacity-50 pointer-events-none" : ""}`}>
              {D.CAPS.map((cap) => {
                const on = perms.includes(cap.key); const Icon = cap.icon;
                return (
                  <button key={cap.key} onClick={() => togglePerm(cap.key)} className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-stone-50 transition-colors">
                    <span className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${on ? "bg-[var(--accent-50)] text-[var(--accent-700)]" : "bg-stone-100 text-stone-400"}`}><Icon width={14} height={14} /></span>
                    <span className={`flex-1 text-start text-[12.5px] font-medium ${on ? "text-stone-900" : "text-stone-400"}`}>{cap.label}</span>
                    <span className={`w-9 h-5 rounded-full p-0.5 transition-colors flex-shrink-0 ${on ? "bg-[var(--accent-600)]" : "bg-stone-200"}`}><span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform ${on ? "translate-x-4 rtl:-translate-x-4" : ""}`} /></span>
                  </button>
                );
              })}
            </div>
            <div className="flex justify-end pt-2 mt-1 border-t border-stone-100">
              <Button variant="brand" size="sm" icon={I.Check} disabled={!dirty || susp} onClick={() => onSave({ tier: tierV, perms, shift })}>{t("ta.saveChanges")}</Button>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function BonusCard({ bonus, member }) {
  const { t } = window.useLg();
  const rows = [
    ["bn.base", bonus.points.base, false],
    ["bn.onTime", bonus.points.onTime, false],
    ["bn.zeroError", bonus.points.zeroError, false],
    ["bn.targetBonus", bonus.points.targetBonus, false],
    ["bn.penalty", -bonus.points.penalty, true],
  ];
  return (
    <Panel bodyClass="p-0">
      <div className="px-4 py-3 bg-gradient-to-br from-amber-50 to-white border-b border-amber-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2"><span className="w-7 h-7 rounded-lg bg-amber-100 text-amber-600 flex items-center justify-center"><I.Zap width={14} height={14} /></span><span className="text-[13px] font-semibold text-stone-900">{t("bn.title")}</span></div>
          <Badge tone={bonus.gatePass ? "green" : "red"} dot>{bonus.gatePass ? t("bn.unlocked") : t("bn.locked")}</Badge>
        </div>
        <div className="mt-3">
          <div className="text-[11px] text-stone-500">{t("bn.earned")} · {t("bn.thisMonth")}</div>
          <div className="flex items-end justify-between gap-2 mt-0.5">
            <div className="text-[26px] font-bold text-stone-900 tabular-nums leading-none whitespace-nowrap">{window.fmtMAD(bonus.earned)} <span className="text-[12px] font-medium text-stone-400">MAD</span></div>
            <div className="text-end leading-tight flex-shrink-0">
              <div className="text-[9.5px] text-stone-400 uppercase tracking-wide">{t("bn.projected")}</div>
              <div className="text-[13px] font-semibold text-emerald-600 tabular-nums">{window.fmtMAD(bonus.projected)}</div>
            </div>
          </div>
        </div>
        <div className="mt-2.5 h-2 rounded-full bg-white ring-1 ring-amber-200/60 overflow-hidden"><div className="h-full rounded-full bg-amber-500" style={{ width: `${bonus.pct * 100}%` }} /></div>
        <div className="mt-1 flex items-center justify-between text-[10.5px] text-stone-400"><span>0</span><span>{t("bn.cap")} {window.fmtMAD(bonus.cap)} MAD</span></div>
      </div>
      <div className="p-4 space-y-1.5">
        {!bonus.gatePass && <div className="rounded-lg bg-rose-50 ring-1 ring-rose-200/60 px-3 py-2 text-[11.5px] text-rose-700 mb-2 flex items-center gap-1.5"><I.AlertCircle width={13} height={13} className="text-rose-500" />{t("bn.raiseSla")}</div>}
        <div className="text-[10.5px] font-semibold uppercase tracking-wide text-stone-400 mb-1">{t("bn.points")}</div>
        {rows.map(([k, v, neg]) => (
          <div key={k} className="flex items-center justify-between gap-2 text-[12px]">
            <span className="text-stone-600 truncate min-w-0">{t(k)}</span>
            <span className={`tabular-nums font-medium flex-shrink-0 ${neg ? "text-rose-600" : "text-stone-800"}`}>{v < 0 ? "−" : "+"}{window.fmtMAD(Math.abs(v))}</span>
          </div>
        ))}
        <div className="flex items-center justify-between gap-2 pt-1.5 mt-1 border-t border-stone-100">
          <span className="inline-flex items-center gap-1 text-[11px] text-amber-700 font-medium whitespace-nowrap"><I.Zap width={12} height={12} />{bonus.streakDays} {t("bn.streak")} +{bonus.streakPct}%</span>
          <span className="text-[11px] text-stone-500 whitespace-nowrap">{t("bn.tierMult")} ×{bonus.tierMult}</span>
        </div>
        {bonus.teamKicker > 0 && (
          <div className="rounded-lg bg-emerald-50 ring-1 ring-emerald-200/60 px-3 py-2 mt-2 flex items-center gap-2 text-[11.5px] text-emerald-700">
            <I.Users width={13} height={13} className="text-emerald-500" />{t("bn.teamKicker")}: +{window.fmtMAD(bonus.teamKicker)} MAD <span className="text-emerald-500/70">· floor hit same-day target</span>
          </div>
        )}
      </div>
    </Panel>
  );
}

// ─────────────────────────────────────────────────────────────────────
// BONUS BOARD — team-wide monthly payout & incentives
// ─────────────────────────────────────────────────────────────────────
function BonusBoard({ onToast }) {
  const { t, askConfirm } = window.useLg();
  const D = window.LG_DATA;
  const B = window.LG_BONUS;
  const rows = D.TEAM_MEMBERS.map((m) => ({ m, b: window.computeBonus(m) }))
    .filter((x) => x.b).sort((a, c) => c.b.projected - a.b.projected);
  const pool = rows.reduce((a, x) => a + x.b.projected, 0);
  const unlocked = rows.filter((x) => x.b.gatePass).length;
  const avg = Math.round(pool / rows.length);
  const kickerOn = B.currentSameDay >= B.teamSameDayTarget;
  const toGo = (B.teamSameDayTarget - B.currentSameDay).toFixed(1);

  return (
    <div className="max-w-[1320px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("bn.title")} sub={t("bn.boardSub")}>
        <Button variant="secondary" size="md" icon={I.Download}>Export</Button>
        <Button variant="brand" size="md" icon={I.Wallet} onClick={() => askConfirm?.({ title: t("bn.runPayout") + "?", body: `${window.fmtMAD(pool)} MAD across ${rows.length} members will be drafted as Additional Salary records in ERPNext.`, confirmLabel: t("bn.runPayout"), onConfirm: () => onToast?.({ type: "success", text: `Payout run · ${window.fmtMAD(pool)} MAD · ${rows.length} Additional Salary drafts in ERPNext` }) })}>{t("bn.runPayout")}</Button>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Wallet} tone="amber" label={t("bn.pool")} value={window.fmtMAD(pool)} unit="MAD" />
        <KpiCard icon={I.Cash} tone="stone" label={t("bn.avgPer")} value={window.fmtMAD(avg)} unit="MAD" />
        <KpiCard icon={I.CheckCircle} tone="emerald" label={t("bn.unlockedN")} value={`${unlocked}/${rows.length}`} />
        <KpiCard icon={I.Zap} tone="violet" label={t("ck.sameday")} value={B.currentSameDay} unit="%" />
      </div>

      {/* team kicker banner */}
      <div className={`rounded-2xl p-4 mb-4 ring-1 flex items-center gap-4 ${kickerOn ? "bg-gradient-to-r from-emerald-50 to-white ring-emerald-200/70" : "bg-gradient-to-r from-amber-50 to-white ring-amber-200/70"}`}>
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${kickerOn ? "bg-emerald-500" : "bg-amber-500"} text-white`}><I.Users width={22} height={22} /></div>
        <div className="flex-1 min-w-0">
          <div className="text-[14px] font-semibold text-stone-900">{t("bn.teamStatus")} · +{window.fmtMAD(B.teamKicker)} MAD for every member</div>
          <div className="text-[12px] text-stone-600 mt-0.5">{kickerOn ? `Floor hit ${B.currentSameDay}% same-day ship — kicker unlocked.` : `Floor at ${B.currentSameDay}% · ${toGo}% ${t("bn.toUnlock")} (target ${B.teamSameDayTarget}%).`}</div>
        </div>
        <div className="w-[120px] flex-shrink-0 hidden sm:block">
          <div className="h-2 rounded-full bg-white ring-1 ring-stone-200 overflow-hidden"><div className={`h-full rounded-full ${kickerOn ? "bg-emerald-500" : "bg-amber-500"}`} style={{ width: `${B.currentSameDay}%` }} /></div>
          <div className="text-[10px] text-stone-400 mt-1 text-end">{B.currentSameDay}% / {B.teamSameDayTarget}%</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        {/* payout table */}
        <Panel title={t("bn.payout")} sub={`${t("bn.thisMonth")} · ${B.workedDays}/${B.monthDays} days`} bodyClass="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px]">
              <thead>
                <tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                  <th className="text-start px-4 py-2.5 w-10">#</th>
                  <th className="text-start px-4 py-2.5">{t("ta.members")}</th>
                  <th className="text-end px-4 py-2.5 hidden md:table-cell">{t("bn.output")}</th>
                  <th className="text-end px-4 py-2.5">{t("c.sla")}</th>
                  <th className="text-start px-4 py-2.5">{t("bn.gate")}</th>
                  <th className="text-end px-4 py-2.5 hidden sm:table-cell">Streak</th>
                  <th className="text-end px-4 py-2.5">{t("bn.payout")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {rows.map(({ m, b }, i) => (
                  <tr key={m.id} className="hover:bg-stone-50 transition-colors">
                    <td className="px-4 py-2.5"><span className={`text-[12px] font-bold tabular-nums ${i === 0 ? "text-amber-500" : "text-stone-400"}`}>{i + 1}</span></td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2.5">
                        <Avatar name={D.byId(m.id).name} size={26} />
                        <div className="min-w-0"><div className="text-[12.5px] font-medium text-stone-900 truncate">{D.byId(m.id).short}</div><div className="text-[10.5px] text-stone-400">{t("role." + m.role)}</div></div>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-end text-[12.5px] text-stone-700 tabular-nums hidden md:table-cell">{m.perf.count} <span className="text-[10px] text-stone-400">{m.perf.unit}</span></td>
                    <td className="px-4 py-2.5 text-end"><span className={`text-[12.5px] font-semibold tabular-nums ${m.perf.sla >= 90 ? "text-emerald-600" : "text-amber-600"}`}>{m.perf.sla}%</span></td>
                    <td className="px-4 py-2.5"><Badge tone={b.gatePass ? "green" : "red"} dot className="whitespace-nowrap">{b.gatePass ? t("bn.unlocked") : t("bn.locked")}</Badge></td>
                    <td className="px-4 py-2.5 text-end hidden sm:table-cell"><span className="inline-flex items-center gap-0.5 text-[11.5px] text-amber-600 font-medium tabular-nums"><I.Zap width={11} height={11} />{b.streakDays}d</span></td>
                    <td className="px-4 py-2.5 text-end"><span className="text-[13px] font-semibold text-stone-900 tabular-nums">{window.fmtMAD(b.projected)}</span> <span className="text-[10px] text-stone-400">MAD</span></td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-stone-200 bg-stone-50/60 text-[12.5px] font-semibold">
                  <td className="px-4 py-2.5" colSpan="6">{t("bn.pool")}</td>
                  <td className="px-4 py-2.5 text-end text-stone-900 tabular-nums">{window.fmtMAD(pool)} <span className="text-[10px] font-normal text-stone-400">MAD</span></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </Panel>

        {/* weekly rewards + rules */}
        <div className="space-y-4">
          <Panel title={t("bn.weeklyTop")} bodyClass="p-3 space-y-2">
            {rows.slice(0, 3).map(({ m }, i) => (
              <div key={m.id} className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg bg-stone-50/60">
                <span className="text-[15px]">{["🥇", "🥈", "🥉"][i]}</span>
                <Avatar name={D.byId(m.id).name} size={26} />
                <span className="text-[12.5px] font-medium text-stone-900 flex-1 truncate">{D.byId(m.id).short}</span>
                <span className="text-[12.5px] font-semibold text-emerald-600 tabular-nums">+{B.weeklyTop[i]} <span className="text-[10px] text-stone-400">MAD</span></span>
              </div>
            ))}
          </Panel>

          <Panel title={t("bn.rules")} bodyClass="p-4">
            <ul className="space-y-2.5 text-[12px] text-stone-600">
              {[
                [I.Box, `Base ${B.perPick} MAD per pick/parcel`],
                [I.Shield, `Quality gate: bonus unlocks at ${B.slaGate}% SLA`],
                [I.Zap, `Streak: +${B.streakStepPct}% per 5-day target streak (cap ${B.streakCapPct}%)`],
                [I.TrendUp, `Tier multiplier rewards improvement, not just output`],
                [I.Users, `Team kicker: +${B.teamKicker} MAD each at ${B.teamSameDayTarget}% same-day`],
                [I.Wallet, `Monthly cap ${window.fmtMAD(B.monthlyCap)} MAD · paid end of month`],
              ].map(([Ic, txt], i) => (
                <li key={i} className="flex items-start gap-2"><Ic width={14} height={14} className="text-[var(--accent-600)] mt-0.5 flex-shrink-0" /><span className="text-pretty">{txt}</span></li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>
    </div>
  );
}
window.BonusBoard = BonusBoard;

// ─────────────────────────────────────────────────────────────────────
// ROSTER — shifts & floor coverage
// ─────────────────────────────────────────────────────────────────────
function Roster() {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const shifts = [["Morning", "06:00 – 14:00", 6], ["Evening", "14:00 – 22:00", 5], ["Full day", "08:00 – 18:00", 3]];
  const onFloor = D.TEAM_MEMBERS.filter((m) => m.status === "active").length;

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("ro.title")} sub={`${t("ro.sub")} · ${D.WAREHOUSE}`}>
        <Button variant="secondary" size="md" icon={I.Calendar}>{t("c.today")}</Button>
        <Button variant="brand" size="md" icon={I.Plus}>Add shift</Button>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Users} tone="stone" label={t("ta.members")} value={D.TEAM_MEMBERS.length} />
        <KpiCard icon={I.Dot} tone="emerald" label={t("ro.onFloor")} value={onFloor} />
        <KpiCard icon={I.Clock} tone="violet" label={t("ro.scheduled")} value={D.TEAM_MEMBERS.filter((m) => m.status !== "offline").length} />
        <KpiCard icon={I.AlertCircle} tone="amber" label={t("ro.gap")} value={1} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {shifts.map(([name, time, cap]) => {
          const members = D.TEAM_MEMBERS.filter((m) => m.shift === name);
          const active = members.filter((m) => m.status === "active").length;
          const pct = Math.min(1, members.length / cap);
          const gap = members.length < cap;
          return (
            <Panel key={name} bodyClass="p-0">
              <div className={`px-4 py-3 border-b border-stone-100 ${gap ? "bg-amber-50/40" : ""}`}>
                <div className="flex items-center justify-between">
                  <div><div className="text-[13.5px] font-semibold text-stone-900">{name}</div><div className="text-[11px] text-stone-500">{time}</div></div>
                  {gap ? <Badge tone="yellow" dot>{t("ro.gap")}</Badge> : <Badge tone="green" dot>{active} {t("ro.onFloor")}</Badge>}
                </div>
                <div className="flex items-center gap-2 mt-2.5">
                  <div className="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className={`h-full rounded-full ${gap ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${pct * 100}%` }} /></div>
                  <span className="text-[11px] text-stone-500 tabular-nums">{members.length}/{cap} {t("ro.capacity")}</span>
                </div>
              </div>
              <div className="p-2 space-y-0.5 min-h-[140px]">
                {members.map((m) => (
                  <div key={m.id} className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-stone-50">
                    <div className="relative flex-shrink-0"><Avatar name={D.byId(m.id).name} size={26} /><span className={`absolute -bottom-0.5 -end-0.5 w-2.5 h-2.5 rounded-full ring-2 ring-white ${m.status === "active" ? "bg-emerald-500" : m.status === "idle" ? "bg-amber-500" : "bg-stone-300"}`} /></div>
                    <div className="min-w-0 flex-1"><div className="text-[12.5px] font-medium text-stone-900 truncate">{D.byId(m.id).short}</div><div className="text-[10.5px] text-stone-500 flex items-center gap-1">{m.status === "offline" ? t("role." + m.role) : <><I.Clock width={9} height={9} className="text-emerald-500" />{(name === "Morning" ? "06" : name === "Evening" ? "14" : "08")}:{String((m.id.charCodeAt(0) * 7) % 55 + 2).padStart(2, "0")} · {t("role." + m.role)}</>}</div></div>
                    {m.suspended && <Badge tone="red">{t("ta.suspended")}</Badge>}
                  </div>
                ))}
                {members.length === 0 && <div className="text-center text-[11.5px] text-stone-300 py-8">No one scheduled</div>}
              </div>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
window.Roster = Roster;