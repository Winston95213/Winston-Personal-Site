import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import { routes } from "./routes";
import { profile } from "./data";
import "./style.css";
const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) });
router.afterEach((to) => { document.title = `${String(to.meta.title ?? "Portfolio")} — ${profile.draft ? "Portfolio" : profile.name}`; const robots=document.querySelector('meta[name="robots"]'); if(robots)robots.setAttribute("content",to.path.startsWith("/chat/")||to.path.startsWith("/schedule/")||to.path.startsWith("/admin/")?"noindex, nofollow":"index, follow"); });
createApp(App).use(router).mount("#app");
