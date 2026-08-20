<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { api } from "../api";

type Option = { id: string; text: string; addedBy: string; createdAt: string };
type Spin = { id: string; text: string; pickedBy: string; decidedAt: string };
type Wheel = { token: string; subject: string; isActive: boolean; options: Option[]; participantCount: number; decision: { optionId: string; text: string; decidedAt: string | null } | null; recentSpins: Spin[]; participant?: { name: string } };
const props = defineProps<{ token: string }>();
const wheel = ref<Wheel | null>(null);
const name = ref("");
const optionText = ref("");
const loading = ref(true);
const joining = ref(false);
const adding = ref(false);
const spinning = ref(false);
const rotation = ref(0);
const pendingDecision = ref<Wheel["decision"]>(null);
const error = ref("");
let refreshTimer: number | undefined;
const colors = ["#1677ff", "#35a8ff", "#7a5cff", "#00a884", "#ef8f20", "#e95579", "#3c7cda", "#8f60d9"];
const wheelGradient = computed(() => {
  const options = wheel.value?.options ?? [];
  if (!options.length) return "conic-gradient(#eff4fb 0 100%)";
  const step = 360 / options.length;
  return `conic-gradient(from -${step / 2}deg, ${options.map((_, index) => `${colors[index % colors.length]} ${index * step}deg ${(index + 1) * step}deg`).join(", ")})`;
});
function wheelLabelStyle(index: number) {
  const optionCount = wheel.value?.options.length ?? 1;
  const angle = (index * 360) / optionCount;
  const radians = (angle * Math.PI) / 180;
  const radius = 33;
  return {
    left: `${50 + Math.sin(radians) * radius}%`,
    top: `${50 - Math.cos(radians) * radius}%`,
    transform: `translate(-50%, -50%) rotate(${-rotation.value}deg)`,
  };
}
const shareLink = computed(() => `${window.location.origin}/wheel/${props.token}`);

async function load(silent = false) {
  if (!silent) loading.value = true;
  try { wheel.value = (await api<{ wheel: Wheel }>(`/wheel/${props.token}/`)).wheel; }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "We couldn’t load this decision wheel."; }
  finally { if (!silent) loading.value = false; }
}
async function join() {
  error.value = "";
  if (!name.value.trim()) { error.value = "Enter your name to join the group."; return; }
  joining.value = true;
  try { await api(`/wheel/${props.token}/join/`, "POST", { name: name.value }); await load(true); }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "We couldn’t join this wheel."; }
  finally { joining.value = false; }
}
async function addOption() {
  error.value = "";
  if (!optionText.value.trim()) return;
  adding.value = true;
  try { await api(`/wheel/${props.token}/options/`, "POST", { text: optionText.value }); optionText.value = ""; await load(true); }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "We couldn’t add that option."; }
  finally { adding.value = false; }
}
async function spin() {
  if (!wheel.value || wheel.value.options.length < 2 || spinning.value) return;
  error.value = ""; spinning.value = true; pendingDecision.value = null;
  try {
    const result = await api<{ decision: NonNullable<Wheel["decision"]>; optionIndex: number; optionCount: number }>(`/wheel/${props.token}/spin/`, "POST");
    const slice = 360 / result.optionCount;
    const visualOffset = (Math.random() - .5) * slice * .28;
    const target = 360 - result.optionIndex * slice + visualOffset;
    rotation.value += 1800 + ((target - (rotation.value % 360) + 360) % 360);
    pendingDecision.value = result.decision;
    window.setTimeout(async () => { spinning.value = false; await load(true); }, 4050);
  } catch (caught) { error.value = caught instanceof Error ? caught.message : "We couldn’t spin the wheel."; spinning.value = false; }
}
async function copy() {
  try { await navigator.clipboard.writeText(shareLink.value); error.value = "Invite link copied — send it to your group."; }
  catch { error.value = "Copy the invite link from the address bar."; }
}
onMounted(async () => { await load(); refreshTimer = window.setInterval(() => load(true), 7000); });
onBeforeUnmount(() => { if (refreshTimer) window.clearInterval(refreshTimer); });
</script>

<template>
  <main id="main" class="wheel-public-page">
    <section v-if="loading && !wheel" class="wheel-public-shell wheel-empty">Loading decision wheel…</section>
    <section v-else-if="wheel" class="wheel-public-shell">
      <header class="wheel-public-header"><div><RouterLink class="wheel-back" to="/">Portfolio</RouterLink><div class="eyebrow">Group decision</div><h1>{{ wheel.subject }}</h1><p>Share ideas, then spin once the group is ready.</p></div><button class="button secondary" type="button" @click="copy">Copy invite link</button></header>
      <p v-if="error" class="wheel-feedback" role="status">{{ error }}</p>
      <section v-if="!wheel.participant && wheel.isActive" class="wheel-join-card">
        <div class="wheel-lock-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="3"/><path d="M5 20c.6-3.4 3-5 7-5s6.4 1.6 7 5"/></svg></div><div><div class="eyebrow">Join the group</div><h2>Add your name first</h2><p>Your name appears next to choices you add. No account or download needed.</p></div>
        <form class="wheel-join-form" @submit.prevent="join"><label class="field"><span>Your name</span><input v-model="name" maxlength="60" autocomplete="name" placeholder="Your name" required></label><button class="button" type="submit" :disabled="joining">{{ joining ? 'Joining…' : 'Join decision wheel' }}</button></form>
      </section>
      <template v-else>
        <section class="wheel-stage-card">
          <div class="wheel-stage-head"><div><div class="eyebrow">{{ wheel.isActive ? 'Ready to decide' : 'Decision complete' }}</div><h2>{{ wheel.options.length }} options from {{ wheel.participantCount }} {{ wheel.participantCount === 1 ? 'person' : 'people' }}</h2></div></div>
          <div class="wheel-layout">
            <div class="wheel-wrap"><div class="wheel-pointer" aria-hidden="true"></div><div class="wheel-disc" :class="{ spinning }" :style="{ background: wheelGradient, transform: `rotate(${rotation}deg)` }"><template v-if="wheel.options.length <= 8"><span v-for="(option, index) in wheel.options" :key="option.id" class="wheel-slice-label" :style="wheelLabelStyle(index)" aria-hidden="true">{{ option.text }}</span></template><div class="wheel-hub" :style="{ transform: `translate(-50%, -50%) rotate(${-rotation}deg)` }"><span>{{ spinning ? 'Spinning…' : wheel.decision?.text || 'Choose' }}</span></div></div></div>
            <div class="wheel-result"><div v-if="pendingDecision || wheel.decision" class="wheel-winner"><span>Latest decision</span><strong>{{ pendingDecision?.text || wheel.decision?.text }}</strong><p>{{ spinning ? 'The wheel is finding the answer…' : 'The group can keep adding ideas and spin again anytime.' }}</p></div><div v-else><h3>Let the wheel decide.</h3><p>Add at least two ideas, then spin for a fair pick.</p></div><div v-if="wheel.options.length" class="wheel-live-options" aria-label="Options on the wheel"><span v-for="(option, index) in wheel.options" :key="option.id"><i :style="{ background: colors[index % colors.length] }" aria-hidden="true"></i>{{ option.text }}</span></div><button v-if="wheel.isActive" class="button wheel-spin-button" type="button" :disabled="wheel.options.length < 2 || spinning" @click="spin">{{ spinning ? 'Spinning…' : wheel.options.length < 2 ? 'Add 2 options to spin' : 'Spin the wheel' }}</button></div>
          </div>
        </section>
        <section class="wheel-options-card"><header><div><div class="eyebrow">Ideas</div><h2>What should go on the wheel?</h2></div><span>{{ wheel.options.length }}/30 options</span></header>
          <form v-if="wheel.isActive" class="wheel-add-form" @submit.prevent="addOption"><label class="field"><span class="sr-only">Add an option</span><input v-model="optionText" maxlength="120" autocomplete="off" placeholder="Add an idea, place, activity, or choice"></label><button class="button" type="submit" :disabled="adding || !optionText.trim()">{{ adding ? 'Adding…' : 'Add option' }}</button></form>
          <div v-if="wheel.options.length" class="wheel-option-grid"><article v-for="(option, index) in wheel.options" :key="option.id"><i :style="{ background: colors[index % colors.length] }" aria-hidden="true"></i><div><b>{{ option.text }}</b><small>Added by {{ option.addedBy }}</small></div></article></div><div v-else class="wheel-empty"><strong>The wheel is empty.</strong><p>Be the first person to add an idea.</p></div>
        </section>
        <section v-if="wheel.recentSpins.length" class="wheel-history-card"><header><div><div class="eyebrow">Results</div><h2>Recent decisions</h2></div><span>Latest {{ wheel.recentSpins.length }}</span></header><ol><li v-for="spin in wheel.recentSpins" :key="spin.id"><strong>{{ spin.text }}</strong><span>Spun by {{ spin.pickedBy }} · {{ new Date(spin.decidedAt).toLocaleString() }}</span></li></ol></section>
      </template>
    </section>
  </main>
</template>
