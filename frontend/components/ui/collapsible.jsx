"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";

/**
 * Collapsible — minimal disclosure primitive used by Section 2 panels
 * (IntegrityPanel, FeatureFiringPanel) in Phase 4c.
 *
 * Three composable parts, matching the shadcn pattern used elsewhere in
 * the ui/ folder:
 *
 *   <Collapsible defaultOpen={false}>
 *     <CollapsibleTrigger>  always-visible header (click to toggle)
 *     <CollapsibleContent>  hidden when collapsed
 *   </Collapsible>
 *
 * Implementation notes:
 *   - State is held inside <Collapsible> via React.useState. No external
 *     state library, no Radix UI dependency.
 *   - Open/close is communicated to children via React Context so trigger
 *     and content stay in sync without prop drilling.
 *   - The chevron rotation is a pure Tailwind transform driven by the
 *     `data-state` attribute we set on the trigger.
 *   - Accessible: trigger renders as a <button>, content is hidden via
 *     conditional rendering (not display:none) so non-visible content
 *     isn't focusable.
 */

const CollapsibleContext = React.createContext({
  open: false,
  setOpen: () => {},
});

export function Collapsible({
  children,
  defaultOpen = false,
  open: controlledOpen,
  onOpenChange,
  className = "",
}) {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(defaultOpen);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : uncontrolledOpen;

  const setOpen = React.useCallback(
    (next) => {
      if (!isControlled) setUncontrolledOpen(next);
      onOpenChange?.(next);
    },
    [isControlled, onOpenChange]
  );

  return (
    <CollapsibleContext.Provider value={{ open, setOpen }}>
      <div className={className} data-state={open ? "open" : "closed"}>
        {children}
      </div>
    </CollapsibleContext.Provider>
  );
}

export function CollapsibleTrigger({ children, className = "" }) {
  const { open, setOpen } = React.useContext(CollapsibleContext);
  return (
    <button
      type="button"
      onClick={() => setOpen(!open)}
      data-state={open ? "open" : "closed"}
      aria-expanded={open}
      className={
        "w-full flex items-center justify-between gap-3 text-left " +
        "transition-colors hover:bg-muted/40 focus-visible:outline-none " +
        "focus-visible:ring-2 focus-visible:ring-ring rounded-md " +
        className
      }
    >
      <div className="flex-1 min-w-0">{children}</div>
      <ChevronDown
        className={
          "h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 " +
          (open ? "rotate-180" : "")
        }
        aria-hidden="true"
      />
    </button>
  );
}

export function CollapsibleContent({ children, className = "" }) {
  const { open } = React.useContext(CollapsibleContext);
  if (!open) return null;
  return <div className={className}>{children}</div>;
}
