/**
 * Built-in demo structures for the stage-0 prototype.
 * Geometry is computed from standard bond lengths, not fetched.
 * The real dataset replaces these in stage 1.
 */

import type { StructureAtom, StructureBond, StructureData } from './structure';

function benzene(): StructureData {
  const atoms: StructureAtom[] = [];
  const bonds: StructureBond[] = [];
  const cc = 1.39;
  const ch = 1.09;
  for (let i = 0; i < 6; i += 1) {
    const angle = (Math.PI / 3) * i;
    atoms.push({ el: 'C', x: cc * Math.cos(angle), y: cc * Math.sin(angle), z: 0 });
  }
  for (let i = 0; i < 6; i += 1) {
    const angle = (Math.PI / 3) * i;
    atoms.push({ el: 'H', x: (cc + ch) * Math.cos(angle), y: (cc + ch) * Math.sin(angle), z: 0 });
  }
  for (let i = 0; i < 6; i += 1) {
    bonds.push([i, (i + 1) % 6, i % 2 === 0 ? 2 : 1]);
    bonds.push([i, i + 6, 1]);
  }
  return { kind: 'molecule', atoms, bonds };
}

function water(): StructureData {
  return {
    kind: 'molecule',
    atoms: [
      { el: 'O', x: 0, y: 0, z: 0 },
      { el: 'H', x: 0.7572, y: 0.5865, z: 0 },
      { el: 'H', x: -0.7572, y: 0.5865, z: 0 },
    ],
    bonds: [
      [0, 1, 1],
      [0, 2, 1],
    ],
  };
}

/** Rock-salt conventional cell (a = 5.64 Å): a 3×3×3 grid of half-cell sites. */
function sodiumChloride(): StructureData {
  const a = 5.64;
  const half = a / 2;
  const atoms: StructureAtom[] = [];
  const index = new Map<string, number>();
  for (let i = 0; i <= 2; i += 1) {
    for (let j = 0; j <= 2; j += 1) {
      for (let k = 0; k <= 2; k += 1) {
        index.set(`${i}${j}${k}`, atoms.length);
        atoms.push({ el: (i + j + k) % 2 === 0 ? 'Na' : 'Cl', x: i * half, y: j * half, z: k * half });
      }
    }
  }
  const bonds: StructureBond[] = [];
  for (let i = 0; i <= 2; i += 1) {
    for (let j = 0; j <= 2; j += 1) {
      for (let k = 0; k <= 2; k += 1) {
        const from = index.get(`${i}${j}${k}`)!;
        if (i < 2) bonds.push([from, index.get(`${i + 1}${j}${k}`)!, 1]);
        if (j < 2) bonds.push([from, index.get(`${i}${j + 1}${k}`)!, 1]);
        if (k < 2) bonds.push([from, index.get(`${i}${j}${k + 1}`)!, 1]);
      }
    }
  }
  return {
    kind: 'crystal',
    atoms,
    bonds,
    cell: [
      [a, 0, 0],
      [0, a, 0],
      [0, 0, a],
    ],
    cellOrigin: [0, 0, 0],
  };
}

export interface DemoCompound {
  id: string;
  formula: string;
  names: Record<'en' | 'ru' | 'uk', string>;
  structure: StructureData;
}

export const DEMO_COMPOUNDS: readonly DemoCompound[] = [
  {
    id: 'demo-benzene',
    formula: 'C₆H₆',
    names: { en: 'Benzene', ru: 'Бензол', uk: 'Бензен' },
    structure: benzene(),
  },
  {
    id: 'demo-water',
    formula: 'H₂O',
    names: { en: 'Water', ru: 'Вода', uk: 'Вода' },
    structure: water(),
  },
  {
    id: 'demo-nacl',
    formula: 'NaCl',
    names: { en: 'Sodium chloride', ru: 'Хлорид натрия', uk: 'Натрій хлорид' },
    structure: sodiumChloride(),
  },
];

export function demoCompound(id: string): DemoCompound | undefined {
  return DEMO_COMPOUNDS.find((compound) => compound.id === id);
}
