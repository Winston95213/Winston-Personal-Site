<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView } from "vue-router";
import { profile } from "./data";

const open = ref(false);
const scrolled = ref(false);
const pages = [["About", "/about"], ["Experience", "/experience"], ["Projects", "/projects"], ["Resume", "/resume"], ["Contact", "/contact"]] as const;
function closeMenu() { open.value = false; }
function updateHeader() { scrolled.value = window.scrollY > 8; }
onMounted(() => { window.addEventListener("scroll", updateHeader, { passive: true }); updateHeader(); });
onBeforeUnmount(() => window.removeEventListener("scroll", updateHeader));
watch(open, (value) => document.body.classList.toggle("menu-open", value));
</script>

<template>
  <a class="skip-link" href="#main">Skip to content</a>
  <header :class="['site-header', { scrolled }]">
    <nav class="shell nav" aria-label="Main navigation">
      <RouterLink class="brand" to="/" @click="closeMenu">{{ profile.draft ? "Portfolio" : profile.name }}<span class="brand-mark">.</span></RouterLink>
      <div class="nav-links">
        <RouterLink v-for="[label, to] in pages" :key="to" :to="to">{{ label }}</RouterLink>
      </div>
      <button class="menu-button" type="button" :aria-expanded="open" aria-controls="mobile-navigation" @click="open = !open">{{ open ? "Close" : "Menu" }}</button>
    </nav>
  </header>
  <nav id="mobile-navigation" :class="['mobile-menu', { open }]" aria-label="Mobile navigation">
    <RouterLink v-for="[label, to] in pages" :key="to" :to="to" @click="closeMenu">{{ label }}</RouterLink>
    <div class="mobile-social">
      <a v-if="profile.github" class="external" :href="profile.github" target="_blank" rel="noopener noreferrer">GitHub</a>
      <a v-if="profile.linkedin" class="external" :href="profile.linkedin" target="_blank" rel="noopener noreferrer">LinkedIn</a>
      <a v-if="profile.email" :href="`mailto:${profile.email}`">Email</a>
    </div>
  </nav>
  <RouterView />
  <footer class="site-footer">
    <div class="shell footer-inner">
      <div><div class="footer-title">{{ profile.draft ? "Portfolio" : profile.name }}</div><div class="copyright">Software engineering · © {{ new Date().getFullYear() }}</div></div>
      <div class="footer-links"><a v-if="profile.github" class="external" :href="profile.github" target="_blank" rel="noopener noreferrer">GitHub</a><a v-if="profile.linkedin" class="external" :href="profile.linkedin" target="_blank" rel="noopener noreferrer">LinkedIn</a><a v-if="profile.email" :href="`mailto:${profile.email}`">{{ profile.email }}</a></div>
    </div>
  </footer>
</template>
