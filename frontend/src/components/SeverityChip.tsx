import { Chip } from "@mui/material";

interface SeverityChipProps {
  severity: string;
}

export function SeverityChip({ severity }: SeverityChipProps) {
  const s = severity.toLowerCase();
  const isCritical = s === "critical";
  return (
    <Chip
      label={severity.charAt(0).toUpperCase() + severity.slice(1).toLowerCase()}
      size="small"
      sx={{
        bgcolor: isCritical ? "#ffebee" : "#fff8e1",
        color: isCritical ? "#c62828" : "#f57f17",
        fontWeight: 500,
        height: 22,
        fontSize: "0.7rem",
      }}
    />
  );
}
