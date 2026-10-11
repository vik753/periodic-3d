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

/** Picks a name in the interface language, then English, then any. */
export function pickName(names: Names | undefined, language: string, fallback = ''): string {
  if (!names) return fallback;
  return names[language as NameLanguage] ?? names.en ?? Object.values(names)[0] ?? fallback;
}
