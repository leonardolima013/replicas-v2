import { createRouter, createWebHistory } from "vue-router";
import Login from "../views/Login.vue";
import ServiceSelector from "../views/ServiceSelector.vue";
import Dashboard from "../views/Dashboard.vue";
import DataValidationTest from "../views/DataValidationTest.vue";

const routes = [
  {
    path: "/",
    redirect: "/login",
  },
  {
    path: "/login",
    name: "Login",
    component: Login,
  },
  {
    path: "/service-selector",
    name: "ServiceSelector",
    component: ServiceSelector,
    meta: { requiresAuth: true },
  },
  {
    path: "/dashboard",
    name: "Dashboard",
    component: Dashboard,
    meta: { requiresAuth: true },
  },
  {
    path: "/data-validation-test",
    name: "DataValidationTest",
    component: DataValidationTest,
    meta: { requiresAuth: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Guard de navegação para rotas protegidas
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("access_token");

  if (to.meta.requiresAuth && !token) {
    next("/login");
  } else if (to.path === "/login" && token) {
    next("/service-selector");
  } else {
    next();
  }
});

export default router;
