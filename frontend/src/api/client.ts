import type { Anomaly, FleetState, Vehicle, ZoneCount } from "./types";

export function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
}

async function fetchJson<T>(path: string): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`;
  const response = await fetch(url);
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(
      `Request failed ${response.status}: ${response.statusText}${text ? ` — ${text}` : ""}`,
    );
  }
  return response.json() as Promise<T>;
}

export function fetchVehicles(): Promise<Vehicle[]> {
  return fetchJson<Vehicle[]>("/vehicles");
}

export function fetchFleetState(): Promise<FleetState> {
  return fetchJson<FleetState>("/fleet/state");
}

export function fetchZoneCounts(): Promise<ZoneCount[]> {
  return fetchJson<ZoneCount[]>("/zones/counts");
}

export function fetchAnomalies(limit = 200): Promise<Anomaly[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  return fetchJson<Anomaly[]>(`/anomalies?${params.toString()}`);
}
