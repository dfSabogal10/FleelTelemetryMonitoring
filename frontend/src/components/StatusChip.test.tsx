import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusChip } from "./StatusChip";

describe("StatusChip", () => {
  it("renders title-case label for a known status", () => {
    render(<StatusChip status="moving" />);
    expect(screen.getByText("Moving")).toBeInTheDocument();
  });

  it("renders idle with stable styling label", () => {
    render(<StatusChip status="IDLE" />);
    expect(screen.getByText("Idle")).toBeInTheDocument();
  });
});
