<template>
  <div class="th-widget" style="display: contents">
    <!-- Floating trigger -->
    <button
      v-if="!open"
      class="th-fab"
      :title="`Report to Task Hub (${portal})`"
      @click="open = true"
    >
      <span class="th-fab-icon">⚑</span>
      <span class="th-fab-label">Report</span>
    </button>

    <!-- Modal -->
    <div v-if="open" class="th-overlay" @click.self="close">
      <div class="th-modal">
        <div class="th-head">
          <div>
            <div class="th-title">New Task Hub ticket</div>
            <div class="th-sub">{{ portal }} portal · goes to the central hub</div>
          </div>
          <button class="th-x" @click="close">✕</button>
        </div>

        <div v-if="sent" class="th-done">
          <div class="th-done-icon">✓</div>
          <div class="th-done-text">
            Ticket <b>{{ sent }}</b> created.
            <a href="/taskhub" target="_blank" rel="noopener">Open Task Hub →</a>
          </div>
          <button class="th-btn th-btn-primary" @click="reset">Report another</button>
        </div>

        <div v-else class="th-body">
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
import { ref, reactive, computed, watch, nextTick } from "vue";

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
  } catch (e) {
    error.value = e.message || "Could not create the ticket.";
  } finally {
    busy.value = false;
  }
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
</style>
