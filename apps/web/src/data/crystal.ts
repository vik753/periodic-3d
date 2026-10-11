/**
 * Builds a displayable crystal from the compact unit cell of a predicted material
 * (GNoME layer, ADR 0007). The API sends only the cell parameters and the atoms; the
 * browser closes the cell with atoms on its far faces, repeats tiny cells into a block
 * and adds bonds by distance. The rules match the pipeline's crystal builder
 * (pipeline/src/p3d_pipeline/structures.py), so known and predicted crystals look alike.
 */

import { covalentRadius, NONMETALS } from './chemistry';
import { SYMBOLS } from './periodic';
import type { StructureAtom, StructureBond, StructureData, Vec3 } from './structure';

/** The cell as the API sends it (MaterialStructure in apps/api/src/p3d_api/schemas.py). */
export interface CompactCell {
  /** a, b, c in ångström; alpha, beta, gamma in degrees. */
  cell: number[];
  /** base64 of 7-byte records: Z (uint8), then x, y, z ×10⁴ (uint16, little-endian). */
  sites: string;
}

export interface Site {
  el: string;
  /** Fractional coordinates in [0, 1). */
  frac: Vec3;
}

const FRACTION_SCALE = 10_000;
const RECORD_BYTES = 7;
const BOUNDARY_EPS = 1e-3;
const MAX_ATOMS = 160;
const MAX_BONDS_PER_ATOM = 12;
const METAL_SHELL = 1.12; // metals and alloys: only the nearest-neighbour shell is drawn
const SMALL_CELL_SITES = 8;
const SUPERCELL_TARGET = 6; // Å: a block of cells should be at least this long on each side
const SUPERCELL_MAX_SITES = 64;

export function decodeSites(base64: string): Site[] {
  let binary: string;
  try {
    binary = atob(base64);
  } catch {
    return [];
  }
  const word = (at: number) => binary.charCodeAt(at) | (binary.charCodeAt(at + 1) << 8);
  const sites: Site[] = [];
  for (let offset = 0; offset + RECORD_BYTES <= binary.length; offset += RECORD_BYTES) {
    const symbol = SYMBOLS[binary.charCodeAt(offset) - 1];
    if (!symbol) continue;
    sites.push({
      el: symbol,
      frac: [
        word(offset + 1) / FRACTION_SCALE,
        word(offset + 3) / FRACTION_SCALE,
        word(offset + 5) / FRACTION_SCALE,
      ],
    });
  }
  return sites;
}

/** Cell parameters → lattice vectors: a along x, b in the xy plane (the usual convention). */
export function latticeVectors(parameters: number[]): [Vec3, Vec3, Vec3] {
  const [a = 1, b = 1, c = 1, alpha = 90, beta = 90, gamma = 90] = parameters;
  const rad = Math.PI / 180;
  const cosA = Math.cos(alpha * rad);
  const cosB = Math.cos(beta * rad);
  const cosG = Math.cos(gamma * rad);
  const sinG = Math.sin(gamma * rad) || 1;
  const cx = c * cosB;
  const cy = (c * (cosA - cosB * cosG)) / sinG;
  const cz = Math.sqrt(Math.max(c * c - cx * cx - cy * cy, 0));
  return [
    [a, 0, 0],
    [b * cosG, b * sinG, 0],
    [cx, cy, cz],
  ];
}

function toCartesian(frac: Vec3, lattice: [Vec3, Vec3, Vec3]): Vec3 {
  const [a, b, c] = lattice;
  return [
    frac[0] * a[0] + frac[1] * b[0] + frac[2] * c[0],
    frac[0] * a[1] + frac[1] * b[1] + frac[2] * c[1],
    frac[0] * a[2] + frac[1] * b[2] + frac[2] * c[2],
  ];
}

/** How many cells to show along a, b, c: more than one only for tiny cells. */
export function supercellRepeats(lattice: [Vec3, Vec3, Vec3], sites: number): [number, number, number] {
  if (sites >= SMALL_CELL_SITES) return [1, 1, 1];
  const lengths = lattice.map((vector) => Math.hypot(...vector));
  const target = Math.max(SUPERCELL_TARGET, ...lengths);
  const repeats = lengths.map((length) => Math.min(3, Math.max(1, Math.round(target / length))));
  while (sites * repeats[0]! * repeats[1]! * repeats[2]! > SUPERCELL_MAX_SITES) {
    const largest = repeats.indexOf(Math.max(...repeats));
    repeats[largest]! -= 1;
  }
  return [repeats[0]!, repeats[1]!, repeats[2]!];
}

/** Atoms on a face (coordinate 0) get a copy on the opposite face, so the cell looks closed. */
function withBoundaryImages(sites: Site[]): Site[] {
  const points: Site[] = [];
  for (const site of sites) {
    const wrapped = site.frac.map((value) => {
      const inside = value - Math.floor(value);
      return inside > 1 - BOUNDARY_EPS ? 0 : inside;
    }) as Vec3;
    const options = wrapped.map((value) => (value < BOUNDARY_EPS ? [0, 1] : [0]));
    for (const dx of options[0]!) {
      for (const dy of options[1]!) {
        for (const dz of options[2]!) {
          points.push({ el: site.el, frac: [wrapped[0] + dx, wrapped[1] + dy, wrapped[2] + dz] });
        }
      }
    }
  }
  return points;
}

/** Distance-based bonds; metal–metal bonds are skipped when the crystal has anions. */
export function crystalBonds(atoms: StructureAtom[]): StructureBond[] {
  const count = atoms.length;
  if (count < 2) return [];
  const nonmetal = atoms.map((atom) => NONMETALS.has(atom.el));
  const hasNonmetal = nonmetal.some(Boolean);
  const radii = atoms.map((atom) => covalentRadius(atom.el));
  const distances: number[] = [];
  let nearest = Infinity;
  for (let i = 0; i < count; i += 1) {
    for (let j = i + 1; j < count; j += 1) {
      const a = atoms[i]!;
      const b = atoms[j]!;
      const distance = Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
      distances.push(distance);
      if (distance > 0.4) nearest = Math.min(nearest, distance);
    }
  }
  const metalShell = !hasNonmetal && Number.isFinite(nearest) ? nearest * METAL_SHELL : Infinity;
  const candidates: Array<[number, number, number]> = [];
  let index = 0;
  for (let i = 0; i < count; i += 1) {
    for (let j = i + 1; j < count; j += 1) {
      const distance = distances[index]!;
      index += 1;
      const bothNonmetal = nonmetal[i]! && nonmetal[j]!;
      const bothMetal = !nonmetal[i]! && !nonmetal[j]!;
      if (hasNonmetal && bothMetal) continue;
      const cutoff = Math.min((radii[i]! + radii[j]!) * (bothNonmetal ? 1.1 : 1.2), metalShell);
      if (distance > 0.4 && distance <= cutoff) candidates.push([distance, i, j]);
    }
  }
  candidates.sort((x, y) => x[0] - y[0]);
  const degree = new Array<number>(count).fill(0);
  const bonds: StructureBond[] = [];
  for (const [, i, j] of candidates) {
    if (degree[i]! >= MAX_BONDS_PER_ATOM || degree[j]! >= MAX_BONDS_PER_ATOM) continue;
    degree[i]! += 1;
    degree[j]! += 1;
    bonds.push([i, j, 1]);
  }
  return bonds;
}

/** The unit cell for display: closed with boundary images, tiny cells as a block, with bonds. */
export function crystalFromCell(compact: CompactCell): StructureData | null {
  const sites = decodeSites(compact.sites);
  if (sites.length === 0 || compact.cell.length < 6) return null;
  const lattice = latticeVectors(compact.cell);
  const repeats = supercellRepeats(lattice, sites.length);
  const block: Site[] = [];
  for (let i = 0; i < repeats[0]; i += 1) {
    for (let j = 0; j < repeats[1]; j += 1) {
      for (let k = 0; k < repeats[2]; k += 1) {
        for (const site of sites) {
          block.push({
            el: site.el,
            frac: [(site.frac[0] + i) / repeats[0], (site.frac[1] + j) / repeats[1], (site.frac[2] + k) / repeats[2]],
          });
        }
      }
    }
  }
  const blockLattice = lattice.map((vector, axis) => vector.map((value) => value * repeats[axis]!)) as [Vec3, Vec3, Vec3];
  let points = withBoundaryImages(block);
  if (points.length > MAX_ATOMS * 1.6) points = block;
  const atoms = points.map((point) => {
    const [x, y, z] = toCartesian(point.frac, blockLattice);
    return { el: point.el, x, y, z };
  });
  return { kind: 'crystal', atoms, bonds: crystalBonds(atoms), cell: lattice, cellOrigin: [0, 0, 0] };
}
