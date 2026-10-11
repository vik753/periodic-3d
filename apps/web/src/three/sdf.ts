/**
 * Signed distance fields for the tile labels.
 *
 * A bitmap label gets blurry when the camera comes close: one texel covers several
 * screen pixels. A distance field stores, for each texel, how far it is from the edge
 * of the letters. Bilinear filtering of distances keeps the edge sharp at any zoom, so
 * the shader can draw crisp letters with one extra texture read (the technique of
 * Valve, SIGGRAPH 2007; the subpixel set-up follows Mapbox TinySDF).
 *
 * The letters are drawn at SDF_SCALE times the atlas resolution, the distance transform
 * runs there (Felzenszwalb & Huttenlocher, linear time), and each atlas texel takes the
 * mean distance of its SDF_SCALE² source pixels. This keeps thin strokes of the small
 * text (the element name) accurate.
 */

/** Source resolution: the letters are drawn this many times larger than the atlas cell. */
export const SDF_SCALE = 2;
/** Distances from −SDF_SPREAD/2 to +SDF_SPREAD/2 atlas texels map to the bytes 0…255. */
export const SDF_SPREAD = 8;

const INF = 1e20;

export interface SdfScratch {
  outer: Float32Array;
  inner: Float32Array;
  f: Float32Array;
  v: Uint16Array;
  z: Float32Array;
}

export function sdfScratch(size: number): SdfScratch {
  return {
    outer: new Float32Array(size * size),
    inner: new Float32Array(size * size),
    f: new Float32Array(size),
    v: new Uint16Array(size),
    z: new Float32Array(size + 1),
  };
}

/** 1D squared distance transform of a lower envelope of parabolas, in place. */
function edt1d(
  grid: Float32Array,
  offset: number,
  stride: number,
  length: number,
  f: Float32Array,
  v: Uint16Array,
  z: Float32Array,
): void {
  v[0] = 0;
  z[0] = -INF;
  z[1] = INF;
  f[0] = grid[offset]!;
  for (let q = 1, k = 0, s = 0; q < length; q += 1) {
    f[q] = grid[offset + q * stride]!;
    const q2 = q * q;
    do {
      const r = v[k]!;
      s = (f[q]! - f[r]! + q2 - r * r) / (q - r) / 2;
    } while (s <= z[k]! && --k > -1);
    k += 1;
    v[k] = q;
    z[k] = s;
    z[k + 1] = INF;
  }
  for (let q = 0, k = 0; q < length; q += 1) {
    while (z[k + 1]! < q) k += 1;
    const r = v[k]!;
    const qr = q - r;
    grid[offset + q * stride] = f[r]! + qr * qr;
  }
}

function edt(grid: Float32Array, size: number, scratch: SdfScratch): void {
  for (let x = 0; x < size; x += 1) edt1d(grid, x, size, size, scratch.f, scratch.v, scratch.z);
  for (let y = 0; y < size; y += 1) edt1d(grid, y * size, 1, size, scratch.f, scratch.v, scratch.z);
}

/**
 * Distance field of one square cell.
 *
 * alpha: coverage bytes of the letters, size × size (row 0 at the top), drawn at
 * SDF_SCALE times the cell resolution. Writes (size / SDF_SCALE)² bytes into out,
 * row by row from the top, starting at outOffset with outStride bytes per row:
 * 128 is the edge, larger values are inside the letters.
 */
export function cellSdf(
  alpha: Uint8Array,
  alphaOffset: number,
  size: number,
  out: Uint8Array,
  outOffset: number,
  outStride: number,
  scratch: SdfScratch,
): void {
  const { outer, inner } = scratch;
  const area = size * size;
  outer.fill(INF, 0, area);
  inner.fill(0, 0, area);
  for (let i = 0; i < area; i += 1) {
    const a = alpha[alphaOffset + i]! / 255;
    if (a === 0) continue;
    if (a === 1) {
      outer[i] = 0;
      inner[i] = INF;
    } else {
      // Subpixel edge position from the antialiased coverage.
      const d = 0.5 - a;
      outer[i] = d > 0 ? d * d : 0;
      inner[i] = d < 0 ? d * d : 0;
    }
  }
  edt(outer, size, scratch);
  edt(inner, size, scratch);

  const cell = size / SDF_SCALE;
  const norm = 1 / (SDF_SCALE * SDF_SCALE * SDF_SCALE); // mean of the block, in atlas texels
  for (let y = 0; y < cell; y += 1) {
    for (let x = 0; x < cell; x += 1) {
      let sum = 0;
      for (let dy = 0; dy < SDF_SCALE; dy += 1) {
        const row = (y * SDF_SCALE + dy) * size + x * SDF_SCALE;
        for (let dx = 0; dx < SDF_SCALE; dx += 1) {
          const i = row + dx;
          // Positive inside the letters.
          sum += Math.sqrt(inner[i]!) - Math.sqrt(outer[i]!);
        }
      }
      const distance = sum * norm;
      const value = Math.round(255 * (0.5 + distance / SDF_SPREAD));
      out[outOffset + y * outStride + x] = value < 0 ? 0 : value > 255 ? 255 : value;
    }
  }
}
