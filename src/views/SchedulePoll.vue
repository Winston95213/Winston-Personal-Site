<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { api } from "../api";
import AvailabilityGrid from "../components/AvailabilityGrid.vue";
import { browserTimezone, formatRange, formatTimezone, type AvailabilityCount, type ScheduleSlot } from "../lib/scheduling";

type Meeting = { startAt: string; endAt: string; icsUrl: string; googleCalendarUrl: string };
type Poll = { title: string; description: string; location: string; meetingUrl: string; timezone: string; status: string; responseDeadline: string | null; allowParticipantEditing: boolean; availabilityVisibility: string; slots: ScheduleSlot[]; aggregate?: Record<string, AvailabilityCount>; availableNames?: Record<string, string[]>; confirmedMeeting: Meeting | null; participant?: { name: string; email: string; selectedSlotIds: string[] } };
const props = defineProps<{ token: string }>();
const poll = ref<Poll | null>(null);
const loading = ref(true);
const error = ref("");
const name = ref("");
const email = ref("");
const participantReady = ref(false);
const selectedIds = ref<string[]>([]);
const saving = ref(false);
const saved = ref(false);
const displayTimezone = ref("");
const dirty = computed(() => participantReady.value && !saved.value);
const statusMessage = computed(() => poll.value?.status === "EXPIRED" ? "The response deadline has passed." : poll.value?.status === "CLOSED" ? "This scheduling poll is closed." : poll.value?.status === "CANCELLED" ? "This meeting has been cancelled." : "This scheduling poll is no longer accepting responses.");

async function load() {
  loading.value = true;
  try {
    const result = await api<{ event: Poll }>(`/schedule/${props.token}/`);
    poll.value = result.event;
    displayTimezone.value ||= result.event.timezone;
    if (result.event.participant) {
      participantReady.value = true;
      name.value = result.event.participant.name;
      email.value = result.event.participant.email;
      selectedIds.value = result.event.participant.selectedSlotIds;
      saved.value = true;
    }
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "We couldn’t load this schedule. Please try again.";
  } finally {
    loading.value = false;
  }
}

async function begin() {
  error.value = "";
  saving.value = true;
  try {
    const result = await api<{ participant: { name: string; email: string }; selectedSlotIds: string[] }>(`/schedule/${props.token}/participant/`, "POST", { name: name.value, email: email.value });
    name.value = result.participant.name;
    email.value = result.participant.email;
    selectedIds.value = result.selectedSlotIds;
    participantReady.value = true;
    saved.value = result.selectedSlotIds.length > 0;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Please enter your name again to continue.";
  } finally {
    saving.value = false;
  }
}

function toggle(slotId: string) { selectedIds.value = selectedIds.value.includes(slotId) ? selectedIds.value.filter((value) => value !== slotId) : [...selectedIds.value, slotId]; saved.value = false; }
function replace(slotIds: string[]) { selectedIds.value = slotIds; saved.value = false; }
async function submit() {
  error.value = "";
  saving.value = true;
  try {
    const result = await api<{ selectedSlotIds: string[] }>(`/schedule/${props.token}/availability/`, "PUT", { slotIds: selectedIds.value });
    selectedIds.value = result.selectedSlotIds;
    saved.value = true;
    await load();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Your availability wasn’t saved. Please try again.";
  } finally {
    saving.value = false;
  }
}

function leaving(event: BeforeUnloadEvent) { if (dirty.value) { event.preventDefault(); event.returnValue = ""; } }
watch(displayTimezone, () => { /* The grid derives labels from this explicit choice. */ });
onMounted(() => { window.addEventListener("beforeunload", leaving); load(); });
onBeforeUnmount(() => window.removeEventListener("beforeunload", leaving));
</script>

<template>
  <main id="main" class="schedule-poll-page">
    <section v-if="loading" class="schedule-public-card schedule-loading">Loading scheduling poll…</section>
    <section v-else-if="error && !poll" class="schedule-public-card schedule-public-error"><div class="eyebrow">Scheduling unavailable</div><h1>This link isn’t available.</h1><p>{{ error }}</p></section>
    <section v-else-if="poll" class="schedule-public-shell">
      <header class="schedule-public-header"><div><div class="eyebrow">Scheduling poll</div><h1>{{ poll.title }}</h1><p v-if="poll.description">{{ poll.description }}</p></div><div class="timezone-card"><span>Times shown in</span><select v-model="displayTimezone"><option :value="poll.timezone">Event timezone · {{ poll.timezone }}</option><option v-if="browserTimezone() !== poll.timezone" :value="browserTimezone()">My timezone · {{ browserTimezone() }}</option></select><small>{{ formatTimezone(displayTimezone) }}</small></div></header>

      <section v-if="poll.confirmedMeeting" class="schedule-confirmed"><div class="schedule-confirmed-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="m5 12.5 4.2 4.2L19.5 6.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div><div class="eyebrow">Meeting confirmed</div><h2>{{ formatRange(poll.confirmedMeeting.startAt, poll.confirmedMeeting.endAt, displayTimezone) }}</h2><p>{{ formatTimezone(displayTimezone) }}</p><p v-if="poll.location">{{ poll.location }}</p><a v-if="poll.meetingUrl" class="text-link external" :href="poll.meetingUrl" target="_blank" rel="noopener noreferrer">Join meeting</a></div><div class="confirmed-actions"><a class="button" :href="poll.confirmedMeeting.icsUrl">Add to Calendar</a><a class="button secondary" :href="poll.confirmedMeeting.googleCalendarUrl" target="_blank" rel="noopener noreferrer">Google Calendar</a></div></section>

      <section v-else-if="poll.status !== 'OPEN'" class="schedule-closed"><div class="eyebrow">Scheduling closed</div><h2>{{ statusMessage }}</h2><p v-if="poll.responseDeadline">The response deadline was {{ new Date(poll.responseDeadline).toLocaleString() }}.</p></section>

      <template v-else>
        <section v-if="!participantReady" class="schedule-participant-card"><div><h2>Find a time that works.</h2><p>Select every time you are available. No account is needed.</p></div><form class="schedule-name-form" @submit.prevent="begin"><label class="field">Your name<input v-model="name" required maxlength="60" autocomplete="name" /></label><label class="field">Email <small>Optional — only used for a future meeting confirmation.</small><input v-model="email" type="email" maxlength="254" autocomplete="email" /></label><p v-if="error" class="schedule-error" role="alert">{{ error }}</p><button class="button" :disabled="saving">{{ saving ? 'Starting…' : 'Choose availability' }}</button></form></section>
        <section v-else class="schedule-selection-card"><header><div><h2>Select every time you’re available.</h2><p>{{ selectedIds.length }} {{ selectedIds.length === 1 ? 'time selected' : 'times selected' }}<span v-if="!saved"> · Unsaved changes</span></p></div><button v-if="poll.allowParticipantEditing && saved" class="text-button" type="button" @click="saved = false">Update availability</button></header><AvailabilityGrid :slots="poll.slots" :timezone="displayTimezone" :selected-ids="selectedIds" :counts="poll.aggregate" :names="poll.availableNames" @toggle="toggle" @replace="replace" /><p v-if="error" class="schedule-error" role="alert">{{ error }}</p><div class="schedule-sticky-submit"><span>{{ selectedIds.length }} selected</span><button class="button" :disabled="saving || (saved && !poll.allowParticipantEditing)" @click="submit">{{ saving ? 'Saving…' : saved ? 'Availability saved' : 'Submit availability' }}</button></div></section>
      </template>
    </section>
  </main>
</template>
