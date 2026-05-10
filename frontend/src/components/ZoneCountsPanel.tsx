import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import type { ZoneCount } from "../api/types";
import { formatZoneLabel } from "../utils/formatters";

const headSx = {
  bgcolor: "#ffffff",
  fontWeight: 600,
  py: 1,
  borderBottom: 1,
  borderColor: "divider",
};

interface ZoneCountsPanelProps {
  zones: ZoneCount[];
}

export function ZoneCountsPanel({ zones }: ZoneCountsPanelProps) {
  return (
    <Paper elevation={1} sx={{ borderRadius: 2, pb: 2 }}>
      <Typography variant="subtitle1" fontWeight={700} sx={{ px: 2, pt: 2, pb: 1 }}>
        Zone Entry Counts
      </Typography>
      <TableContainer sx={{ maxHeight: 260, pb: 1 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell sx={headSx}>Zone</TableCell>
              <TableCell sx={headSx} align="right">
                Entry Count
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {zones.map((z) => (
              <TableRow key={z.zone_id} hover>
                <TableCell sx={{ fontSize: "0.85rem" }}>{formatZoneLabel(z.zone_id)}</TableCell>
                <TableCell align="right">{z.entry_count}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}
