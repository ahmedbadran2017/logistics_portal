import { ref, computed } from "vue";
import { api } from "@/lib/resource";

// Module-level singletons so every component shares one auth state.
const user = ref(null);        // ERPNext login id (e.g. marouane@justyol.com)
const fullName = ref("");
const role = ref(null);        // resolved logistics role
const roles = ref([]);         // all logistics roles this user has (multi-role)
const zone = ref("");
const isLoading = ref(true);
const isInitialized = ref(false);

const isLoggedIn = computed(() => !!user.value && user.value !== "Guest");

async function init(force = false) {
  if (isInitialized.value && !force) return;
  isLoading.value = true;
  try {
    const boot = await api("auth.get_boot");
    user.value = boot.user;
    fullName.value = boot.full_name || boot.user;
    role.value = boot.role;
    roles.value = boot.roles || (boot.role ? [boot.role] : []);
    zone.value = boot.zone || "";
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
  await fetch("/api/method/logout", { method: "POST" });
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
    user, fullName, role, roles, zone, isLoading, isLoggedIn, isInitialized,
    init, login, logout, setActiveRole,
  };
}
