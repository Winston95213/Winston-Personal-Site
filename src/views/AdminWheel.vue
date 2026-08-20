<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";

type WheelSummary = { id: string; token: string; subject: string; isActive: boolean; options: { id: string; text: string }[]; participantCount: number; decision: { text: string; decidedAt: string | null } | null; updatedAt: string };

const wheels = ref<WheelSummary[]>([]);
const subject = ref("");
const startingOptions = ref("");
const loading = ref(true);
const creating = ref(false);
const error = ref("");
const created = ref<WheelSummary | null>(null);
const options = computed(() => startingOptions.value.split("\n").map((value) => value.trim()).filter(Boolean));

function shareLink(wheel: Pick<WheelSummary, "token">) { return `${window.location.origin}/wheel/${wheel.token}`; }
async function copy(wheel: WheelSummary) {
  try { await navigator.clipboard.writeText(shareLink(wheel)); error.value = "Invite link copied."; }
  catch { error.value = "Copy the invite link from the address bar."; }
}
async function load() {
  loading.value = true;
  try { wheels.value = (await api<{ wheels: WheelSummary[] }>("/owner/wheels/")).wheels; }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "We couldn’t load your decision wheels."; }
  finally { loading.value = false; }
}
async function create() {
  error.value = "";
  if (subject.value.trim().length < 2) { error.value = "Add a short subject so everyone knows what they’re deciding."; return; }
  creating.value = true;
  try {
    const response = await api<{ wheel: WheelSummary }>("/owner/wheels/", "POST", { subject: subject.value, options: options.value });
    created.value = response.wheel;
    wheels.value.unshift(response.wheel);
    subject.value = ""; startingOptions.value = "";
  } catch (caught) { error.value = caught instanceof Error ? caught.message : "We couldn’t create this wheel."; }
  finally { creating.value = false; }
}
onMounted(load);
</script>

<template>
  <main id="main" class="wheel-admin-page">
    <section class="wheel-admin-shell">
      <header class="wheel-console-header">
        <div><div class="eyebrow">Owner dashboard</div><h1>Decision wheel</h1><p>Start a question, share one link, and let the group decide together.</p></div>
        <div class="actions"><RouterLink class="button secondary" to="/admin/chat">Private chats</RouterLink><RouterLink class="button secondary" to="/admin/schedule">Scheduling</RouterLink></div>
      </header>

      <p v-if="error" class="wheel-feedback" role="status">{{ error }} <RouterLink v-if="error.includes('Sign in')" to="/admin/chat">Open owner sign-in</RouterLink></p>
      <section v-if="created" class="wheel-created-card" aria-live="polite">
        <div class="wheel-created-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 12a8 8 0 1 0 16 0A8 8 0 1 0 4 12Z"/><path d="M12 4v16M4 12h16"/></svg></div>
        <div><div class="eyebrow">Ready to invite</div><h2>{{ created.subject }}</h2><p>Send this link to your group. They can enter their name and add their own ideas.</p></div>
        <div class="wheel-share-row"><code>{{ shareLink(created) }}</code><button class="button" type="button" @click="copy(created)">Copy invite link</button></div>
      </section>

      <section class="wheel-admin-grid">
        <form class="wheel-create-card" @submit.prevent="create">
          <div><div class="eyebrow">New decision</div><h2>What should the group decide?</h2><p>Keep it simple. People can add more choices after they join.</p></div>
          <label class="field"><span>Subject</span><input v-model="subject" maxlength="180" autocomplete="off" placeholder="Where should we eat tonight?" required><small>This becomes the title your invitees see.</small></label>
          <label class="field"><span>Starting options <i>optional</i></span><textarea v-model="startingOptions" maxlength="3650" placeholder="Hotpot&#10;Sushi&#10;Pizza"></textarea><small>One option per line. Add none if you want the group to suggest everything.</small></label>
          <div class="wheel-create-footer"><span>{{ options.length }} starter {{ options.length === 1 ? 'option' : 'options' }}</span><button class="button" type="submit" :disabled="creating">{{ creating ? 'Creating…' : 'Create decision wheel' }}</button></div>
        </form>
        <section class="wheel-list-card">
          <header><div><h2>Your wheels</h2><p>Open a link any time to see the latest group decision.</p></div><button class="text-button" type="button" :disabled="loading" @click="load">{{ loading ? 'Refreshing…' : 'Refresh' }}</button></header>
          <div v-if="loading" class="wheel-empty">Loading decision wheels…</div>
          <div v-else-if="wheels.length" class="wheel-list"><article v-for="wheel in wheels" :key="wheel.id"><div><b>{{ wheel.subject }}</b><small>{{ wheel.options.length }} options · {{ wheel.participantCount }} {{ wheel.participantCount === 1 ? 'person' : 'people' }}</small></div><div class="wheel-list-actions"><span :class="['wheel-state', { closed: !wheel.isActive }]">{{ wheel.isActive ? 'Open' : 'Closed' }}</span><button class="text-button" type="button" @click="copy(wheel)">Copy link</button><RouterLink class="text-button" :to="`/wheel/${wheel.token}`">Open</RouterLink></div></article></div>
          <div v-else class="wheel-empty"><strong>No decision wheels yet.</strong><p>Create one whenever a group needs a quick, fair choice.</p></div>
        </section>
      </section>
    </section>
  </main>
</template>
