import { createRouter, createWebHistory } from "vue-router";
import AppLayout from "@/components/layout/AppLayout.vue";

const Dashboard = () => import("@/pages/Dashboard.vue");
const NotFound  = () => import("@/pages/NotFound.vue");

const routes = [
  {
    path: "/logistics",
    component: AppLayout,
    children: [
      { path: "", name: "Dashboard", component: Dashboard, meta: { title: "Dashboard" } },
    ],
  },
  { path: "/:pathMatch(.*)*", name: "NotFound", component: NotFound },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.afterEach((to) => {
  if (to.meta?.title) {
    document.title = `${to.meta.title} · Justyol Logistics`;
  }
});

export default router;
