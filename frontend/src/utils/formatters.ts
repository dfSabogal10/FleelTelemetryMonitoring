/** Display vehicle id as in mock (e.g. v-12 → V-12). */
export function formatVehicleId(vehicleId: string): string {
  if (!vehicleId) return vehicleId;
  return vehicleId.charAt(0).toUpperCase() + vehicleId.slice(1);
}

/** Short locale time for operator display. */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}

/** Human-readable zone id for compact tables (charging_bay_1 → Charging Bay 1). */
export function formatZoneLabel(zoneId: string): string {
  return zoneId
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

/** Turn snake_case anomaly type into readable label. */
export function formatAnomalyType(type: string): string {
  return type
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}
