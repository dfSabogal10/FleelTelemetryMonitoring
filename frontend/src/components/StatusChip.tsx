import { Chip } from "@mui/material";

const STATUS_COLORS: Record<
  string,
  { bg: string; color: string; label?: string }
> = {
  idle: { bg: "#e3f2fd", color: "#1565c0" },
  moving: { bg: "#e8f5e9", color: "#2e7d32" },
  charging: { bg: "#fff3e0", color: "#ef6c00" },
  fault: { bg: "#ffebee", color: "#c62828" },
};

interface StatusChipProps {
  status: string;
}

export function StatusChip({ status }: StatusChipProps) {
  const key = status.toLowerCase();
  const palette = STATUS_COLORS[key] ?? { bg: "#f5f5f5", color: "#616161" };
  const label = status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();

  return (
    <Chip
      label={label}
      size="small"
      sx={{
        bgcolor: palette.bg,
        color: palette.color,
        fontWeight: 500,
        height: 26,
      }}
    />
  );
}
