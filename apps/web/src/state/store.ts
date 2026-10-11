import { create } from 'zustand';

import type { CloudMode, CompoundGroup } from '../data/compoundIndex';
import { SYMBOLS } from '../data/periodic';
import type { SceneRoute } from '../lib/route';

type Navigate = (path: string) => void;

interface AppState {
  /** Current scene, synced from the URL by <RouteSync>. */
  scene: SceneRoute;
  /** Atomic number under the pointer on the table, or null. */
  hoveredZ: number | null;
  /** Atomic numbers picked with Shift/Ctrl-click for the multi-element search. */
  selection: number[];
  /** Tap-to-select mode for touch screens (no Shift or Ctrl there). */
  selectMode: boolean;
  /** Router navigation, injected by <RouteSync> so 3D components can navigate. */
  navigate: Navigate;
  /** Atom index under the pointer in the structure viewer, or null. */
  hoveredAtom: number | null;
  /** Partner element (atomic number) whose ray is under the pointer, or null. */
  hoveredPartner: number | null;
  /** The ray under the pointer belongs to predicted materials (violet), not known compounds. */
  hoveredPredicted: boolean;
  /** Show the layer of predicted materials (GNoME): violet rays and cloud beads. */
  showPredicted: boolean;
  /** Compound in focus while walking along a ray (index in the pair list). */
  walkIndex: number;
  /** Multi-element cloud: "contains at least these" or "only these" elements. */
  cloudMode: CloudMode;
  /** Multi-element cloud: all compounds, or only organic, inorganic or minerals. */
  cloudGroup: CompoundGroup;
  /** Compound under the pointer in the cloud (or its list), and the one in focus. */
  cloudHover: string | null;
  cloudFocus: string | null;
  /** Element scene: the Bohr atom or the 3D simple substance (O₂, bcc iron…). */
  elementView: 'atom' | 'substance';
  /** A page panel (About) covers part of the table scene; the 3D view shifts away. */
  pagePanel: boolean;
  setScene: (scene: SceneRoute) => void;
  setHoveredZ: (z: number | null) => void;
  toggleSelection: (z: number) => void;
  clearSelection: () => void;
  setSelectMode: (on: boolean) => void;
  setPagePanel: (open: boolean) => void;
  setCloudGroup: (group: CompoundGroup) => void;
  setNavigate: (navigate: Navigate) => void;
  setHoveredAtom: (index: number | null) => void;
  setHoveredPartner: (z: number | null, predicted?: boolean) => void;
  setShowPredicted: (show: boolean) => void;
  setWalkIndex: (index: number) => void;
  setCloudMode: (mode: CloudMode) => void;
  setCloudHover: (id: string | null) => void;
  setCloudFocus: (id: string | null) => void;
  setElementView: (view: 'atom' | 'substance') => void;
}

export const useAppStore = create<AppState>((set) => ({
  scene: { kind: 'table' },
  hoveredZ: null,
  selection: [],
  selectMode: false,
  hoveredAtom: null,
  hoveredPartner: null,
  hoveredPredicted: false,
  showPredicted: false,
  walkIndex: 0,
  cloudMode: 'contains',
  cloudGroup: 'all',
  cloudHover: null,
  cloudFocus: null,
  elementView: 'atom',
  pagePanel: false,
  navigate: () => undefined,
  setScene: (scene) =>
    set((state) => ({
      scene,
      hoveredAtom: null,
      hoveredPartner: null,
      // A new ray starts at its first compound.
      walkIndex: scene.kind === 'element' && state.scene.kind === 'element' && sameRay(scene, state.scene) ? state.walkIndex : 0,
      cloudHover: null,
      cloudFocus: scene.kind === 'set' && state.scene.kind === 'set' ? state.cloudFocus : null,
      elementView:
        scene.kind === 'element' && state.scene.kind === 'element' && scene.symbol === state.scene.symbol
          ? state.elementView
          : 'atom',
      // The set scene shows its elements as the selection on the table.
      selection: scene.kind === 'set' ? scene.symbols.map((symbol) => SYMBOLS.indexOf(symbol as (typeof SYMBOLS)[number]) + 1) : state.selection,
    })),
  setHoveredZ: (hoveredZ) => set({ hoveredZ }),
  toggleSelection: (z) =>
    set((state) => ({
      selection: state.selection.includes(z)
        ? state.selection.filter((value) => value !== z)
        : [...state.selection, z],
    })),
  clearSelection: () => set({ selection: [], selectMode: false }),
  setSelectMode: (selectMode) => set({ selectMode }),
  setPagePanel: (pagePanel) => set({ pagePanel }),
  setCloudGroup: (cloudGroup) => set({ cloudGroup, cloudFocus: null, cloudHover: null }),
  setNavigate: (navigate) => set({ navigate }),
  setHoveredAtom: (hoveredAtom) => set({ hoveredAtom }),
  setHoveredPartner: (hoveredPartner, predicted = false) => set({ hoveredPartner, hoveredPredicted: predicted }),
  setShowPredicted: (showPredicted) => set({ showPredicted }),
  setWalkIndex: (walkIndex) => set({ walkIndex }),
  setCloudMode: (cloudMode) => set({ cloudMode, cloudFocus: null }),
  setCloudHover: (cloudHover) => set({ cloudHover }),
  setCloudFocus: (cloudFocus) => set({ cloudFocus }),
  setElementView: (elementView) => set({ elementView }),
}));

function sameRay(a: SceneRoute, b: SceneRoute): boolean {
  return (
    a.kind === 'element' &&
    b.kind === 'element' &&
    a.symbol === b.symbol &&
    a.partner === b.partner &&
    Boolean(a.predicted) === Boolean(b.predicted)
  );
}
