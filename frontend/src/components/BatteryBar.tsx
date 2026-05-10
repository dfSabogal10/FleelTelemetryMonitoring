import { Box, LinearProgress, Typography } from "@mui/material";

interface BatteryBarProps {
  batteryPct: number | null;
}

export function BatteryBar({ batteryPct }: BatteryBarProps) {
  if (batteryPct === null || batteryPct === undefined) {
    return (
      <Typography variant="body2" color="text.secondary">
        —
      </Typography>
    );
  }
  const low = batteryPct < 15;
  return (
    <Box sx={{ minWidth: 100 }}>
      <Typography variant="body2" sx={{ mb: 0.25 }}>
        {batteryPct}%
      </Typography>
      <LinearProgress
        variant="determinate"
        value={batteryPct}
        color={low ? "error" : "success"}
        sx={{ height: 8, borderRadius: 1 }}
      />
    </Box>
  );
}
