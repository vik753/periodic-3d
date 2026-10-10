/**
 * Static facts about the periodic table layout.
 *
 * Names, masses and other properties come from the dataset (pipeline output).
 * This module only holds what never changes and is needed for the first paint:
 * symbols, grid positions, blocks, categories and electron shells.
 */

export const SYMBOLS = [
  'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
  'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr',
  'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe',
  'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu',
  'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn',
  'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr',
  'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og',
] as const;

export type ElementSymbol = (typeof SYMBOLS)[number];

export type Category =
  | 'alkali-metal'
  | 'alkaline-earth-metal'
  | 'transition-metal'
  | 'post-transition-metal'
  | 'metalloid'
  | 'reactive-nonmetal'
  | 'noble-gas'
  | 'lanthanide'
  | 'actinide'
  | 'unknown';

export type Block = 's' | 'p' | 'd' | 'f';

export interface ElementCell {
  z: number;
  symbol: ElementSymbol;
  period: number;
  /** IUPAC group 1–18; null for the lanthanides and actinides of the f-block rows. */
  group: number | null;
  block: Block;
  category: Category;
  /** Grid column 1–18. */
  col: number;
  /** Grid row: 1–7 for the main table, 9 and 10 for the f-block rows. */
  row: number;
}

export function periodOf(z: number): number {
  if (z <= 2) return 1;
  if (z <= 10) return 2;
  if (z <= 18) return 3;
  if (z <= 36) return 4;
  if (z <= 54) return 5;
  if (z <= 86) return 6;
  return 7;
}

export function isLanthanide(z: number): boolean {
  return z >= 57 && z <= 71;
}

export function isActinide(z: number): boolean {
  return z >= 89 && z <= 103;
}

export function groupOf(z: number): number | null {
  if (z === 1) return 1;
  if (z === 2) return 18;
  if (z <= 10) return z <= 4 ? z - 2 : z + 8;
  if (z <= 18) return z <= 12 ? z - 10 : z;
  if (z <= 36) return z - 18;
  if (z <= 54) return z - 36;
  if (z <= 86) {
    if (z <= 56) return z - 54;
    if (isLanthanide(z)) return null;
    return z - 68;
  }
  if (z <= 88) return z - 86;
  if (isActinide(z)) return null;
  return z - 100;
}

export function blockOf(z: number): Block {
  if (isLanthanide(z) || isActinide(z)) return 'f';
  if (z === 2) return 's';
  const group = groupOf(z) ?? 0;
  if (group <= 2) return 's';
  if (group >= 13) return 'p';
  return 'd';
}

const ALKALI = new Set([3, 11, 19, 37, 55, 87]);
const ALKALINE_EARTH = new Set([4, 12, 20, 38, 56, 88]);
const METALLOID = new Set([5, 14, 32, 33, 51, 52, 85]);
const REACTIVE_NONMETAL = new Set([1, 6, 7, 8, 9, 15, 16, 17, 34, 35, 53]);
const NOBLE_GAS = new Set([2, 10, 18, 36, 54, 86]);
const POST_TRANSITION = new Set([13, 31, 49, 50, 81, 82, 83, 84]);

export function categoryOf(z: number): Category {
  if (isLanthanide(z)) return 'lanthanide';
  if (isActinide(z)) return 'actinide';
  if (z >= 109) return 'unknown';
  if (ALKALI.has(z)) return 'alkali-metal';
  if (ALKALINE_EARTH.has(z)) return 'alkaline-earth-metal';
  if (METALLOID.has(z)) return 'metalloid';
  if (REACTIVE_NONMETAL.has(z)) return 'reactive-nonmetal';
  if (NOBLE_GAS.has(z)) return 'noble-gas';
  if (POST_TRANSITION.has(z)) return 'post-transition-metal';
  return 'transition-metal';
}

function gridOf(z: number): { col: number; row: number } {
  if (isLanthanide(z)) return { col: z - 54, row: 9 };
  if (isActinide(z)) return { col: z - 86, row: 10 };
  return { col: groupOf(z) ?? 3, row: periodOf(z) };
}

export const ELEMENTS: readonly ElementCell[] = SYMBOLS.map((symbol, index) => {
  const z = index + 1;
  return {
    z,
    symbol,
    period: periodOf(z),
    group: groupOf(z),
    block: blockOf(z),
    category: categoryOf(z),
    ...gridOf(z),
  };
});

const BY_SYMBOL = new Map<string, ElementCell>(ELEMENTS.map((cell) => [cell.symbol, cell]));

export function elementBySymbol(symbol: string): ElementCell | undefined {
  return BY_SYMBOL.get(symbol);
}

export function elementByZ(z: number): ElementCell | undefined {
  return ELEMENTS[z - 1];
}

// ---------------------------------------------------------------------------
// Electron shells (Bohr model), from the Madelung rule plus known exceptions.
// The dataset can override this with configurations from PubChem.
// ---------------------------------------------------------------------------

const SUBSHELL_ORDER: ReadonlyArray<readonly [n: number, l: number]> = [
  [1, 0], [2, 0], [2, 1], [3, 0], [3, 1], [4, 0], [3, 2], [4, 1], [5, 0], [4, 2],
  [5, 1], [6, 0], [4, 3], [5, 2], [6, 1], [7, 0], [5, 3], [6, 2], [7, 1],
];
const SUBSHELL_LETTER = ['s', 'p', 'd', 'f'] as const;
const SUBSHELL_CAPACITY = [2, 6, 10, 14] as const;

/** Ground-state configurations that differ from the Madelung order (NIST). */
const CONFIGURATION_EXCEPTIONS: Readonly<Record<number, Readonly<Record<string, number>>>> = {
  24: { '3d': 5, '4s': 1 },
  29: { '3d': 10, '4s': 1 },
  41: { '4d': 4, '5s': 1 },
  42: { '4d': 5, '5s': 1 },
  44: { '4d': 7, '5s': 1 },
  45: { '4d': 8, '5s': 1 },
  46: { '4d': 10, '5s': 0 },
  47: { '4d': 10, '5s': 1 },
  57: { '4f': 0, '5d': 1 },
  58: { '4f': 1, '5d': 1 },
  64: { '4f': 7, '5d': 1 },
  78: { '5d': 9, '6s': 1 },
  79: { '5d': 10, '6s': 1 },
  89: { '5f': 0, '6d': 1 },
  90: { '5f': 0, '6d': 2 },
  91: { '5f': 2, '6d': 1 },
  92: { '5f': 3, '6d': 1 },
  93: { '5f': 4, '6d': 1 },
  96: { '5f': 7, '6d': 1 },
  103: { '6d': 0, '7p': 1 },
};

/** Electron configuration as an ordered list of [subshell, electrons], e.g. [["1s", 2], ...]. */
export function configurationOf(z: number): Array<[string, number]> {
  const filled = new Map<string, number>();
  let remaining = z;
  for (const [n, l] of SUBSHELL_ORDER) {
    if (remaining <= 0) break;
    const take = Math.min(remaining, SUBSHELL_CAPACITY[l] ?? 0);
    filled.set(`${n}${SUBSHELL_LETTER[l]}`, take);
    remaining -= take;
  }
  const exceptions = CONFIGURATION_EXCEPTIONS[z];
  if (exceptions) {
    for (const [subshell, electrons] of Object.entries(exceptions)) filled.set(subshell, electrons);
  }
  return [...filled.entries()].filter(([, electrons]) => electrons > 0);
}

/** Electrons per shell n = 1, 2, 3, … */
export function shellsOf(z: number): number[] {
  const shells: number[] = [];
  for (const [subshell, electrons] of configurationOf(z)) {
    const n = Number(subshell[0]);
    shells[n - 1] = (shells[n - 1] ?? 0) + electrons;
  }
  return Array.from(shells, (count) => count ?? 0);
}

/** Rough mass number for drawing the nucleus until the dataset provides the real mass. */
export function approximateMassNumber(z: number): number {
  if (z === 1) return 1;
  return Math.round(2 * z + 0.0063 * z * z);
}

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

const SUPERSCRIPT_DIGITS = '⁰¹²³⁴⁵⁶⁷⁸⁹';
const NOBLE_CORES: ReadonlyArray<[number, string]> = [
  [86, 'Rn'],
  [54, 'Xe'],
  [36, 'Kr'],
  [18, 'Ar'],
  [10, 'Ne'],
  [2, 'He'],
];
const SUBSHELL_RANK: Record<string, number> = { s: 0, p: 1, d: 2, f: 3 };

function superscript(value: number): string {
  return String(value)
    .split('')
    .map((digit) => SUPERSCRIPT_DIGITS[Number(digit)] ?? digit)
    .join('');
}

/** Condensed notation, e.g. Fe → [Ar] 3d⁶ 4s². */
export function condensedConfiguration(z: number): string {
  const core = NOBLE_CORES.find(([coreZ]) => coreZ < z);
  const full = configurationOf(z);
  let rest = full;
  let prefix = '';
  if (core) {
    const coreSubshells = new Map(configurationOf(core[0]));
    rest = full.filter(([subshell, electrons]) => coreSubshells.get(subshell) !== electrons);
    prefix = `[${core[1]}] `;
  }
  const sorted = [...rest].sort(
    ([a], [b]) => Number(a[0]) - Number(b[0]) || (SUBSHELL_RANK[a[1]!] ?? 0) - (SUBSHELL_RANK[b[1]!] ?? 0),
  );
  return prefix + sorted.map(([subshell, electrons]) => `${subshell}${superscript(electrons)}`).join(' ');
}
