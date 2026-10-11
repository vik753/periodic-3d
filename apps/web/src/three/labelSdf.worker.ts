/**
 * Builds the distance-field atlas of the tile labels off the main thread (about 0.5 s of
 * work on a laptop, more on a phone): the table keeps animating while it runs.
 */
import { cellSdf, SDF_SCALE, sdfScratch } from './sdf';

export interface LabelSdfRequest {
  /** Coverage bytes of each cell, drawn SDF_SCALE times larger, one cell after another. */
  alpha: Uint8Array;
  count: number;
  /** Side of one source cell in pixels. */
  source: number;
  /** Cells per atlas row. */
  grid: number;
}

export interface LabelSdfResponse {
  /** Atlas bytes, bottom row first (texture order: v = 1 is the top, like the canvas atlas). */
  data: Uint8Array;
  size: number;
}

const scope = self as unknown as {
  onmessage: ((event: MessageEvent<LabelSdfRequest>) => void) | null;
  postMessage(message: LabelSdfResponse, transfer: Transferable[]): void;
};

scope.onmessage = (event) => {
  const { alpha, count, source, grid } = event.data;
  const cell = source / SDF_SCALE;
  const size = grid * cell;
  const data = new Uint8Array(size * size);
  const scratch = sdfScratch(source);
  for (let index = 0; index < count; index += 1) {
    const col = index % grid;
    const row = Math.floor(index / grid);
    // Canvas row r of the atlas is texture row size − 1 − r: write each cell upwards.
    const top = (size - 1 - row * cell) * size + col * cell;
    cellSdf(alpha, index * source * source, source, data, top, -size, scratch);
  }
  scope.postMessage({ data, size }, [data.buffer]);
};
