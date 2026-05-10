import ErrorOutline from "@mui/icons-material/ErrorOutline";
import WarningAmber from "@mui/icons-material/WarningAmber";
import {
  Box,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  Paper,
  Typography,
} from "@mui/material";

import type { Anomaly } from "../api/types";
import { formatAnomalyType, formatTime, formatVehicleId } from "../utils/formatters";
import { SeverityChip } from "./SeverityChip";

const DISPLAY_LIMIT = 12;

interface RecentAnomaliesPanelProps {
  anomalies: Anomaly[];
}

export function RecentAnomaliesPanel({ anomalies }: RecentAnomaliesPanelProps) {
  const rows = anomalies.slice(0, DISPLAY_LIMIT);

  return (
    <Paper elevation={1} sx={{ borderRadius: 2, pb: 2 }}>
      <Typography variant="subtitle1" fontWeight={700} sx={{ px: 2, pt: 2, pb: 1 }}>
        Recent anomalies
      </Typography>
      <List dense disablePadding sx={{ pb: 1 }}>
        {rows.map((a, i) => {
          const isCritical = a.severity.toLowerCase() === "critical";
          return (
            <Box key={a.id}>
              {i > 0 ? <Divider component="li" /> : null}
              <ListItem alignItems="flex-start" sx={{ px: 2, py: 1.25 }}>
                <ListItemIcon sx={{ minWidth: 36, mt: 0.25 }}>
                  {isCritical ? (
                    <ErrorOutline color="error" fontSize="small" />
                  ) : (
                    <WarningAmber sx={{ color: "#f57f17", fontSize: 22 }} />
                  )}
                </ListItemIcon>
                <Box sx={{ flex: 1, minWidth: 0, pr: 1 }}>
                  <Typography variant="body2" fontWeight={600}>
                    {formatAnomalyType(a.type)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    {formatVehicleId(a.vehicle_id)} · {formatTime(a.created_at)}
                  </Typography>
                </Box>
                <SeverityChip severity={a.severity} />
              </ListItem>
            </Box>
          );
        })}
        {rows.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ px: 2, pb: 2 }}>
            No anomalies yet.
          </Typography>
        ) : null}
      </List>
    </Paper>
  );
}
