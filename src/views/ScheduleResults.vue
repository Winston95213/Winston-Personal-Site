<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { api } from "../api";
import AvailabilityGrid from "../components/AvailabilityGrid.vue";
import { formatRange, type AvailabilityCount, type ScheduleSlot } from "../lib/scheduling";

type Participant = { id: string; name: string; email: string; isOwner: boolean; selectedSlotIds: string[]; updatedAt: string };
type BestTime = { slotId: string; startAt: string; endAt: string; available: number; total: number; percentage: number };
type EventDetail = { id: string; token: string; title: string; description: string; timezone: string; status: string; slots: ScheduleSlot[]; aggregate: Record<string, AvailabilityCount>; bestTimes: BestTime[]; participants: Participant[]; confirmedMeeting: { startAt: string; endAt: string } | null; allowParticipantEditing: boolean; responseDeadline: string | null };
const props = defineProps<{ id: string }>();
const event = ref<EventDetail | null>(null);
const error = ref("");
const loading = ref(true);
const ownerSlots = ref<string[]>([]);
const savingOwner = ref(false);
const selectedSlot = ref<string | null>(null);
const poller = ref<number | undefined>();
const shareLink = computed(() => event.value ? `${window.location.origin}/schedule/${event.value.token}` : "");
const responseCount = computed(() => event.value?.participants.filter((participant) => !participant.isOwner).length ?? 0);
const selectedPeople = computed(() => { const slotId = selectedSlot.value; if (!event.value || !slotId) return []; return event.value.participants.filter((participant) => participant.selectedSlotIds.includes(slotId)); });

async function load(silent = false) {
  if (!silent) loading.value = true;
  try {
    const result = await api<{ event: EventDetail }>(`/owner/schedule/events/${props.id}/`);
    event.value = result.event;
    ownerSlots.value = result.event.participants.find((participant) => participant.isOwner)?.selectedSlotIds ?? [];
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "We couldn’t load this scheduling poll.";
  } finally { loading.value = false; }
}
function toggleOwner(slotId: string) { ownerSlots.value = ownerSlots.value.includes(slotId) ? ownerSlots.value.filter((value) => value !== slotId) : [...ownerSlots.value, slotId]; }
function replaceOwner(slotIds: string[]) { ownerSlots.value = slotIds; }
async function saveOwner() { if (!event.value) return; savingOwner.value = true; try { await api(`/owner/schedule/events/${event.value.id}/availability/`, "POST", { slotIds: ownerSlots.value }); await load(true); } catch (caught) { error.value = caught instanceof Error ? caught.message : "We couldn’t save your availability."; } finally { savingOwner.value = false; } }
async function copy() { try { await navigator.clipboard.writeText(shareLink.value); error.value = "Share link copied."; window.setTimeout(() => error.value = "", 1500); } catch { error.value = "Select the link and copy it manually."; } }
async function confirmMeeting(slotId: string) { if (!event.value || !confirm("Confirm this meeting time? Participants will see the final time.")) return; try { await api(`/owner/schedule/events/${event.value.id}/confirm/`, "POST", { slotId }); await load(); } catch (caught) { error.value = caught instanceof Error ? caught.message : "We couldn’t confirm the meeting."; } }
async function updateStatus(action: "close" | "reopen" | "cancel" | "delete") { if (!event.value) return; const messages = { close: "Close responses to this poll?", reopen: "Reopen this poll? The confirmed meeting will be removed.", cancel: "Cancel the confirmed meeting?", delete: "Delete this scheduling poll and its responses?" }; if (!confirm(messages[action])) return; try { if (action === "delete") { await api(`/owner/schedule/events/${event.value.id}/settings/`, "DELETE"); window.location.assign("/admin/schedule"); return; } if (action === "reopen" || action === "cancel") await api(`/owner/schedule/events/${event.value.id}/${action}/`, "POST", {}); else await api(`/owner/schedule/events/${event.value.id}/settings/`, "PATCH", { status: "CLOSED" }); await load(); } catch (caught) { error.value = caught instanceof Error ? caught.message : "We couldn’t update this poll."; } }
async function removeParticipant(participant: Participant) { if (!event.value || !confirm(`Remove ${participant.name}'s availability?`)) return; try { await api(`/owner/schedule/events/${event.value.id}/participants/${participant.id}/`, "DELETE"); await load(); } catch (caught) { error.value = caught instanceof Error ? caught.message : "We couldn’t remove this participant."; } }

onMounted(() => { load(); poller.value = window.setInterval(() => load(true), 20000); });
onBeforeUnmount(() => { if (poller.value) window.clearInterval(poller.value); });
</script>

<template>
  <main id="main" class="schedule-admin-page"><section v-if="loading && !event" class="schedule-admin-shell schedule-loading">Loading scheduling poll…</section><section v-else-if="event" class="schedule-results-shell"><RouterLink class="schedule-back" to="/admin/schedule">Scheduling</RouterLink><header class="schedule-results-header"><div><div class="eyebrow">{{ event.status }}</div><h1>{{ event.title }}</h1><p>{{ responseCount }} {{ responseCount === 1 ? 'response' : 'responses' }} · {{ event.timezone }}</p></div><div class="actions"><button class="button secondary" @click="copy">Copy link</button><a class="button secondary" :href="shareLink" target="_blank" rel="noopener noreferrer">Open poll</a></div></header><p v-if="error" class="schedule-feedback" role="status">{{ error }}</p>
    <section v-if="event.confirmedMeeting" class="schedule-final-meeting"><div><div class="eyebrow">Meeting confirmed</div><h2>{{ formatRange(event.confirmedMeeting.startAt, event.confirmedMeeting.endAt, event.timezone) }}</h2><p>Availability is now locked for participants.</p></div><div class="actions"><button class="button secondary" @click="updateStatus('reopen')">Reopen poll</button><button class="text-button danger" @click="updateStatus('cancel')">Cancel meeting</button></div></section>
    <div class="schedule-results-layout"><div class="schedule-results-main"><section class="schedule-panel heatmap-panel"><header class="schedule-panel-header"><div><h2>Availability heatmap</h2><p>Counts are calculated server-side and refresh automatically.</p></div><button class="text-button" @click="() => load()">Refresh</button></header><AvailabilityGrid :slots="event.slots" :timezone="event.timezone" :counts="event.aggregate" readonly @inspect="selectedSlot = $event" /><aside v-if="selectedSlot" class="schedule-slot-inspector"><header><div><b>{{ event.slots.find((slot) => slot.id === selectedSlot) ? formatRange(event.slots.find((slot) => slot.id === selectedSlot)!.startAt, event.slots.find((slot) => slot.id === selectedSlot)!.endAt, event.timezone) : '' }}</b><small>{{ selectedPeople.length }} available</small></div><button class="text-button" @click="selectedSlot = null">Close</button></header><p>{{ selectedPeople.length ? selectedPeople.map((person) => person.name).join(', ') : 'No one has selected this time.' }}</p></aside></section>
      <section class="schedule-panel owner-availability"><header class="schedule-panel-header"><div><h2>My availability</h2><p>Include your own schedule in the best-time calculation.</p></div><button class="button" :disabled="savingOwner" @click="saveOwner">{{ savingOwner ? 'Saving…' : 'Save availability' }}</button></header><AvailabilityGrid :slots="event.slots" :timezone="event.timezone" :selected-ids="ownerSlots" @toggle="toggleOwner" @replace="replaceOwner" /></section></div>
      <aside class="schedule-results-sidebar"><section class="schedule-panel best-times"><header class="schedule-panel-header"><h2>Best times</h2><span>{{ responseCount }} participants</span></header><div v-if="event.bestTimes.length" class="best-time-list"><article v-for="(time, index) in event.bestTimes" :key="time.slotId"><span class="best-rank">{{ index + 1 }}</span><div><b>{{ formatRange(time.startAt, time.endAt, event.timezone) }}</b><small>{{ time.available }}/{{ time.total }} available · {{ time.percentage }}%</small></div><button v-if="event.status === 'OPEN'" class="text-button" @click="confirmMeeting(time.slotId)">Confirm</button></article></div><p v-else class="schedule-hint">Waiting for responses. Share the link to start collecting availability.</p></section><section class="schedule-panel participant-panel"><header class="schedule-panel-header"><h2>Participants</h2><span>{{ responseCount }}</span></header><div v-if="responseCount" class="participant-list"><article v-for="person in event.participants.filter((item) => !item.isOwner)" :key="person.id"><span class="participant-initial">{{ person.name.slice(0, 1).toUpperCase() }}</span><div><b>{{ person.name }}</b><small>{{ person.selectedSlotIds.length }} slots selected · Updated {{ new Date(person.updatedAt).toLocaleString() }}</small></div><button class="text-button danger" @click="removeParticipant(person)">Remove</button></article></div><p v-else class="schedule-hint">Waiting for responses.</p></section><section class="schedule-panel schedule-admin-actions"><h2>Poll controls</h2><p v-if="event.responseDeadline">Response deadline: {{ new Date(event.responseDeadline).toLocaleString() }}</p><button v-if="event.status === 'OPEN'" class="button secondary" @click="updateStatus('close')">Close responses</button><button v-else-if="event.status !== 'CANCELLED'" class="button secondary" @click="updateStatus('reopen')">Reopen poll</button><button class="text-button danger" @click="updateStatus('delete')">Delete poll</button></section></aside></div>
  </section></main>
</template>
