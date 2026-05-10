export interface Vehicle {
  vehicle_id: string;
  status: string;
  battery_pct: number | null;
  speed_mps: number | null;
  lat: number | null;
  lon: number | null;
  last_seen_at: string | null;
}

export interface FleetState {
  idle: number;
  moving: number;
  charging: number;
  fault: number;
}

export interface ZoneCount {
  zone_id: string;
  entry_count: number;
}

export interface Anomaly {
  id: string;
  vehicle_id: string;
  type: string;
  severity: string;
  message: string;
  created_at: string;
}
