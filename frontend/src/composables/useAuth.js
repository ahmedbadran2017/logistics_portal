import { ref, computed } from "vue";
import { api } from "@/lib/resource";

// Module-level singletons so every component shares one auth state.
const user = ref(null);        // ERPNext login id (e.g. marouane@justyol.com)
const fullName = ref("");
const role = ref(null);        // resolved logistics role
const roles = ref([]);         // all logistics roles this user has (multi-role)
const zone = ref("");
const hiddenPages = ref([]);   // route names a manager hid for THIS user
const ccAdmin = ref({ cf: false, rs: false, cs: false });
const isLoading = ref(true);
const isInitialized = ref(false);

const isLoggedIn = computed(() => !!user.value && user.value !== "Guest");

// View-as (manager UX tool): render the portal through a member's role and,
// on the per-agent-scoped endpoints, their data (lib/resource appends
// `as_user`). Local + read-safe: the session stays the manager's; any action
// still runs and attributes as the manager.
const viewAs = ref(null);      // { user, fullName, role } or null
try {
  const raw = localStorage.getItem("lp_view_as_meta");
  if (raw) viewAs.value = JSON.parse(raw);
} catch (_) { /* corrupted → off */ }

function setViewAs(member) {
  try {
    if (member) {
      localStorage.setItem("lp_view_as", member.user);
      localStorage.setItem("lp_view_as_meta", JSON.stringify(member));
    } else {
      localStorage.removeItem("lp_view_as");
      localStorage.removeItem("lp_view_as_meta");
    }
  } catch (_) { /* private mode */ }
  // Hard reload: the role change swaps home/nav/portal side entirely.
  window.location.href = member && ["confirmation", "cs", "tracking"].includes(member.role)
    ? "/confirmation/home" : (member ? "/logistics/home" : window.location.pathname);
}

async function init(force = false) {
  if (isInitialized.value && !force) return;
  isLoading.value = true;
  try {
    const boot = await api("auth.get_boot");
    user.value = boot.user;
    fullName.value = boot.full_name || boot.user;
    role.value = boot.role;
    roles.value = boot.roles || (boot.role ? [boot.role] : []);
    // A non-manager must never carry a stale view-as marker.
    if (viewAs.value && boot.role !== "manager") setViewAs(null);
    else if (viewAs.value) {
      role.value = viewAs.value.role;
      // Fidelity: while viewing as an agent, admin-only surfaces hide too.
      ccAdmin.value = { cf: false, rs: false, cs: false };
    }
    zone.value = boot.zone || "";
    hiddenPages.value = Array.isArray(boot.hiddenPages) ? boot.hiddenPages : [];
    ccAdmin.value = boot.ccAdmin || { cf: false, rs: false, cs: false };
    // The page template can't inject the CSRF token reliably; the boot endpoint
    // returns it so POST writes (apiPost) work from the browser session.
    if (boot.csrf_token) window.csrf_token = boot.csrf_token;
  } catch (e) {
    // Dev-only: with no Frappe backend running (preview/design work), fall back to
    // a demo identity so the SPA is fully browsable. Never reached in production
    // (import.meta.env.DEV is false in the Frappe bundle build).
    if (import.meta.env.DEV) {
      user.value = "demo@justyol.com";
      fullName.value = "Eman (Demo)";
      roles.value = ["manager", "dispatcher", "picker", "packer", "returns"];
      role.value = localStorage.getItem("lp.role") || "manager";
      zone.value = "Soft WH";
    } else {
      user.value = "Guest";
      role.value = null;
    }
  } finally {
    isLoading.value = false;
    isInitialized.value = true;
  }
}

async function login(usr, pwd) {
  const res = await fetch("/api/method/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ usr, pwd }),
  });
  if (!res.ok) throw new Error("Invalid credentials");
  await init(true);
}

async function logout() {
  // CSRF header: Frappe rejects tokenless POSTs once a session token exists.
  const token = window.csrf_token || (window.frappe_boot && window.frappe_boot.csrf_token) || "";
  await fetch("/api/method/logout", {
    method: "POST",
    headers: { "X-Frappe-CSRF-Token": token, "X-Requested-With": "XMLHttpRequest" },
  });
  user.value = "Guest";
  role.value = null;
  isInitialized.value = false;
}

/** Switch active role for multi-role users (remembered client-side). */
function setActiveRole(next) {
  if (roles.value.includes(next)) {
    role.value = next;
    localStorage.setItem("lp.role", next);
  }
}

export function useAuth() {
  return {
    user, fullName, role, roles, zone, hiddenPages, ccAdmin, isLoading, isLoggedIn, isInitialized,
    init, login, logout, setActiveRole, viewAs, setViewAs,
  };
}
