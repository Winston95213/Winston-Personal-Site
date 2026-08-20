import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Port 8080 is used by another local web service on this Mac. Keep Django on
// its own loopback-only port and let Vite proxy API calls to it.
const djangoServer = "http://127.0.0.1:8081";

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": { target: djangoServer },
      "/media": { target: djangoServer }
    }
  }
});
