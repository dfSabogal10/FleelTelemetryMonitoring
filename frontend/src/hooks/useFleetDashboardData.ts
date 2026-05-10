import { useEffect, useRef, useState } from "react";

import {
  fetchAnomalies,
  fetchFleetState,
  fetchVehicles,
  fetchZoneCounts,
} from "../api/client";
import type { Anomaly, FleetState, Vehicle, ZoneCount } from "../api/types";

/** Normal poll interval after a successful refresh. */
const POLL_MS_SUCCESS = 1000;

const ANOMALY_LIMIT = 5;

const RETRY_MESSAGE = "Backend unavailable. Retrying…";

/** Exponential backoff after failures (ms): 2s, 4s, then 8s max. */
function backoffMs(consecutiveFailures: number): number {
  if (consecutiveFailures <= 1) return 2000;
  if (consecutiveFailures === 2) return 4000;
  return 8000;
}

export interface FleetDashboardData {
  vehicles: Vehicle[];
  fleetState: FleetState | null;
  zoneCounts: ZoneCount[];
  anomalies: Anomaly[];
  lastUpdated: Date | null;
  loading: boolean;
  /** Shown when polling fails; previous snapshot stays on screen. */
  error: string | null;
}

export function useFleetDashboardData(): FleetDashboardData {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [fleetState, setFleetState] = useState<FleetState | null>(null);
  const [zoneCounts, setZoneCounts] = useState<ZoneCount[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mountedRef = useRef(true);
  const inFlightRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const failuresRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;
    failuresRef.current = 0;

    const clearTimer = () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };

    const scheduleNext = (delayMs: number) => {
      clearTimer();
      timerRef.current = window.setTimeout(() => {
        timerRef.current = null;
        void tick();
      }, delayMs);
    };

    const tick = async () => {
      if (!mountedRef.current || inFlightRef.current) {
        return;
      }
      inFlightRef.current = true;

      try {
        const [v, f, z, a] = await Promise.all([
          fetchVehicles(),
          fetchFleetState(),
          fetchZoneCounts(),
          fetchAnomalies(ANOMALY_LIMIT),
        ]);
        if (!mountedRef.current) return;

        setVehicles(v);
        setFleetState(f);
        setZoneCounts(z);
        setAnomalies(a);
        setLastUpdated(new Date());
        setError(null);
        failuresRef.current = 0;
        scheduleNext(POLL_MS_SUCCESS);
      } catch {
        if (!mountedRef.current) return;
        failuresRef.current += 1;
        setError(RETRY_MESSAGE);
        scheduleNext(backoffMs(failuresRef.current));
      } finally {
        inFlightRef.current = false;
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    };

    void tick();

    return () => {
      mountedRef.current = false;
      clearTimer();
    };
  }, []);

  return {
    vehicles,
    fleetState,
    zoneCounts,
    anomalies,
    lastUpdated,
    loading,
    error,
  };
}
