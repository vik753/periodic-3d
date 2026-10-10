import * as THREE from 'three';

import type { ElementCell } from '../data/periodic';
import type { Vec3 } from '../data/structure';

/** Tile size and spacing in world units. */
export const TILE = 1;
export const TILE_GAP = 0.14;
export const TILE_DEPTH = 0.16;
const STEP = TILE + TILE_GAP;

/** The table is bent into a gentle concave arc, like a panoramic screen. */
const CURVE = 0.016;

/** Half extents of the table, used to fit the camera. */
export const TABLE_HALF_WIDTH = 10.3;
export const TABLE_HALF_HEIGHT = 5.45;

/** Where compound structures are shown: in front of the table. */
export const STAGE_POSITION: Vec3 = [0, 0, 7];

function rowY(row: number): number {
  // f-block rows (9 and 10) sit half a row below period 7.
  return row <= 7 ? row : row - 0.5;
}

export function tilePosition(cell: Pick<ElementCell, 'col' | 'row'>): Vec3 {
  const x = (cell.col - 9.5) * STEP;
  const y = (5.25 - rowY(cell.row)) * STEP;
  const z = CURVE * x * x;
  return [x, y, z];
}

/** Rotation around Y so each tile faces the centre axis of the arc. */
export function tileYaw(x: number): number {
  return -Math.atan(2 * CURVE * x);
}

const scratchQuaternion = new THREE.Quaternion();
const scratchEuler = new THREE.Euler();
const scratchPosition = new THREE.Vector3();
const scratchScale = new THREE.Vector3();

/** Matrix of a tile, optionally pushed towards the viewer and scaled. */
export function tileMatrix(
  position: Vec3,
  out: THREE.Matrix4,
  options: { scale?: number; lift?: number; zOffset?: number } = {},
): THREE.Matrix4 {
  const { scale = 1, lift = 0, zOffset = 0 } = options;
  const yaw = tileYaw(position[0]);
  scratchEuler.set(0, yaw, 0);
  scratchQuaternion.setFromEuler(scratchEuler);
  // Move along the tile normal (towards the viewer) by `lift` and `zOffset`.
  const forward = lift + zOffset;
  scratchPosition.set(position[0] + Math.sin(yaw) * forward, position[1], position[2] + Math.cos(yaw) * forward);
  scratchScale.setScalar(scale);
  return out.compose(scratchPosition, scratchQuaternion, scratchScale);
}

/** How far the curved edges of the table come towards the viewer. */
export const TABLE_EDGE_Z = CURVE * (TABLE_HALF_WIDTH - TILE / 2) ** 2;

/**
 * Camera distance that fits the whole table for a given aspect ratio and vertical FOV.
 * The curved edges are closer to the camera, so they need extra distance. A margin
 * keeps the table clear of the top bar and the hint at the bottom.
 */
export function tableFitDistance(aspect: number, fovDegrees: number): number {
  const halfV = Math.tan(THREE.MathUtils.degToRad(fovDegrees / 2));
  const halfH = halfV * aspect;
  const byHeight = (TABLE_HALF_HEIGHT * 1.16) / halfV;
  const byWidth = (TABLE_HALF_WIDTH * 1.05) / halfH + TABLE_EDGE_Z;
  return Math.max(byHeight, byWidth);
}
