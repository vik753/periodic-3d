import type { ReactNode } from 'react';

/**
 * A formula and a name in one list row. The formula never shrinks into the name: when
 * both do not fit with at least 7rem for the name, the name moves to the next line.
 * A formula wider than the row wraps inside itself.
 */
export function FormulaRow({
  formula,
  name,
  formulaClassName = 'min-w-[4.5rem] font-display text-sm font-medium',
}: {
  formula: ReactNode;
  name?: ReactNode;
  formulaClassName?: string;
}) {
  return (
    <span className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-3 gap-y-0.5">
      <span className={`max-w-full shrink-0 [overflow-wrap:anywhere] ${formulaClassName}`}>{formula}</span>
      {name ? <span className="min-w-[7rem] flex-1 basis-0 truncate text-sm text-muted">{name}</span> : null}
    </span>
  );
}
