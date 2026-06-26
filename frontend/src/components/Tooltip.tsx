// Hover tooltip wrapper. Wraps a labelled control and shows a Vietnamese hint
// on hover/focus. Pure CSS positioning (no portal, no lib).

import type { ReactNode } from "react";

export function Tooltip({
  hint,
  children,
}: {
  hint: string;
  children: ReactNode;
}) {
  return (
    <span className="tooltip">
      {children}
      <span className="tooltip-bubble" role="tooltip">
        {hint}
      </span>
    </span>
  );
}
