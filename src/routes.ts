import type { RouteRecordRaw } from "vue-router";
import Home from "./views/Home.vue";
import Static from "./views/Static.vue";
import Project from "./views/Project.vue";
import NotFound from "./views/NotFound.vue";
import ChatRoom from "./views/ChatRoom.vue";
import AdminChat from "./views/AdminChat.vue";
import AdminSchedule from "./views/AdminSchedule.vue";
import ScheduleCreate from "./views/ScheduleCreate.vue";
import ScheduleResults from "./views/ScheduleResults.vue";
import SchedulePoll from "./views/SchedulePoll.vue";
import AdminWheel from "./views/AdminWheel.vue";
import DecisionWheel from "./views/DecisionWheel.vue";

export const routes: RouteRecordRaw[] = [
  { path: "/", component: Home, meta: { title: "Software Engineer" } },
  { path: "/about", component: Static, props: { page: "about" }, meta: { title: "About" } },
  { path: "/experience", component: Static, props: { page: "experience" }, meta: { title: "Experience" } },
  { path: "/education", component: Static, props: { page: "education" }, meta: { title: "Education" } },
  { path: "/projects", component: Static, props: { page: "projects" }, meta: { title: "Projects" } },
  { path: "/projects/:slug", component: Project, props: true, meta: { title: "Project" } },
  { path: "/resume", component: Static, props: { page: "resume" }, meta: { title: "Resume" } },
  { path: "/contact", component: Static, props: { page: "contact" }, meta: { title: "Contact" } },
  { path: "/chat/:token", component: ChatRoom, props: true, meta: { title: "Private conversation" } },
  { path: "/admin/chat", component: AdminChat, meta: { title: "Private chats" } },
  { path: "/admin/wheel", component: AdminWheel, meta: { title: "Decision wheel" } },
  { path: "/admin/schedule", component: AdminSchedule, meta: { title: "Scheduling" } },
  { path: "/admin/schedule/new", component: ScheduleCreate, meta: { title: "Create scheduling poll" } },
  { path: "/admin/schedule/:id", component: ScheduleResults, props: true, meta: { title: "Scheduling results" } },
  { path: "/schedule/:token", component: SchedulePoll, props: true, meta: { title: "Scheduling poll" } },
  { path: "/wheel/:token", component: DecisionWheel, props: true, meta: { title: "Decision wheel" } },
  { path: "/:pathMatch(.*)*", component: NotFound, meta: { title: "Page not found" } },
];
