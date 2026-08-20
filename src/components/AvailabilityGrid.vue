<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { dateKey, formatDay, formatTime, type AvailabilityCount, type ScheduleSlot } from "../lib/scheduling";

const props = withDefaults(defineProps<{ slots: ScheduleSlot[]; timezone: string; selectedIds?: string[]; counts?: Record<string, AvailabilityCount>; names?: Record<string, string[]>; readonly?: boolean }>(), { selectedIds: () => [], counts: () => ({}), names: () => ({}), readonly: false });
const emit = defineEmits<{ toggle: [slotId: string]; replace: [slotIds: string[]]; inspect: [slotId: string] }>();
const activeDay = ref("");

const days = computed(() => {
  const grouped = new Map<string, ScheduleSlot[]>();
  for (const slot of props.slots) {
    const key = dateKey(slot.startAt, props.timezone);
    grouped.set(key, [...(grouped.get(key) ?? []), slot]);
  }
  return [...grouped.entries()].map(([key, slots]) => ({ key, slots, label: formatDay(slots[0].startAt, props.timezone) }));
});

watch(days, (value) => {
  if (!value.some((day) => day.key === activeDay.value)) activeDay.value = value[0]?.key ?? "";
}, { immediate: true });

function selected(slot: ScheduleSlot) { return props.selectedIds.includes(slot.id); }
function choose(slot: ScheduleSlot) { if (props.readonly) emit("inspect", slot.id); else emit("toggle", slot.id); }
function selectDay(day: { slots: ScheduleSlot[] }) { emit("replace", [...new Set([...props.selectedIds, ...day.slots.map((slot) => slot.id)])]); }
function clearDay(day: { slots: ScheduleSlot[] }) { const ids = new Set(day.slots.map((slot) => slot.id)); emit("replace", props.selectedIds.filter((id) => !ids.has(id))); }
function slotLabel(slot: ScheduleSlot) { const count = props.counts[slot.id]; const names = props.names[slot.id]; const state = selected(slot) ? "available" : "not available"; return `${formatDay(slot.startAt, props.timezone)}, ${formatTime(slot.startAt, props.timezone)} — ${state}${count ? `, ${count.available} of ${count.total} available` : ""}${names?.length ? `: ${names.join(", ")}` : ""}`; }
</script>

<template>
  <div class="availability-grid-wrap">
    <div class="date-tabs" role="tablist" aria-label="Available dates">
      <button v-for="day in days" :key="day.key" type="button" :class="{ active: activeDay === day.key }" role="tab" :aria-selected="activeDay === day.key" @click="activeDay = day.key">{{ day.label }}</button>
    </div>
    <div class="availability-days" role="group" aria-label="Availability times">
      <section v-for="day in days" :key="day.key" :class="['day-column', { active: activeDay === day.key }]">
        <header><div><strong>{{ day.label }}</strong><small>{{ timezone }}</small></div><div v-if="!readonly" class="day-tools"><button type="button" @click="selectDay(day)">All</button><button type="button" @click="clearDay(day)">Clear</button></div></header>
        <div class="slot-list">
          <button v-for="slot in day.slots" :key="slot.id" type="button" :class="['slot-button', { selected: selected(slot), heat: counts[slot.id] }]" :style="counts[slot.id] ? { '--heat': `${counts[slot.id].percentage}%` } : {}" :aria-pressed="selected(slot)" :aria-label="slotLabel(slot)" @click="choose(slot)">
            <span>{{ formatTime(slot.startAt, timezone) }}</span><b v-if="counts[slot.id]">{{ counts[slot.id].available }}/{{ counts[slot.id].total }}</b><i v-else aria-hidden="true">{{ selected(slot) ? 'Selected' : 'Select' }}</i><small v-if="names[slot.id]?.length" class="slot-names">{{ names[slot.id].join(', ') }}</small>
          </button>
        </div>
      </section>
    </div>
  </div>
</template>
