<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";
import { formatDay, formatTime } from "../lib/scheduling";

type EventSummary = { id: string; token: string; title: string; timezone: string; status: string; responses: number; bestTime: string | null; bestAvailable: number; updatedAt: string; responseDeadline: string | null };
const events = ref<EventSummary[]>([]);
const error = ref("");
const loading = ref(true);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    events.value = (await api<{ events: EventSummary[] }>("/owner/schedule/events/")).events;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "We couldn’t load your scheduling polls.";
  } finally {
    loading.value = false;
  }
}

function bestTime(event: EventSummary) { return event.bestTime ? `${formatDay(event.bestTime, event.timezone)} · ${formatTime(event.bestTime, event.timezone)}` : "Waiting for responses"; }
onMounted(load);
</script>

<template>
  <main id="main" class="schedule-admin-page">
    <section class="schedule-admin-shell">
      <header class="schedule-console-header"><div><div class="eyebrow">Owner dashboard</div><h1>Scheduling</h1><p>Create a poll, share one private link, and find a time that works.</p></div><div class="actions"><RouterLink class="button secondary" to="/admin/chat">Private chats</RouterLink><RouterLink class="button" to="/admin/schedule/new">Create event</RouterLink></div></header>
      <p v-if="error" class="schedule-error" role="alert">{{ error }} <RouterLink to="/admin/chat">Sign in through Private chats</RouterLink></p>
      <section class="schedule-panel"><header class="schedule-panel-header"><h2>Your polls</h2><button class="text-button" type="button" :disabled="loading" @click="load">{{ loading ? 'Refreshing…' : 'Refresh' }}</button></header>
        <div v-if="loading" class="schedule-loading">Loading scheduling polls…</div>
        <div v-else-if="events.length" class="schedule-event-list"><RouterLink v-for="event in events" :key="event.id" class="schedule-event-row" :to="`/admin/schedule/${event.id}`"><span class="schedule-event-name"><b>{{ event.title }}</b><small>{{ event.timezone }}</small></span><span><b :class="['schedule-status', event.status.toLowerCase()]">{{ event.status }}</b><small>{{ event.responses }} {{ event.responses === 1 ? 'response' : 'responses' }}</small></span><span class="schedule-best"><small>Best time</small><b>{{ bestTime(event) }}</b></span></RouterLink></div>
        <div v-else class="schedule-empty"><strong>No scheduling polls yet.</strong><p>Create a poll and share it with people to find a time that works.</p><RouterLink class="button" to="/admin/schedule/new">Create scheduling poll</RouterLink></div>
      </section>
    </section>
  </main>
</template>
