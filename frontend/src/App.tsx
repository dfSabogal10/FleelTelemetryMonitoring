import { Alert, Box, CircularProgress, Container, Stack, Typography } from "@mui/material";
import Grid from "@mui/material/Grid2";

import { AppHeader } from "./components/AppHeader";
import { FleetStateCards } from "./components/FleetStateCards";
import { RecentAnomaliesPanel } from "./components/RecentAnomaliesPanel";
import { VehicleTable } from "./components/VehicleTable";
import { ZoneCountsPanel } from "./components/ZoneCountsPanel";
import { useFleetDashboardData } from "./hooks/useFleetDashboardData";

export default function App() {
  const { vehicles, fleetState, zoneCounts, anomalies, lastUpdated, loading, error } =
    useFleetDashboardData();

  return (
    <Box sx={{ bgcolor: "#f5f5f5", minHeight: "100vh", pb: 3 }}>
      <AppHeader lastUpdated={lastUpdated} />
      <Container maxWidth={false} sx={{ px: { xs: 1.5, sm: 2 }, pt: 2 }}>
        {error ? (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}

        {loading && vehicles.length === 0 ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
            <CircularProgress />
          </Box>
        ) : null}

        {vehicles.length > 0 ? (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, lg: 8 }}> 
              <Typography variant="h6" fontWeight={700} sx={{ mb: 1.5 }}>
                Fleet State
              </Typography>
            </Grid>
            <Grid size={{ xs: 12, lg: 8 }}>
              <Stack spacing={2}>
                <Box>
                  <FleetStateCards fleetState={fleetState} />
                </Box>
                <VehicleTable vehicles={vehicles} anomalies={anomalies} />
              </Stack>
            </Grid>
            <Grid size={{ xs: 12, lg: 4 }}>
              <Stack spacing={2}>
                <ZoneCountsPanel zones={zoneCounts} />
                <RecentAnomaliesPanel anomalies={anomalies} />
              </Stack>
            </Grid>
          </Grid>
        ) : null}
      </Container>
    </Box>
  );
}
