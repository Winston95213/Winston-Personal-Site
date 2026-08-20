<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { api } from "../api";
import { browserTimezone, formatTimezone } from "../lib/scheduling";

type CreatedEvent = { id: string; token: string; title: string; timezone: string; dates: { date: string }[]; responseDeadline: string | null };
const today = new Date().toISOString().slice(0, 10);
const dateToAdd = ref("");
const dates = ref<string[]>([]);
const saving = ref(false);
const error = ref("");
const errorAlert = ref<HTMLElement | null>(null);
const copied = ref("");
const created = ref<CreatedEvent | null>(null);
const form = ref({ title: "Availability poll", description: "", location: "", meetingUrl: "", timezone: browserTimezone(), startTime: "10:00", endTime: "18:00", intervalMinutes: 30, meetingDurationMinutes: 30, deadlineHours: 168, allowParticipantEditing: true, availabilityVisibility: "AGGREGATE" });
const shareLink = computed(() => created.value ? `${window.location.origin}/schedule/${created.value.token}` : "");
const durationOptions = computed(() => [30, 45, 60, 90, 120].filter((minutes) => minutes % form.value.intervalMinutes === 0));
// A blue chip is an already-added date. Keep it separate from the picker so
// submitting never depends on the picker retaining its last value.
const selectedDates = computed(() => [...new Set(dates.value)].sort());

watch(() => form.value.intervalMinutes, () => {
  if (!durationOptions.value.includes(form.value.meetingDurationMinutes)) form.value.meetingDurationMinutes = durationOptions.value[0];
});

function addDate() {
  const date = dateToAdd.value;
  if (!date) return;
  if (!dates.value.includes(date)) dates.value = [...dates.value, date].sort();
  dateToAdd.value = "";
}
function removeDate(date: string) { dates.value = dates.value.filter((value) => value !== date); }
async function copy(value: string) { try { await navigator.clipboard.writeText(value); copied.value = "Copied."; window.setTimeout(() => copied.value = "", 1500); } catch { copied.value = "Select the link and copy it manually."; } }
async function create() {
  error.value = "";
  const eventDates = selectedDates.value;
  if (!eventDates.length) { error.value = "Add at least one possible date before creating the poll."; return; }
  saving.value = true;
  try {
    const result = await api<{ event: CreatedEvent }>("/owner/schedule/events/", "POST", {
      ...form.value,
      title: form.value.title.trim() || "Availability poll",
      // Send each chip as an explicit date range. This avoids relying on the
      // backend to combine a dates array with the shared start/end values.
      dateRanges: eventDates.map((date) => ({ date, startTime: form.value.startTime, endTime: form.value.endTime })),
    });
    created.value = result.event;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "We couldn’t create this scheduling poll.";
    await nextTick();
    errorAlert.value?.scrollIntoView({ behavior: "smooth", block: "center" });
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <main id="main" class="schedule-admin-page">
    <section class="schedule-create-shell">
      <RouterLink class="schedule-back" to="/admin/schedule">Scheduling</RouterLink>
      <section v-if="created" class="schedule-created-card" aria-labelledby="poll-created-title"><div class="schedule-success" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="m5 12.5 4.2 4.2L19.5 6.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="eyebrow">Scheduling poll created</div><h1 id="poll-created-title">{{ created.title }}</h1><p>Share the link below. Participants can choose every time they are available without creating an account.</p><div class="schedule-share-box"><span>Share link</span><code>{{ shareLink }}</code><button class="button" @click="copy(shareLink)">Copy link</button></div><p class="schedule-meta">{{ formatTimezone(created.timezone) }} · {{ created.dates.length }} {{ created.dates.length === 1 ? 'date' : 'dates' }}</p><p v-if="copied" class="schedule-feedback" role="status">{{ copied }}</p><div class="actions"><RouterLink class="button" :to="`/admin/schedule/${created.id}`">View results</RouterLink><a class="button secondary" :href="shareLink" target="_blank" rel="noopener noreferrer">Open poll</a></div></section>
      <form v-else class="schedule-create-card" @submit.prevent="create"><header><div class="eyebrow">New scheduling poll</div><h1>Create an event</h1><p>Choose the possible dates and shared meeting hours. Each selected date is added automatically.</p></header><p v-if="error" ref="errorAlert" class="schedule-error schedule-error-prominent" role="alert">{{ error }} <RouterLink v-if="error.includes('Sign in with your owner account')" to="/admin/chat">Sign in to the owner dashboard.</RouterLink></p>
        <div class="schedule-form-section"><h2>Event details</h2><label class="field">Event name <small>Optional — defaults to “Availability poll”</small><input v-model="form.title" maxlength="120" placeholder="Availability poll" /></label><label class="field">Description <small>Optional</small><textarea v-model="form.description" maxlength="500" placeholder="Let’s find a time for our project discussion." /></label><div class="schedule-two-col"><label class="field">Location or meeting method <small>Optional</small><input v-model="form.location" maxlength="200" placeholder="Zoom, Google Meet, or in person" /></label><label class="field">Meeting URL <small>Optional — shown only after confirmation</small><input v-model="form.meetingUrl" type="url" maxlength="500" placeholder="https://" /></label></div></div>
        <div class="schedule-form-section"><h2>When</h2><label class="field">Event timezone<input v-model="form.timezone" list="timezones" required /><small>Use an IANA timezone. {{ formatTimezone(form.timezone) }}</small></label><datalist id="timezones"><option>America/Chicago</option><option>America/New_York</option><option>America/Los_Angeles</option><option>Asia/Taipei</option><option>Asia/Tokyo</option><option>Europe/London</option><option>Europe/Paris</option><option>UTC</option></datalist><div class="schedule-date-picker"><label class="field">Possible dates <small>Select a date and it is added immediately</small><input v-model="dateToAdd" :min="today" type="date" @change="addDate" @keydown.enter.prevent="addDate" /></label></div><div class="date-chips" aria-live="polite"><span v-if="!selectedDates.length" class="schedule-hint">Select at least one date above.</span><span v-for="date in selectedDates" :key="date" class="date-chip">{{ date }}<button type="button" :aria-label="`Remove ${date}`" @click="removeDate(date)">Remove</button></span></div><p v-if="selectedDates.length" class="schedule-date-status" role="status">{{ selectedDates.length }} {{ selectedDates.length === 1 ? 'date selected' : 'dates selected' }}.</p><div class="schedule-three-col"><label class="field">Start time<input v-model="form.startTime" type="time" required /></label><label class="field">End time<input v-model="form.endTime" type="time" required /></label><label class="field">Interval<select v-model.number="form.intervalMinutes"><option :value="15">15 minutes</option><option :value="30">30 minutes</option><option :value="45">45 minutes</option><option :value="60">60 minutes</option></select></label></div><label class="field">Meeting duration<select v-model.number="form.meetingDurationMinutes"><option v-for="minutes in durationOptions" :key="minutes" :value="minutes">{{ minutes }} minutes</option></select><small>These hours apply to every selected date. Only whole {{ form.intervalMinutes }}-minute slots are available.</small></label></div>
        <div class="schedule-form-section"><h2>Responses and privacy</h2><div class="schedule-two-col"><label class="field">Response deadline<select v-model.number="form.deadlineHours"><option :value="0">No deadline</option><option :value="24">24 hours</option><option :value="72">3 days</option><option :value="168">7 days</option><option :value="720">30 days</option></select></label><label class="field">Public availability<select v-model="form.availabilityVisibility"><option value="HIDDEN">Hide participant details</option><option value="AGGREGATE">Show aggregate counts only</option><option value="NAMES">Show participant names</option></select></label></div><label class="schedule-check"><input v-model="form.allowParticipantEditing" type="checkbox" /><span><b>Let participants update availability</b><small>They can return using their private browser session.</small></span></label></div>
        <footer class="schedule-create-actions"><RouterLink class="button secondary" to="/admin/schedule">Cancel</RouterLink><button class="button" :disabled="saving">{{ saving ? 'Creating poll…' : 'Create scheduling poll' }}</button></footer>
      </form>
    </section>
  </main>
</template>
