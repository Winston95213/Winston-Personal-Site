export type ScheduleSlot = { id: string; startAt: string; endAt: string; localDate: string };
export type AvailabilityCount = { available: number; total: number; percentage: number };

export function browserTimezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

export function formatTimezone(timezone: string) {
  try {
    const label = new Intl.DateTimeFormat("en-US", { timeZone: timezone, timeZoneName: "long" }).formatToParts(new Date()).find((part) => part.type === "timeZoneName")?.value;
    return label ? `${timezone.replace(/_/g, " ")} · ${label}` : timezone;
  } catch {
    return timezone;
  }
}

export function dateKey(instant: string, timezone: string) {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(instant));
  const value = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}

export function formatDay(instant: string, timezone: string, compact = false) {
  return new Intl.DateTimeFormat("en-US", { timeZone: timezone, weekday: compact ? undefined : "short", month: "short", day: "numeric" }).format(new Date(instant));
}

export function formatTime(instant: string, timezone: string) {
  return new Intl.DateTimeFormat("en-US", { timeZone: timezone, hour: "numeric", minute: "2-digit" }).format(new Date(instant));
}

export function formatRange(start: string, end: string, timezone: string) {
  return `${formatDay(start, timezone)} · ${formatTime(start, timezone)}–${formatTime(end, timezone)}`;
}
