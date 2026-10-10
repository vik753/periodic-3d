/**
 * 3D structure format shared by molecules and crystal fragments.
 * Coordinates are in ångström. The pipeline produces the same shape.
 */

export type Vec3 = [number, number, number];

export interface StructureAtom {
  el: string;
  x: number;
  y: number;
  z: number;
}

/** [atom index a, atom index b, bond order 1 | 2 | 3 (1.5 for aromatic)] */
export type StructureBond = [number, number, number];

export interface StructureData {
  kind: 'molecule' | 'crystal' | 'flat';
  atoms: StructureAtom[];
  bonds: StructureBond[];
  /** Unit-cell vectors for crystals, drawn as a thin frame. */
  cell?: [Vec3, Vec3, Vec3];
  /** Origin of the unit-cell frame. */
  cellOrigin?: Vec3;
}

export function centroid(atoms: StructureAtom[]): Vec3 {
  if (atoms.length === 0) return [0, 0, 0];
  let x = 0;
  let y = 0;
  let z = 0;
  for (const atom of atoms) {
    x += atom.x;
    y += atom.y;
    z += atom.z;
  }
  return [x / atoms.length, y / atoms.length, z / atoms.length];
}

/** Largest distance from the centroid, used to fit the structure into view. */
export function boundingRadius(atoms: StructureAtom[]): number {
  const [cx, cy, cz] = centroid(atoms);
  let radius = 0;
  for (const atom of atoms) {
    radius = Math.max(radius, Math.hypot(atom.x - cx, atom.y - cy, atom.z - cz));
  }
  return radius;
}
