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
  setScene: (scene: SceneRoute) => void;
  setHoveredZ: (z: number | null) => void;
  toggleSelection: (z: number) => void;
  clearSelection: () => void;
  setNavigate: (navigate: Navigate) => void;
  setHoveredAtom: (index: number | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  scene: { kind: 'table' },
  hoveredZ: null,
  selection: [],
  hoveredAtom: null,
  navigate: () => undefined,
  setScene: (scene) => set({ scene, hoveredAtom: null }),
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
}));
