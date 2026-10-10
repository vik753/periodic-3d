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

/** Screen layout of the info panel: side panel on wide screens, bottom sheet on phones. */
export const PANEL_LAYOUT = { sideMinWidth: 640, sideWidth: 380, sheetFraction: 0.46 } as const;

/** Where compound structures are shown: in front of the table. */
export const STAGE_POSITION: Vec3 = [0, 0, 7];

/** The multi-element cloud floats where single compounds are shown. */
export const CLOUD_CENTER: Vec3 = STAGE_POSITION;
export const CLOUD_RADIUS = 3.4;

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

/** Where the table group sits and how large it is. */
export interface TableTransform {
  position: Vec3;
  scale: number;
}

export const TABLE_AT_REST: TableTransform = { position: [0, 0, 0], scale: 1 };

/** How far the table moves back when the visitor "falls into" an element. */
export const RECEDE_DEPTH = 17;
/** Distance from the camera to the atom in the element scene (see CameraDirector). */
export const ELEMENT_VIEW_DISTANCE = 6.45;

/**
 * Element scene: the table moves far behind the atom and shrinks, centred on the chosen
 * tile. The rays then run from the atom "into the distance" to the partner tiles, and
 * the whole table stays inside the area that the info panel leaves free.
 */
export function recededTable(
  cell: Pick<ElementCell, 'col' | 'row'>,
  viewport: { width: number; height: number },
  fovDegrees: number,
  panel: { sideWidth: number; sheetFraction: number; sideMinWidth: number } = PANEL_LAYOUT,
): TableTransform {
  const [px, py, pz] = tilePosition(cell);
  const depth = ELEMENT_VIEW_DISTANCE + RECEDE_DEPTH;
  const tanV = Math.tan(THREE.MathUtils.degToRad(fovDegrees / 2));
  const aspect = viewport.width / Math.max(viewport.height, 1);
  const side = viewport.width >= panel.sideMinWidth;
  const halfV = tanV * depth * (side ? 1 : 1 - panel.sheetFraction);
  const halfH = tanV * aspect * depth * (side ? Math.max(0.35, 1 - panel.sideWidth / viewport.width) : 1);
  const extentH = Math.max(TABLE_HALF_WIDTH + px, TABLE_HALF_WIDTH - px);
  const extentV = Math.max(TABLE_HALF_HEIGHT + py, TABLE_HALF_HEIGHT - py);
  // Perspective and the curved edges make the table look larger than its flat extent: keep a margin.
  const scale = Math.min(0.62, (0.74 * halfH) / extentH, (0.8 * halfV) / extentV);
  return { position: [px - scale * px, py - scale * py, pz - RECEDE_DEPTH - scale * pz], scale };
}

/**
 * Cloud scene: the whole table moves far back as a backdrop, centred, so the floating
 * compounds stand out while the gold and cyan tiles stay readable.
 */
export function backdropTable(
  viewport: { width: number; height: number },
  fovDegrees: number,
  cameraDistance: number,
  panel: { sideWidth: number; sheetFraction: number; sideMinWidth: number } = PANEL_LAYOUT,
): TableTransform {
  const depth = cameraDistance + CLOUD_CENTER[2] + RECEDE_DEPTH;
  const tanV = Math.tan(THREE.MathUtils.degToRad(fovDegrees / 2));
  const aspect = viewport.width / Math.max(viewport.height, 1);
  const side = viewport.width >= panel.sideMinWidth;
  const halfV = tanV * depth * (side ? 1 : 1 - panel.sheetFraction);
  const halfH = tanV * aspect * depth * (side ? Math.max(0.35, 1 - panel.sideWidth / viewport.width) : 1);
  const scale = Math.min(1, (0.8 * halfH) / TABLE_HALF_WIDTH, (0.8 * halfV) / TABLE_HALF_HEIGHT);
  return { position: [0, CLOUD_CENTER[1], -RECEDE_DEPTH], scale };
}

/** World position of the front face of a tile under a table transform. */
export function tileWorldPosition(cell: Pick<ElementCell, 'col' | 'row'>, transform: TableTransform): Vec3 {
  const [x, y, z] = tilePosition(cell);
  const { position, scale } = transform;
  return [position[0] + scale * x, position[1] + scale * y, position[2] + scale * (z + TILE_DEPTH / 2)];
}
