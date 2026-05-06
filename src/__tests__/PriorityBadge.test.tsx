import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PriorityBadge } from "../SkillGapPage";

describe("PriorityBadge", () => {
  it("renders the priority label", () => {
    render(<PriorityBadge p="High" />);
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("applies red styling for High priority", () => {
    const { container } = render(<PriorityBadge p="High" />);
    const span = container.querySelector("span");
    expect(span?.className).toContain("bg-red-100");
    expect(span?.className).toContain("text-red-800");
  });

  it("applies amber styling for Medium priority", () => {
    const { container } = render(<PriorityBadge p="Medium" />);
    const span = container.querySelector("span");
    expect(span?.className).toContain("bg-amber-100");
    expect(span?.className).toContain("text-amber-800");
  });

  it("applies green styling for Low priority", () => {
    const { container } = render(<PriorityBadge p="Low" />);
    const span = container.querySelector("span");
    expect(span?.className).toContain("bg-emerald-100");
    expect(span?.className).toContain("text-emerald-800");
  });

  it("renders as an inline-flex span", () => {
    const { container } = render(<PriorityBadge p="Low" />);
    const span = container.querySelector("span");
    expect(span?.tagName).toBe("SPAN");
    expect(span?.className).toContain("inline-flex");
  });
});
