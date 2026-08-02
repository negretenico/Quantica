"use client";

import { useState } from "react";

type DateState = string | null | undefined;

export function useDateSelector(dates: string[]) {
  // undefined = user hasn't interacted yet (auto-select first date)
  // null      = user explicitly closed the panel
  // string    = user picked a date
  const [selected, setSelected] = useState<DateState>(undefined);

  const activeDate =
    selected === undefined
      ? dates.length > 0
        ? dates[0]
        : null
      : selected;

  const toggle = (date: string) =>
    setSelected(activeDate === date ? null : date);

  return { activeDate, toggle } as const;
}
