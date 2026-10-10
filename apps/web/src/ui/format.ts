/** Number formatting in the interface language: "55,845" in Ukrainian, "55.845" in English. */
export function formatNumber(value: number, language: string, maximumFractionDigits = 3): string {
  return new Intl.NumberFormat(language, { maximumFractionDigits }).format(value);
}

/** Ion charge with a true minus sign: +1, −2. */
export function formatCharge(charge: number): string {
  if (charge === 0) return '0';
  return charge > 0 ? `+${charge}` : `−${Math.abs(charge)}`;
}

/** Atom count in a composition: integers as is, fractions with two digits. */
export function formatCount(value: number, language: string): string {
  return Number.isInteger(value) ? String(value) : formatNumber(value, language, 2);
}
