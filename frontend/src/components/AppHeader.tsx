import DirectionsCar from "@mui/icons-material/DirectionsCar";
import FiberManualRecord from "@mui/icons-material/FiberManualRecord";
import { Box, Chip, Typography } from "@mui/material";

interface AppHeaderProps {
  lastUpdated: Date | null;
}

export function AppHeader({ lastUpdated }: AppHeaderProps) {
  const timeStr = lastUpdated
    ? lastUpdated.toLocaleTimeString(undefined, {
        hour: "numeric",
        minute: "2-digit",
        second: "2-digit",
      })
    : "—";

  return (
    <Box
      sx={{
        bgcolor: "background.paper",
        borderBottom: 1,
        borderColor: "divider",
        px: 2,
        py: 1.5,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <DirectionsCar color="primary" sx={{ fontSize: 32 }} />
        <Typography variant="h6" component="h1" fontWeight={700}>
          Fleet Telemetry Monitor
        </Typography>
      </Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Last updated: <strong>{timeStr}</strong>
        </Typography>
        <Chip
          size="small"
          label="Live (polling every 1s)"
          icon={<FiberManualRecord sx={{ fontSize: "14px !important", color: "#4caf50" }} />}
          sx={{
            bgcolor: "#e8f5e9",
            color: "#2e7d32",
            fontWeight: 600,
            "& .MuiChip-label": { px: 1 },
          }}
        />
      </Box>
    </Box>
  );
}
