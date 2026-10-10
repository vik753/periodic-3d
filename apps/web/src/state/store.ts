import { create } from 'zustand';

import type { SceneRoute } from '../lib/route';

type Navigate = (path: string) => void;

interface AppState {
  /** Current scene, synced from the URL by <RouteSync>. */
  scene: SceneRoute;
  /** Atomic number under the pointer on the table, or null. */
  hoveredZ: number | null;
  /** Atomic numbers picked with Shift/Ctrl-click for the multi-element search. */
  selection: number[];
  /** Router navigation, injected by <RouteSync> so 3D components can navigate. */
  navigate: Navigate;
  /** Atom index under the pointer in the structure viewer, or null. */
  hoveredAtom: number | null;
  /** Partner element (atomic number) whose ray is under the pointer, or null. */
  hoveredPartner: number | null;
  /** Compound in focus while walking along a ray (index in the pair list). */
  walkIndex: number;
  setScene: (scene: SceneRoute) => void;
  setHoveredZ: (z: number | null) => void;
  toggleSelection: (z: number) => void;
  clearSelection: () => void;
  setNavigate: (navigate: Navigate) => void;
  setHoveredAtom: (index: number | null) => void;
  setHoveredPartner: (z: number | null) => void;
  setWalkIndex: (index: number) => void;
}

export const useAppStore = create<AppState>((set) => ({
  scene: { kind: 'table' },
  hoveredZ: null,
  selection: [],
  hoveredAtom: null,
  hoveredPartner: null,
  walkIndex: 0,
  navigate: () => undefined,
  setScene: (scene) =>
    set((state) => ({
      scene,
      hoveredAtom: null,
      hoveredPartner: null,
      // A new ray starts at its first compound.
      walkIndex: scene.kind === 'element' && state.scene.kind === 'element' && sameRay(scene, state.scene) ? state.walkIndex : 0,
    })),
  setHoveredZ: (hoveredZ) => set({ hoveredZ }),
  toggleSelection: (z) =>
    set((state) => ({
      selection: state.selection.includes(z)
        ? state.selection.filter((value) => value !== z)
        : [...state.selection, z],
    })),
  clearSelection: () => set({ selection: [] }),
  setNavigate: (navigate) => set({ navigate }),
  setHoveredAtom: (hoveredAtom) => set({ hoveredAtom }),
  setHoveredPartner: (hoveredPartner) => set({ hoveredPartner }),
  setWalkIndex: (walkIndex) => set({ walkIndex }),
}));

function sameRay(a: SceneRoute, b: SceneRoute): boolean {
  return a.kind === 'element' && b.kind === 'element' && a.symbol === b.symbol && a.partner === b.partner;
}
