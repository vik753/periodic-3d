/**
 * Response types of the data API (apps/api/src/p3d_api/schemas.py).
 * The live API and the static export return the same JSON.
 */

import type { StructureData } from './structure';

export type NameLanguage = 'en' | 'ru' | 'uk' | 'la';
export type Names = Partial<Record<NameLanguage, string>>;
export type StructureKind = StructureData['kind'];

export interface Meta {
  version: string;
  schemaVersion: number;
  apiVersion: number;
  created: string;
  counts: Record<string, number>;
  licenses: Record<string, string>;
  /** The layer of predicted materials (GNoME, ADR 0007); absent when the site has none. */
  gnome?: GnomeInfo | null;
}

export interface GnomeInfo {
  /** Layer name, e.g. "gnome-2026.10.11-r2"; static files live under data/<version>/materials/. */
  version: string;
  created: string;
  counts: Record<string, number>;
  license: string;
  licenseUrl: string | null;
  citation: string;
  sourceUrl: string | null;
}

export interface ElementSummary {
  z: number;
  symbol: string;
  names: Names;
  mass: number | null;
  groupBlock: string | null;
  standardState: string | null;
  cpk: string | null;
  compoundCount: number;
  hasSubstance: boolean;
}

export interface ElementList {
  version: string;
  elements: ElementSummary[];
}

export interface StructureInfo {
  kind: StructureKind;
  source: string;
  ref: string | null;
  atoms: number;
  license: string;
}

export interface Substance {
  names: Names;
  info: StructureInfo;
  structure: StructureData;
}

export interface Partner {
  z: number;
  symbol: string;
  count: number;
}

export interface CompoundSummary {
  id: string;
  formula: string;
  names: Names;
  elements: string[];
  fame: number;
  kind: StructureKind | null;
}

/** A photo from Wikimedia Commons with its attribution. */
export interface Photo {
  /** Thumbnail, 640 px wide. */
  url: string;
  /** File page on Commons: author, license, full size. */
  page: string;
  license: string;
  author?: string | null;
  licenseUrl?: string | null;
}

export interface SimilarElement {
  z: number;
  symbol: string;
  /** Cosine similarity of the element vectors, −1…1. */
  score: number;
}

export interface ElementDetail {
  version: string;
  z: number;
  symbol: string;
  names: Names;
  substanceNames: Names;
  wikidata: string | null;
  mass: number | null;
  configuration: string | null;
  electronegativity: number | null;
  atomicRadius: number | null;
  ionizationEnergy: number | null;
  electronAffinity: number | null;
  oxidationStates: string | null;
  standardState: string | null;
  meltingPoint: number | null;
  boilingPoint: number | null;
  density: number | null;
  groupBlock: string | null;
  yearDiscovered: string | null;
  cpk: string | null;
  compoundCount: number;
  substance: Substance | null;
  partners: Partner[];
  topCompounds: CompoundSummary[];
  /** Elements with similar partners (vector model); empty for older datasets. */
  similar?: SimilarElement[];
  photo?: Photo | null;
}

export interface ClassRef {
  qid: string;
  names: Names;
}

export interface Source {
  role: 'identity' | 'description' | 'properties' | 'structure' | 'photo';
  name: string;
  url: string | null;
  license: string;
}

export interface CompoundDetail {
  version: string;
  id: string;
  formula: string;
  hill: string;
  elements: string[];
  composition: Record<string, number>;
  names: Names;
  descriptions: Names;
  fame: number;
  pubchemCid: number | null;
  mass: number | null;
  charge: number;
  smiles: string | null;
  inchikey: string | null;
  iupac: string | null;
  classes: ClassRef[];
  structureInfo: StructureInfo | null;
  structure: StructureData | null;
  sources: Source[];
  /** Compounds with similar elements in similar proportions (vector model). */
  similar?: CompoundSummary[];
  photo?: Photo | null;
}

export interface ElementRef {
  z: number;
  symbol: string;
}

export interface PairDetail {
  version: string;
  a: ElementRef;
  b: ElementRef;
  count: number;
  compounds: CompoundSummary[];
}

/** rows: [id, formula, atomic numbers, fame, kind, names, flags]; flags bit 1 = mineral (older datasets: no flags). */
export type CompoundIndexRow = [string, string, number[], number, StructureKind | null, Names, number?];

export interface CompoundIndex {
  version: string;
  fields: string[];
  rows: CompoundIndexRow[];
}

/** Compact unit cell; data/crystal.ts turns it into a displayable structure. */
export interface MaterialStructure {
  /** a, b, c in ångström; alpha, beta, gamma in degrees. */
  cell: number[];
  /** base64 of 7-byte records: Z, then x, y, z ×10⁴ (uint16, little-endian). */
  sites: string;
}

/** A crystal predicted by GNoME: computed, not confirmed by experiment. Energies in eV/atom. */
export interface Material {
  id: string;
  formula: string;
  composition: Record<string, number>;
  elements: string[];
  nsites: number;
  spaceGroup: string | null;
  spaceGroupNumber: number | null;
  pointGroup: string | null;
  crystalSystem: string | null;
  volume: number | null;
  density: number | null;
  formationEnergy: number | null;
  /** Distance to the convex hull of competing phases; ≤ 0 means stable in the calculation. */
  decompositionEnergy: number | null;
  r2scanDecompositionEnergy: number | null;
  bandgap: number | null;
  dimensionality: string | null;
  structure: MaterialStructure;
}

export interface MaterialShard {
  version: string;
  prefix: string;
  materials: Material[];
}

/** rows: [id, formula, decompositionEnergy]: fewer elements first, then the most stable. */
export type MaterialListRow = [string, string, number | null];

export interface MaterialList {
  version: string;
  symbol: string;
  total: number;
  fields: string[];
  rows: MaterialListRow[];
}

export interface MaterialPairs {
  version: string;
  /** [Z, count] */
  elements: Array<[number, number]>;
  /** [Za, Zb, count], Za < Zb */
  pairs: Array<[number, number, number]>;
}

/** Picks a name in the interface language, then English, then any. */
export function pickName(names: Names | undefined, language: string, fallback = ''): string {
  if (!names) return fallback;
  return names[language as NameLanguage] ?? names.en ?? Object.values(names)[0] ?? fallback;
}
