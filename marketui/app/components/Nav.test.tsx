import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

import Nav from "./Nav";

describe("Nav", () => {
  it("renders the Quantica brand link", () => {
    render(<Nav />);
    expect(screen.getByText("Quantica")).toBeInTheDocument();
    expect(screen.getByText("Quantica").closest("a")).toHaveAttribute(
      "href",
      "/"
    );
  });

  it("renders all navigation links", () => {
    render(<Nav />);
    expect(screen.getByText("Feed")).toBeInTheDocument();
    expect(screen.getByText("Trades")).toBeInTheDocument();
    expect(screen.getByText("Docs")).toBeInTheDocument();
  });

  it("highlights the active link", () => {
    render(<Nav />);
    const feedLink = screen.getByText("Feed");
    expect(feedLink.className).toContain("text-foreground");
    expect(feedLink.className).toContain("font-medium");
  });

  it("non-active links have muted styling", () => {
    render(<Nav />);
    const tradesLink = screen.getByText("Trades");
    expect(tradesLink.className).toContain("text-muted");
  });
});
