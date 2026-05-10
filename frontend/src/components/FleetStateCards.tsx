import Bolt from "@mui/icons-material/Bolt";
import DirectionsCar from "@mui/icons-material/DirectionsCar";
import ErrorOutline from "@mui/icons-material/ErrorOutline";
import PlayArrow from "@mui/icons-material/PlayArrow";
import { Box, Card, CardContent, Typography } from "@mui/material";
import Grid from "@mui/material/Grid2";
import type { FleetState } from "../api/types";

interface FleetStateCardsProps {
  fleetState: FleetState | null;
}

const CARD_META = [
  {
    key: "idle" as const,
    label: "Idle",
    Icon: DirectionsCar,
    iconColor: "#1976d2",
    numberColor: "#1976d2",
  },
  {
    key: "moving" as const,
    label: "Moving",
    Icon: PlayArrow,
    iconColor: "#2e7d32",
    numberColor: "#2e7d32",
  },
  {
    key: "charging" as const,
    label: "Charging",
    Icon: Bolt,
    iconColor: "#f57f17",
    numberColor: "#ef6c00",
  },
  {
    key: "fault" as const,
    label: "Fault",
    Icon: ErrorOutline,
    iconColor: "#c62828",
    numberColor: "#c62828",
  },
];

export function FleetStateCards({ fleetState }: FleetStateCardsProps) {
  const total = fleetState
    ? fleetState.idle + fleetState.moving + fleetState.charging + fleetState.fault
    : 0;

  return (
    <Grid container spacing={2}>
      {CARD_META.map(({ key, label, Icon, iconColor, numberColor }) => {
        const count = fleetState?.[key] ?? 0;
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        return (
          <Grid size={{ xs: 6, sm: 3 }} key={key}>
            <Card elevation={1} sx={{ borderRadius: 2 }}>
              <CardContent sx={{ py: 2, "&:last-child": { pb: 2 } }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                  <Icon sx={{ color: iconColor, fontSize: 40 }} aria-hidden />
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      {label}
                    </Typography>
                    <Typography variant="h4" fontWeight={700} sx={{ color: numberColor, lineHeight: 1.2 }}>
                      {count}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {pct}%
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        );
      })}
    </Grid>
  );
}
