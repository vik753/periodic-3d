import * as THREE from 'three';

/** The atlas is a 16 × 16 grid of 128-px cells: one cell per element. */
export const ATLAS_GRID = 16;
const CELL = 128;

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

/** Draws atomic number, symbol and (when known) the localized name into each cell. */
export function drawLabelAtlas(texture: THREE.CanvasTexture, entries: readonly AtlasEntry[]): void {
  const canvas = texture.image as HTMLCanvasElement;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  entries.forEach((entry, index) => {
    const [col, row] = atlasCell(index);
    const x = col * CELL;
    const y = row * CELL;

    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.font = `500 21px ${TEXT_FONT}`;
    ctx.fillStyle = 'rgba(233, 238, 248, 0.74)';
    ctx.fillText(String(entry.z), x + 13, y + 11);

    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = `600 46px ${DISPLAY_FONT}`;
    ctx.fillStyle = '#F4F7FF';
    ctx.fillText(entry.symbol, x + CELL / 2, y + CELL / 2 + (entry.name ? 0 : 6));

    if (entry.name) {
      ctx.font = `500 16px ${TEXT_FONT}`;
      ctx.fillStyle = 'rgba(233, 238, 248, 0.8)';
      ctx.fillText(fitText(ctx, entry.name, CELL - 14), x + CELL / 2, y + CELL - 19);
    }
  });
  texture.needsUpdate = true;
}

/** Instanced label quads: each instance samples its own atlas cell and has its own alpha (aAlpha). */
export function createLabelMaterial(atlas: THREE.Texture): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: {
      uAtlas: { value: atlas },
      uGrid: { value: ATLAS_GRID },
      uOpacity: { value: 1 },
    },
    vertexShader: /* glsl */ `
      attribute vec2 aCell;
      attribute float aAlpha;
      uniform float uGrid;
      varying vec2 vUv;
      varying float vAlpha;
      void main() {
        // Canvas row 0 is at the top; texture v = 1 is at the top (flipY).
        vec2 cell = vec2(aCell.x, uGrid - 1.0 - aCell.y);
        vUv = (uv + cell) / uGrid;
        vAlpha = aAlpha;
        gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uAtlas;
      uniform float uOpacity;
      varying vec2 vUv;
      varying float vAlpha;
      void main() {
        vec4 texel = texture2D(uAtlas, vUv);
        float alpha = texel.a * uOpacity * vAlpha;
        if (alpha < 0.01) discard;
        gl_FragColor = vec4(texel.rgb, alpha);
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    toneMapped: false,
  });
}
