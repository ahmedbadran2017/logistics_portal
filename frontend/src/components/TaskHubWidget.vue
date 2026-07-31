<template>
  <div class="th-widget" style="display: contents">
    <!-- Floating trigger -->
    <button
      v-if="!open"
      class="th-fab"
      :title="`My tasks · report to Task Hub (${portal})`"
      @click="openPanel"
    >
      <span class="th-fab-icon">⚑</span>
      <span class="th-fab-label">Tasks</span>
      <span v-if="counts.assigned_open" class="th-fab-badge" :class="{ hot: counts.breached }">
        {{ counts.assigned_open > 99 ? "99+" : counts.assigned_open }}
      </span>
    </button>

    <!-- Modal -->
    <div v-if="open" class="th-overlay" @click.self="close">
      <div class="th-modal">
        <div class="th-head">
          <div>
            <div class="th-title">Task Hub</div>
            <div class="th-sub">{{ portal }} portal · your work, in one place</div>
          </div>
          <button class="th-x" @click="close">✕</button>
        </div>

        <!-- tabs: your open work, or raise something new -->
        <div class="th-tabs">
          <button :class="{ on: tab === 'tasks' }" @click="switchTab('tasks')">
            My tasks
            <span v-if="counts.assigned_open" class="th-tabcount">{{ counts.assigned_open }}</span>
          </button>
          <button :class="{ on: tab === 'new' }" @click="switchTab('new')">Report</button>
        </div>

        <!-- ── My tasks ─────────────────────────────────────────────── -->
        <div v-if="tab === 'tasks'" class="th-body">
          <div class="th-scope">
            <button :class="{ on: scope === 'all' }" @click="setScope('all')">All</button>
            <button :class="{ on: scope === 'assigned' }" @click="setScope('assigned')">
              Assigned to me
            </button>
            <button :class="{ on: scope === 'reported' }" @click="setScope('reported')">
              I reported
            </button>
            <a class="th-hublink" href="/taskhub" target="_blank" rel="noopener">Open hub →</a>
          </div>

          <p v-if="tasksError" class="th-error">{{ tasksError }}</p>
          <p v-if="loadingTasks && !tasks.length" class="th-muted">Loading…</p>
          <p v-else-if="!tasks.length" class="th-muted">Nothing open — you're clear.</p>

          <div v-for="tk in tasks" :key="tk.name" class="th-task">
            <button class="th-task-head" @click="toggleTask(tk)">
              <span class="th-dot" :style="{ background: prioColor(tk.priority) }" />
              <span class="th-task-main">
                <span class="th-task-title">{{ tk.title }}</span>
                <span class="th-task-meta">
                  {{ tk.name }} · {{ tk.stage || tk.status }}
                  <template v-if="tk.due_date"> · due {{ tk.due_date }}</template>
                  <b v-if="tk.sla_breached" class="th-late"> · late</b>
                </span>
              </span>
            </button>

            <!-- inline detail: enough to act without leaving the portal -->
            <div v-if="expanded === tk.name" class="th-task-body">
              <p v-if="detail && detail.ticket.description" class="th-task-desc">
                {{ plain(detail.ticket.description) }}
              </p>

              <div class="th-row">
                <div class="th-col">
                  <label class="th-label">Status</label>
                  <select class="th-input" :value="tk.status" :disabled="acting"
                          @change="onStatus(tk, $event.target.value)">
                    <option>Open</option>
                    <option>In Progress</option>
                    <option>In Review</option>
                    <option>Resolved</option>
                  </select>
                </div>
              </div>

              <div v-if="detail && detail.comments.length" class="th-comments">
                <div v-for="(c, i) in detail.comments.slice(-3)" :key="i" class="th-comment">
                  <b>{{ String(c.author).split("@")[0] }}</b>: {{ c.message }}
                </div>
              </div>

              <div class="th-files" style="margin-top: 8px">
                <input v-model="commentText" class="th-input" placeholder="Add a comment…"
                       @keydown.enter="onComment(tk)" />
                <button class="th-btn th-btn-sm" :disabled="acting || !commentText.trim()"
                        @click="onComment(tk)">Send</button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="tab === 'new' && sent" class="th-done">
          <div class="th-done-icon">✓</div>
          <div class="th-done-text">
            Ticket <b>{{ sent }}</b> created.
            <a href="/taskhub" target="_blank" rel="noopener">Open Task Hub →</a>
          </div>
          <button class="th-btn th-btn-primary" @click="reset">Report another</button>
        </div>

        <div v-else-if="tab === 'new'" class="th-body">
          <label class="th-label">Title *</label>
          <input
            ref="titleEl"
            v-model="form.title"
            class="th-input"
            placeholder="Short summary of the problem or task"
            maxlength="180"
            @keydown.enter="submit"
          />

          <div class="th-row">
            <div class="th-col">
              <label class="th-label">Type</label>
              <select v-model="form.ticket_type" class="th-input">
                <option>Problem</option>
                <option>Task</option>
                <option>Request</option>
              </select>
            </div>
            <div class="th-col">
              <label class="th-label">Priority</label>
              <select v-model="form.priority" class="th-input">
                <option>Urgent</option>
                <option>High</option>
                <option>Medium</option>
                <option>Low</option>
              </select>
            </div>
          </div>

          <label class="th-label">Details</label>
          <textarea
            v-model="form.description"
            class="th-input th-textarea"
            rows="3"
            placeholder="What happened? Steps, order numbers, links…"
          />
          <div v-if="!aiHidden" class="th-ai">
            <button
              v-if="!aiPreview"
              type="button"
              class="th-btn th-btn-sm"
              :disabled="aiBusy || !form.description.trim()"
              @click="aiPolish"
            >
              {{ aiBusy ? "✨ Rewriting…" : "✨ Rewrite in English" }}
            </button>
            <div v-else class="th-ai-preview">
              <div class="th-ai-tag">✨ AI suggestion</div>
              <div class="th-ai-text">{{ aiPreview }}</div>
              <div class="th-ai-actions">
                <button type="button" class="th-btn th-btn-sm th-btn-primary" @click="aiApply">
                  Use suggestion
                </button>
                <button type="button" class="th-btn th-btn-sm" @click="aiPreview = ''">
                  Keep original
                </button>
              </div>
            </div>
          </div>

          <label class="th-label">Attachments</label>
          <input
            ref="fileEl"
            type="file"
            multiple
            accept="image/*,.pdf,.csv,.xlsx,.xls,.docx,.doc,.txt,.zip,.mp4,.mov,.webm"
            style="display: none"
            @change="onPickFiles"
          />
          <div class="th-files">
            <button type="button" class="th-btn th-btn-sm" @click="fileEl && fileEl.click()">
              📎 Add photo / file
            </button>
            <span v-for="(f, i) in files" :key="i" class="th-file-chip">
              {{ f.name }}
              <button type="button" class="th-file-x" @click="files.splice(i, 1)">✕</button>
            </span>
          </div>

          <div class="th-context">🔗 Will link to: <b>{{ contextLabel }}</b></div>

          <p v-if="error" class="th-error">{{ error }}</p>

          <div class="th-actions">
            <button class="th-btn" @click="close">Cancel</button>
            <button
              class="th-btn th-btn-primary"
              :disabled="busy || !form.title.trim()"
              @click="submit"
            >
              {{ busy ? "Sending…" : "Create Ticket" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// Task Hub drop-in reporter — self-contained on purpose: no imports from the
// host portal, own CSRF + fetch, scoped styles. Copy this file into any portal
// and mount <TaskHubWidget portal="Logistics" /> once in App.vue.
// Canonical copy lives in the task_hub repo: integration/TaskHubWidget.vue.
import { ref, reactive, computed, watch, nextTick, onMounted } from "vue";

const props = defineProps({
  // Which portal this widget is embedded in — one of the Hub's source portals.
  portal: { type: String, required: true },
  // Optional richer context injected by the host page (falls back to URL/title).
  linked: { type: Object, default: null }, // { doctype, name, label, url }
});

const open = ref(false);
const busy = ref(false);
const sent = ref("");
const error = ref("");
const titleEl = ref(null);
const fileEl = ref(null);
const files = ref([]);

function onPickFiles(e) {
  files.value.push(...Array.from(e.target.files || []));
  e.target.value = "";
}

// ── My tasks ───────────────────────────────────────────────────────────
// A purchasing (or any) employee shouldn't have to leave their portal to
// see what's on their plate: this panel reads the same Hub APIs the SPA
// uses, so status and comments stay in one system.
const tab = ref("tasks");
const scope = ref("all");
const tasks = ref([]);
const counts = reactive({ assigned_open: 0, reported_open: 0, breached: 0 });
const loadingTasks = ref(false);
const tasksError = ref("");
const expanded = ref("");
const detail = ref(null);
const commentText = ref("");
const acting = ref(false);

const PRIO_COLORS = {
  Urgent: "#e11d48", High: "#ea580c", Medium: "#0891b2", Low: "#64748b",
};
function prioColor(p) {
  return PRIO_COLORS[p] || PRIO_COLORS.Low;
}

// Descriptions are stored as HTML by the hub; render them as plain text
// here rather than injecting markup into the host portal.
function plain(html) {
  const d = document.createElement("div");
  d.innerHTML = html || "";
  return (d.textContent || "").trim().slice(0, 600);
}

async function hubCall(method, body) {
  const resp = await fetch(`/api/method/task_hub.api.${method}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": csrf(),
      Accept: "application/json",
    },
    body: JSON.stringify(body || {}),
  });
  const j = await resp.json().catch(() => ({}));
  if (!resp.ok || j.exc) {
    throw new Error(firstServerMessage(j) || "HTTP " + resp.status);
  }
  return j.message;
}

async function loadTasks() {
  loadingTasks.value = true;
  tasksError.value = "";
  try {
    const res = await hubCall("tickets.my_tasks", { scope: scope.value, limit: 25 });
    tasks.value = res.tasks || [];
    counts.assigned_open = res.assigned_open || 0;
    counts.reported_open = res.reported_open || 0;
    counts.breached = res.breached || 0;
  } catch (e) {
    tasksError.value = e.message || "Couldn't load your tasks.";
  } finally {
    loadingTasks.value = false;
  }
}

// Badge only — cheap enough to run on mount in every portal page load.
async function loadCounts() {
  try {
    const res = await hubCall("tickets.my_tasks", { scope: "assigned", limit: 1 });
    counts.assigned_open = res.assigned_open || 0;
    counts.reported_open = res.reported_open || 0;
    counts.breached = res.breached || 0;
  } catch {
    /* the widget stays silent if the hub isn't reachable */
  }
}

function openPanel() {
  open.value = true;
  if (tab.value === "tasks") loadTasks();
}

function switchTab(next) {
  tab.value = next;
  if (next === "tasks" && !tasks.value.length) loadTasks();
}

function setScope(next) {
  scope.value = next;
  expanded.value = "";
  loadTasks();
}

async function toggleTask(tk) {
  if (expanded.value === tk.name) {
    expanded.value = "";
    return;
  }
  expanded.value = tk.name;
  detail.value = null;
  commentText.value = "";
  try {
    detail.value = await hubCall("tickets.get_ticket", { name: tk.name });
  } catch (e) {
    tasksError.value = e.message;
  }
}

async function onStatus(tk, status) {
  if (acting.value || status === tk.status) return;
  acting.value = true;
  try {
    await hubCall("tickets.update_status", { name: tk.name, status });
    tk.status = status;
    // A resolved task leaves the open list — refresh so the badge agrees.
    if (["Resolved", "Closed", "Cancelled"].includes(status)) {
      expanded.value = "";
      await loadTasks();
    }
  } catch (e) {
    tasksError.value = e.message;
  } finally {
    acting.value = false;
  }
}

async function onComment(tk) {
  const msg = commentText.value.trim();
  if (!msg || acting.value) return;
  acting.value = true;
  try {
    await hubCall("tickets.add_comment", { name: tk.name, message: msg });
    commentText.value = "";
    detail.value = await hubCall("tickets.get_ticket", { name: tk.name });
  } catch (e) {
    tasksError.value = e.message;
  } finally {
    acting.value = false;
  }
}

onMounted(loadCounts);

const blank = () => ({
  title: "",
  ticket_type: "Problem",
  priority: "Medium",
  description: "",
});
const form = reactive(blank());

const contextLabel = computed(
  () => props.linked?.label || document.title || window.location.pathname
);

watch(open, async (v) => {
  if (v) {
    error.value = "";
    await nextTick();
    titleEl.value?.focus();
  }
});

function close() {
  open.value = false;
}

function reset() {
  Object.assign(form, blank());
  files.value = [];
  sent.value = "";
  error.value = "";
}

function csrf() {
  if (window.csrf_token) return window.csrf_token;
  const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

async function submit() {
  if (!form.title.trim() || busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    const payload = {
      title: form.title.trim(),
      ticket_type: form.ticket_type,
      priority: form.priority,
      description: form.description,
      source_portal: props.portal,
      linked_doctype: props.linked?.doctype || "",
      linked_name: props.linked?.name || "",
      linked_label: props.linked?.label || document.title || "",
      linked_url: props.linked?.url || window.location.href,
    };
    const resp = await fetch("/api/method/task_hub.api.tickets.create_ticket", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-Frappe-CSRF-Token": csrf(),
        Accept: "application/json",
      },
      body: JSON.stringify({ payload: JSON.stringify(payload) }),
    });
    const j = await resp.json().catch(() => ({}));
    if (!resp.ok || j.exc) {
      throw new Error(firstServerMessage(j) || "HTTP " + resp.status);
    }
    const ticketName = j.message?.name || "OK";

    // Upload attachments after the ticket exists; report partial failures.
    let failedUploads = 0;
    for (const f of files.value) {
      try {
        const fd = new FormData();
        fd.append("file", f, f.name);
        const up = await fetch(
          "/api/method/task_hub.api.tickets.upload_attachment?name=" +
            encodeURIComponent(ticketName),
          {
            method: "POST",
            credentials: "include",
            headers: { "X-Frappe-CSRF-Token": csrf() },
            body: fd,
          }
        );
        if (!up.ok) failedUploads++;
      } catch {
        failedUploads++;
      }
    }
    files.value = [];
    if (failedUploads) {
      error.value = `Ticket ${ticketName} created, but ${failedUploads} file(s) failed to upload.`;
    }

    sent.value = ticketName;
    Object.assign(form, blank());
    loadCounts();
  } catch (e) {
    error.value = e.message || "Could not create the ticket.";
  } finally {
    busy.value = false;
  }
}

// AI rewrite — same task_hub endpoint the Hub SPA uses. If the server says the
// feature is off (no key / toggle disabled), the button hides itself quietly.
const aiBusy = ref(false);
const aiPreview = ref("");
const aiHidden = ref(false);

async function aiPolish() {
  if (aiBusy.value || !form.description.trim()) return;
  aiBusy.value = true;
  try {
    const resp = await fetch("/api/method/task_hub.api.ai.polish_description", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-Frappe-CSRF-Token": csrf(),
        Accept: "application/json",
      },
      body: JSON.stringify({ text: form.description.trim() }),
    });
    const j = await resp.json().catch(() => ({}));
    if (!resp.ok || j.exc) {
      const msg = firstServerMessage(j) || "";
      if (msg.includes("not available")) {
        aiHidden.value = true;
        return;
      }
      throw new Error(msg || "HTTP " + resp.status);
    }
    aiPreview.value = (j.message && j.message.polished) || "";
  } catch (e) {
    error.value = e.message || "AI rewrite failed — please try again.";
  } finally {
    aiBusy.value = false;
  }
}

function aiApply() {
  if (aiPreview.value) form.description = aiPreview.value;
  aiPreview.value = "";
}

function firstServerMessage(j) {
  try {
    const arr = JSON.parse(j._server_messages || "[]");
    if (!arr.length) return "";
    const m = arr[0];
    return (typeof m === "string" ? JSON.parse(m) : m).message || "";
  } catch {
    return "";
  }
}
</script>

<style scoped>
.th-fab {
  position: fixed;
  bottom: 18px;
  left: 18px;
  z-index: 9000;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 14px;
  border: none;
  border-radius: 999px;
  background: #1c1917;
  color: #fff;
  font: 600 12.5px/1 "Inter", system-ui, sans-serif;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(28, 25, 23, 0.35);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.th-fab:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(28, 25, 23, 0.45);
}
.th-fab-icon {
  font-size: 13px;
}
.th-overlay {
  position: fixed;
  inset: 0;
  z-index: 9001;
  background: rgba(28, 25, 23, 0.45);
  display: flex;
  align-items: flex-end;
  justify-content: flex-start;
  padding: 18px;
}
.th-modal {
  width: 400px;
  max-width: calc(100vw - 36px);
  max-height: calc(100vh - 36px);
  overflow-y: auto;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 18px 50px rgba(28, 25, 23, 0.35);
  font-family: "Inter", system-ui, sans-serif;
}
.th-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 18px 12px;
  border-bottom: 1px solid #e7e5e4;
}
.th-title {
  font-size: 14.5px;
  font-weight: 700;
  color: #1c1917;
}
.th-sub {
  font-size: 11.5px;
  color: #a8a29e;
  margin-top: 2px;
}
.th-x {
  border: none;
  background: none;
  color: #a8a29e;
  font-size: 14px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 6px;
}
.th-x:hover {
  background: #e7e5e4;
}
.th-body {
  padding: 14px 18px 18px;
}
.th-label {
  display: block;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #78716c;
  margin: 10px 0 5px;
}
.th-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid #d6d3d1;
  border-radius: 8px;
  font: 400 13px/1.4 "Inter", system-ui, sans-serif;
  color: #1c1917;
  background: #fff;
  outline: none;
}
.th-input:focus {
  border-color: #e17f62;
  box-shadow: 0 0 0 3px rgba(212, 93, 62, 0.18);
}
.th-textarea {
  resize: vertical;
}
.th-row {
  display: flex;
  gap: 10px;
}
.th-col {
  flex: 1;
}
.th-files {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.th-btn-sm {
  padding: 6px 10px;
  font-size: 11.5px;
}
.th-ai {
  margin-top: 6px;
}
.th-ai-preview {
  border: 1px solid #f0c6b8;
  background: #fdf5f2;
  border-radius: 10px;
  padding: 10px 12px;
}
.th-ai-tag {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #c4492a;
  margin-bottom: 6px;
}
.th-ai-text {
  font-size: 12.5px;
  color: #292524;
  line-height: 1.55;
  white-space: pre-wrap;
}
.th-ai-actions {
  display: flex;
  gap: 6px;
  margin-top: 9px;
}
.th-file-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  padding: 4px 8px;
  background: #f5f5f4;
  border: 1px solid #e7e5e4;
  border-radius: 7px;
  font-size: 11px;
  color: #44403c;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.th-file-x {
  border: none;
  background: none;
  color: #a8a29e;
  cursor: pointer;
  font-size: 10px;
  padding: 0;
}
.th-file-x:hover {
  color: #e11d48;
}
.th-context {
  margin-top: 12px;
  padding: 7px 10px;
  background: #f5f5f4;
  border-radius: 8px;
  font-size: 11.5px;
  color: #78716c;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.th-error {
  margin: 10px 0 0;
  font-size: 12px;
  color: #e11d48;
}
.th-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 14px;
}
.th-btn {
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid #d6d3d1;
  background: #fff;
  color: #44403c;
  font: 600 12.5px/1 "Inter", system-ui, sans-serif;
  cursor: pointer;
}
.th-btn:hover {
  background: #f5f5f4;
}
.th-btn-primary {
  border-color: transparent;
  background: #d45d3e;
  color: #fff;
}
.th-btn-primary:hover {
  background: #c4492a;
}
.th-btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.th-done {
  padding: 26px 18px;
  text-align: center;
}
.th-done-icon {
  width: 40px;
  height: 40px;
  margin: 0 auto 10px;
  border-radius: 999px;
  background: #ecfdf5;
  color: #059669;
  font-size: 20px;
  font-weight: 700;
  display: grid;
  place-items: center;
}
.th-done-text {
  font-size: 13px;
  color: #44403c;
  margin-bottom: 14px;
}
.th-done-text a {
  color: #c4492a;
  text-decoration: none;
  font-weight: 600;
}

/* ── tabs + my-tasks list ─────────────────────────────────────────── */
.th-fab-badge {
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  border-radius: 999px;
  background: #d45d3e;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 17px;
  text-align: center;
}
.th-fab-badge.hot {
  background: #e11d48;
}
.th-tabs {
  display: flex;
  gap: 2px;
  padding: 0 18px;
  border-bottom: 1px solid #e7e5e4;
}
.th-tabs button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 10px;
  border: none;
  background: none;
  border-bottom: 2px solid transparent;
  font: 600 12.5px/1 "Inter", system-ui, sans-serif;
  color: #78716c;
  cursor: pointer;
}
.th-tabs button.on {
  color: #c4492a;
  border-bottom-color: #d45d3e;
}
.th-tabcount {
  min-width: 16px;
  padding: 1px 5px;
  border-radius: 999px;
  background: #f5f5f4;
  font-size: 10px;
  color: #57534e;
}
.th-scope {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.th-scope button {
  padding: 4px 9px;
  border: 1px solid #e7e5e4;
  border-radius: 999px;
  background: #fff;
  font: 600 11px/1 "Inter", system-ui, sans-serif;
  color: #78716c;
  cursor: pointer;
}
.th-scope button.on {
  background: #fdf1ed;
  border-color: #f0c6b8;
  color: #c4492a;
}
.th-hublink {
  margin-inline-start: auto;
  font-size: 11px;
  color: #d45d3e;
  text-decoration: none;
}
.th-muted {
  font-size: 12.5px;
  color: #a8a29e;
  padding: 10px 0;
  margin: 0;
}
.th-task {
  border: 1px solid #e7e5e4;
  border-radius: 10px;
  margin-bottom: 7px;
  overflow: hidden;
}
.th-task-head {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  width: 100%;
  padding: 9px 11px;
  border: none;
  background: #fff;
  text-align: start;
  cursor: pointer;
}
.th-task-head:hover {
  background: #fafaf9;
}
.th-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  margin-top: 5px;
  flex: none;
}
.th-task-main {
  min-width: 0;
  flex: 1;
}
.th-task-title {
  display: block;
  font: 600 12.5px/1.35 "Inter", system-ui, sans-serif;
  color: #1c1917;
}
.th-task-meta {
  display: block;
  margin-top: 2px;
  font-size: 10.5px;
  color: #a8a29e;
}
.th-late {
  color: #e11d48;
}
.th-task-body {
  padding: 10px 11px 12px;
  border-top: 1px solid #f5f5f4;
  background: #fafaf9;
}
.th-task-desc {
  margin: 0 0 9px;
  font-size: 12px;
  line-height: 1.55;
  color: #44403c;
  white-space: pre-wrap;
}
.th-comments {
  margin-top: 9px;
  padding-top: 8px;
  border-top: 1px solid #e7e5e4;
}
.th-comment {
  font-size: 11.5px;
  color: #57534e;
  line-height: 1.5;
  margin-bottom: 4px;
}
</style>
