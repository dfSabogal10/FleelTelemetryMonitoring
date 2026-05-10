import type { Anomaly } from "../api/types";

/**
 * API returns anomalies newest-first. First occurrence per vehicle is therefore
 * the latest anomaly for that vehicle.
 */
export function latestAnomalyByVehicle(anomalies: Anomaly[]): Map<string, Anomaly> {
  const map = new Map<string, Anomaly>();
  for (const a of anomalies) {
    if (!map.has(a.vehicle_id)) {
      map.set(a.vehicle_id, a);
    }
  }
  return map;
}
