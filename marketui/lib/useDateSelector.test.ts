import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDateSelector } from "./useDateSelector";

describe("useDateSelector", () => {
  it("auto-selects the first date when dates are available", () => {
    const { result } = renderHook(() =>
      useDateSelector(["2026-08-01", "2026-07-31"])
    );
    expect(result.current.activeDate).toBe("2026-08-01");
  });

  it("returns null when no dates are available", () => {
    const { result } = renderHook(() => useDateSelector([]));
    expect(result.current.activeDate).toBeNull();
  });

  it("selects a date when toggle is called", () => {
    const { result } = renderHook(() =>
      useDateSelector(["2026-08-01", "2026-07-31"])
    );

    act(() => result.current.toggle("2026-07-31"));
    expect(result.current.activeDate).toBe("2026-07-31");
  });

  it("closes the panel when toggling the active date", () => {
    const { result } = renderHook(() =>
      useDateSelector(["2026-08-01", "2026-07-31"])
    );

    // First date is auto-selected; toggle it to close
    act(() => result.current.toggle("2026-08-01"));
    expect(result.current.activeDate).toBeNull();
  });

  it("re-opens a different date after closing", () => {
    const { result } = renderHook(() =>
      useDateSelector(["2026-08-01", "2026-07-31"])
    );

    // Close
    act(() => result.current.toggle("2026-08-01"));
    expect(result.current.activeDate).toBeNull();

    // Open a different date
    act(() => result.current.toggle("2026-07-31"));
    expect(result.current.activeDate).toBe("2026-07-31");
  });

  it("toggles the same date off and on again", () => {
    const { result } = renderHook(() =>
      useDateSelector(["2026-08-01"])
    );

    act(() => result.current.toggle("2026-08-01")); // close
    expect(result.current.activeDate).toBeNull();

    act(() => result.current.toggle("2026-08-01")); // re-open
    expect(result.current.activeDate).toBe("2026-08-01");
  });
});
