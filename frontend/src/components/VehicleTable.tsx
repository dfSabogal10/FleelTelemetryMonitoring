import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useMemo } from "react";

import type { Anomaly, Vehicle } from "../api/types";
import { formatAnomalyType, formatTime, formatVehicleId } from "../utils/formatters";
import { latestAnomalyByVehicle } from "../utils/anomalyUtils";
import { BatteryBar } from "./BatteryBar";
import { SeverityChip } from "./SeverityChip";
import { StatusChip } from "./StatusChip";

const headSx = {
  bgcolor: "#ffffff",
  fontWeight: 600,
  py: 1,
  borderBottom: 1,
  borderColor: "divider",
};

interface VehicleTableProps {
  vehicles: Vehicle[];
  anomalies: Anomaly[];
}

export function VehicleTable({ vehicles, anomalies }: VehicleTableProps) {
  const latestByVehicle = useMemo(() => latestAnomalyByVehicle(anomalies), [anomalies]);

  return (
    <Paper elevation={1} sx={{ borderRadius: 2, pb: 2 }}>
      <Typography variant="subtitle1" fontWeight={700} sx={{ px: 2, pt: 2, pb: 1 }}>
        Vehicles ({vehicles.length})
      </Typography>
      <TableContainer
        sx={{
          maxHeight: { xs: 480, md: "calc(100vh - 380px)" },
          px: 0,
          pb: 1,
        }}
      >
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell sx={headSx}>Vehicle ID</TableCell>
              <TableCell sx={headSx}>Status</TableCell>
              <TableCell sx={headSx}>Battery (%)</TableCell>
              <TableCell sx={headSx}>Latest Anomaly</TableCell>
              <TableCell sx={headSx}>Last Seen</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {vehicles.map((v) => {
              const latest = latestByVehicle.get(v.vehicle_id);
              return (
                <TableRow key={v.vehicle_id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {formatVehicleId(v.vehicle_id)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <StatusChip status={v.status} />
                  </TableCell>
                  <TableCell>
                    <BatteryBar batteryPct={v.battery_pct} />
                  </TableCell>
                  <TableCell sx={{ maxWidth: 240 }}>
                    {latest ? (
                      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}>
                        <Typography variant="body2">{formatAnomalyType(latest.type)}</Typography>
                        <SeverityChip severity={latest.severity} />
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        None
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{formatTime(v.last_seen_at)}</Typography>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}
