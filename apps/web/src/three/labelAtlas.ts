import * as THREE from 'three';

import type { LabelSdfRequest, LabelSdfResponse } from './labelSdf.worker';
import { SDF_SCALE, SDF_SPREAD } from './sdf';

/** The atlas is a 16 × 16 grid of 128-px cells: one cell per element. */
export const ATLAS_GRID = 16;
const CELL = 128;
const ATLAS_SIZE = ATLAS_GRID * CELL;
/** Label colours: the symbol, and the softer atomic number and name. */
const INK = '#F4F7FF';
const SOFT_INK = 'rgb(233, 238, 248)';

export const DISPLAY_FONT = '"Unbounded Variable", "Segoe UI", system-ui, sans-serif';
export const TEXT_FONT = '"Golos Text Variable", "Segoe UI", system-ui, sans-serif';

export interface AtlasEntry {
  z: number;
  symbol: string;
  name?: string;
}

/** Cell coordinates (column, row from the top) of element index i. */
export function atlasCell(index: number): [number, number] {
  return [index % ATLAS_GRID, Math.floor(index / ATLAS_GRID)];
}

export function createLabelAtlas(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = ATLAS_GRID * CELL;
  canvas.height = ATLAS_GRID * CELL;
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.generateMipmaps = true;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.anisotropy = 8;
  return texture;
}

function fitText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string {
  if (ctx.measureText(text).width <= maxWidth) return text;
  let cut = text;
  while (cut.length > 1 && ctx.measureText(`${cut}…`).width > maxWidth) cut = cut.slice(0, -1);
  return `${cut}…`;
}

/**
 * Draws one cell: atomic number, symbol and (when known) the localized name.
 * solid draws everything opaque: the distance field needs the shapes, not the tones.
 */
function drawCell(ctx: CanvasRenderingContext2D, entry: AtlasEntry, x: number, y: number, solid = false): void {
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  ctx.font = `500 21px ${TEXT_FONT}`;
  ctx.fillStyle = solid ? '#fff' : 'rgba(233, 238, 248, 0.74)';
  ctx.fillText(String(entry.z), x + 13, y + 11);

  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = `600 46px ${DISPLAY_FONT}`;
  ctx.fillStyle = solid ? '#fff' : INK;
  ctx.fillText(entry.symbol, x + CELL / 2, y + CELL / 2 + (entry.name ? 0 : 6));

  if (entry.name) {
    ctx.font = `500 16px ${TEXT_FONT}`;
    ctx.fillStyle = solid ? '#fff' : 'rgba(233, 238, 248, 0.8)';
    ctx.fillText(fitText(ctx, entry.name, CELL - 14), x + CELL / 2, y + CELL - 19);
  }
}

/** Draws every cell of the bitmap atlas: it serves the table seen from afar. */
export function drawLabelAtlas(texture: THREE.CanvasTexture, entries: readonly AtlasEntry[]): void {
  const canvas = texture.image as HTMLCanvasElement;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  entries.forEach((entry, index) => {
    const [col, row] = atlasCell(index);
    drawCell(ctx, entry, col * CELL, row * CELL);
  });
  texture.needsUpdate = true;
}

/** A 1 × 1 stand-in until the distance field is ready. */
export function emptyLabelSdf(): THREE.DataTexture {
  const texture = new THREE.DataTexture(new Uint8Array(1), 1, 1, THREE.RedFormat, THREE.UnsignedByteType);
  texture.needsUpdate = true;
  return texture;
}

const pause = () => new Promise<void>((resolve) => window.setTimeout(resolve, 0));

/**
 * The distance-field atlas for close-ups (see sdf.ts). The letters are drawn here, a few
 * cells per task so no frame waits; the distance transform runs in a worker.
 * Resolves to null when the browser cannot do it or the work was cancelled: the
 * bitmap atlas then serves every zoom level.
 */
export async function buildLabelSdf(
  entries: readonly AtlasEntry[],
  cancelled: () => boolean,
): Promise<THREE.DataTexture | null> {
  if (typeof Worker === 'undefined') return null;
  const source = CELL * SDF_SCALE;
  const canvas = document.createElement('canvas');
  canvas.width = source;
  canvas.height = source;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) return null;
  const area = source * source;
  const alpha = new Uint8Array(entries.length * area);
  for (let index = 0; index < entries.length; index += 1) {
    if (index % 12 === 0) {
      await pause();
      if (cancelled()) return null;
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, source, source);
    ctx.setTransform(SDF_SCALE, 0, 0, SDF_SCALE, 0, 0);
    drawCell(ctx, entries[index]!, 0, 0, true);
    const pixels = ctx.getImageData(0, 0, source, source).data;
    const base = index * area;
    for (let i = 0; i < area; i += 1) alpha[base + i] = pixels[i * 4 + 3]!;
  }

  const worker = new Worker(new URL('./labelSdf.worker.ts', import.meta.url), { type: 'module' });
  try {
    const response = await new Promise<LabelSdfResponse>((resolve, reject) => {
      worker.onmessage = (event: MessageEvent<LabelSdfResponse>) => resolve(event.data);
      worker.onerror = (event) => reject(new Error(event.message));
      const request: LabelSdfRequest = { alpha, count: entries.length, source, grid: ATLAS_GRID };
      worker.postMessage(request, [alpha.buffer]);
    });
    if (cancelled()) return null;
    const texture = new THREE.DataTexture(response.data, response.size, response.size, THREE.RedFormat, THREE.UnsignedByteType);
    texture.magFilter = THREE.LinearFilter;
    texture.minFilter = THREE.LinearFilter;
    texture.generateMipmaps = false;
    texture.needsUpdate = true;
    return texture;
  } finally {
    worker.terminate();
  }
}

/**
 * Instanced label quads: each instance samples its own atlas cell and has its own alpha
 * (aAlpha). From afar the mipmapped bitmap draws the letters; close up, when one atlas
 * texel covers more than one screen pixel, the distance field takes over and keeps the
 * edges sharp. The switch follows the screen-space size of a texel, so it is smooth.
 */
export function createLabelMaterial(atlas: THREE.Texture, sdf: THREE.Texture): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: {
      uAtlas: { value: atlas },
      uSdf: { value: sdf },
      uSdfReady: { value: 0 },
      uGrid: { value: ATLAS_GRID },
      uOpacity: { value: 1 },
      uInk: { value: new THREE.Color(INK) },
      uSoftInk: { value: new THREE.Color(SOFT_INK) },
    },
    vertexShader: /* glsl */ `
      attribute vec2 aCell;
      attribute float aAlpha;
      uniform float uGrid;
      varying vec2 vUv;
      varying vec2 vLocal;
      varying float vAlpha;
      void main() {
        // Canvas row 0 is at the top; texture v = 1 is at the top (flipY).
        vec2 cell = vec2(aCell.x, uGrid - 1.0 - aCell.y);
        vUv = (uv + cell) / uGrid;
        vLocal = uv;
        vAlpha = aAlpha;
        gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uAtlas;
      uniform sampler2D uSdf;
      uniform float uSdfReady;
      uniform float uOpacity;
      uniform vec3 uInk;
      uniform vec3 uSoftInk;
      varying vec2 vUv;
      varying vec2 vLocal;
      varying float vAlpha;
      void main() {
        vec4 texel = texture2D(uAtlas, vUv);
        // Atlas texels per screen pixel: below 1 the bitmap is magnified and gets blurry.
        vec2 texels = vUv * ${ATLAS_SIZE.toFixed(1)};
        float footprint = max(length(dFdx(texels)), length(dFdy(texels)));
        // Signed distance to the letter edge in atlas texels, positive inside.
        float signedTexels = (texture2D(uSdf, vUv).r - 0.5) * ${SDF_SPREAD.toFixed(1)};
        float coverage = clamp(signedTexels / max(footprint, 0.001) + 0.5, 0.0, 1.0);
        // The number (top band) and the name (bottom band) are softer than the symbol.
        float top = 1.0 - vLocal.y;
        float tone = top < 0.3 ? 0.74 : (top > 0.76 ? 0.8 : 1.0);
        vec3 ink = tone < 1.0 ? uSoftInk : uInk;
        float sharp = uSdfReady * (1.0 - smoothstep(0.6, 1.0, footprint));
        float alpha = mix(texel.a, coverage * tone, sharp) * uOpacity * vAlpha;
        if (alpha < 0.01) discard;
        gl_FragColor = vec4(mix(texel.rgb, ink, sharp), alpha);
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    toneMapped: false,
  });
}
