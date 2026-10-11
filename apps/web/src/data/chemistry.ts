/**
 * Rendering conventions for atoms: CPK/Jmol colours and covalent radii.
 * The dataset will provide colours for every element; this table covers the
 * common ones so demo structures render before the dataset loads.
 */

/** Jmol CPK colours (sRGB hex). */
const CPK: Readonly<Record<string, string>> = {
  H: '#FFFFFF', He: '#D9FFFF', Li: '#CC80FF', Be: '#C2FF00', B: '#FFB5B5', C: '#909090',
  N: '#3050F8', O: '#FF0D0D', F: '#90E050', Ne: '#B3E3F5', Na: '#AB5CF2', Mg: '#8AFF00',
  Al: '#BFA6A6', Si: '#F0C8A0', P: '#FF8000', S: '#FFFF30', Cl: '#1FF01F', Ar: '#80D1E3',
  K: '#8F40D4', Ca: '#3DFF00', Sc: '#E6E6E6', Ti: '#BFC2C7', V: '#A6A6AB', Cr: '#8A99C7',
  Mn: '#9C7AC7', Fe: '#E06633', Co: '#F090A0', Ni: '#50D050', Cu: '#C88033', Zn: '#7D80B0',
  Ga: '#C28F8F', Ge: '#668F8F', As: '#BD80E3', Se: '#FFA100', Br: '#A62929', Kr: '#5CB8D1',
  Rb: '#702EB0', Sr: '#00FF00', Y: '#94FFFF', Zr: '#94E0E0', Nb: '#73C2C9', Mo: '#54B5B5',
  Tc: '#3B9E9E', Ru: '#248F8F', Rh: '#0A7D8C', Pd: '#006985', Ag: '#C0C0C0', Cd: '#FFD98F',
  In: '#A67573', Sn: '#668080', Sb: '#9E63B5', Te: '#D47A00', I: '#940094', Xe: '#429EB0',
  Cs: '#57178F', Ba: '#00C900', La: '#70D4FF', Ce: '#FFFFC7', W: '#2194D6', Pt: '#D0D0E0',
  Au: '#FFD123', Hg: '#B8B8D0', Tl: '#A6544D', Pb: '#575961', Bi: '#9E4FB5', U: '#008FFF',
};

/** Covalent radii in ångström (Cordero et al. 2008). */
const COVALENT_RADIUS: Readonly<Record<string, number>> = {
  H: 0.31, He: 0.28, Li: 1.28, Be: 0.96, B: 0.84, C: 0.76, N: 0.71, O: 0.66, F: 0.57, Ne: 0.58,
  Na: 1.66, Mg: 1.41, Al: 1.21, Si: 1.11, P: 1.07, S: 1.05, Cl: 1.02, Ar: 1.06, K: 2.03, Ca: 1.76,
  Sc: 1.7, Ti: 1.6, V: 1.53, Cr: 1.39, Mn: 1.39, Fe: 1.32, Co: 1.26, Ni: 1.24, Cu: 1.32, Zn: 1.22,
  Ga: 1.22, Ge: 1.2, As: 1.19, Se: 1.2, Br: 1.2, Kr: 1.16, Rb: 2.2, Sr: 1.95, Y: 1.9, Zr: 1.75,
  Nb: 1.64, Mo: 1.54, Ru: 1.46, Rh: 1.42, Pd: 1.39, Ag: 1.45, Cd: 1.44, In: 1.42, Sn: 1.39,
  Sb: 1.39, Te: 1.38, I: 1.39, Xe: 1.4, Cs: 2.44, Ba: 2.15, La: 2.07, W: 1.62, Pt: 1.36, Au: 1.36,
  Hg: 1.32, Pb: 1.46, Bi: 1.48, U: 1.96,
};

const FALLBACK_COLOR = '#C8D0E0';
const FALLBACK_RADIUS = 1.5;

/**
 * Deliberate departures from Jmol. Oxygen sits next to the red rays in most scenes;
 * the pure #FF0D0D merged with them, a softer coral keeps it red but distinct.
 */
const STYLE: Readonly<Record<string, string>> = { O: '#F0564A' };

/** CPK colours of all 118 elements from the dataset (fills gaps in the table above). */
let datasetColors: Record<string, string> = {};

export function registerElementColors(elements: ReadonlyArray<{ symbol: string; cpk: string | null }>): void {
  const colors: Record<string, string> = {};
  for (const element of elements) {
    if (element.cpk) colors[element.symbol] = element.cpk;
  }
  datasetColors = colors;
}

export function atomColor(symbol: string, override?: string | null): string {
  return override ?? STYLE[symbol] ?? CPK[symbol] ?? datasetColors[symbol] ?? FALLBACK_COLOR;
}

export function covalentRadius(symbol: string): number {
  return COVALENT_RADIUS[symbol] ?? FALLBACK_RADIUS;
}
