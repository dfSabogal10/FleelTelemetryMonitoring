import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const mockUseFleetDashboardData = vi.hoisted(() => vi.fn());

vi.mock("./hooks/useFleetDashboardData", () => ({
  useFleetDashboardData: () => mockUseFleetDashboardData(),
}));

const loadedDashboard = {
  vehicles: [
    {
      vehicle_id: "v-1",
      status: "idle",
      battery_pct: 80,
      speed_mps: 0,
      lat: 37.41,
      lon: -122.08,
      last_seen_at: "2026-05-09T12:00:00Z",
    },
  ],
  fleetState: { idle: 1, moving: 0, charging: 0, fault: 0 },
  zoneCounts: [{ zone_id: "aisle_a", entry_count: 3 }],
  anomalies: [],
  lastUpdated: new Date("2026-05-09T12:00:00Z"),
  loading: false,
  error: null as string | null,
};

describe("App", () => {
  beforeEach(() => {
    mockUseFleetDashboardData.mockReturnValue(loadedDashboard);
  });

  it("renders dashboard panels when vehicle data is present", () => {
    render(<App />);
    expect(screen.getByText("Fleet State")).toBeInTheDocument();
    expect(screen.getByText(/Vehicles \(1\)/)).toBeInTheDocument();
    expect(screen.getByText("Zone Entry Counts")).toBeInTheDocument();
    expect(screen.getByText("Recent anomalies")).toBeInTheDocument();
  });

  it("shows a warning alert when polling reports an error", () => {
    mockUseFleetDashboardData.mockReturnValue({
      ...loadedDashboard,
      error: "Backend unavailable. Retrying…",
    });
    render(<App />);
    expect(screen.getByRole("alert")).toHaveTextContent("Backend unavailable. Retrying…");
  });

  it("shows loading spinner when loading and no vehicles yet", () => {
    mockUseFleetDashboardData.mockReturnValue({
      ...loadedDashboard,
      vehicles: [],
      loading: true,
      error: null,
    });
    const { container } = render(<App />);
    expect(container.querySelector(".MuiCircularProgress-root")).not.toBeNull();
  });
});
