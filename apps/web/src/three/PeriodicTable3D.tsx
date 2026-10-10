import type { ThreeEvent } from '@react-three/fiber';
import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

import type { Category } from '../data/periodic';
import { ELEMENTS } from '../data/periodic';
import { useAppStore } from '../state/store';
import type { AtlasEntry } from './labelAtlas';
import { atlasCell, createLabelAtlas, createLabelMaterial, drawLabelAtlas, DISPLAY_FONT, TEXT_FONT } from './labelAtlas';
import { TILE, TILE_DEPTH, tileMatrix, tilePosition } from './layout';
import { damp } from './useKeepRendering';

const COUNT = ELEMENTS.length;

/** Quiet category tints; the saturated colour of the app belongs to the bond rays. */
export const CATEGORY_COLORS: Readonly<Record<Category, string>> = {
  'alkali-metal': '#E0915A',
  'alkaline-earth-metal': '#D9B45A',
  'transition-metal': '#5E8BD6',
  'post-transition-metal': '#58A7A0',
  metalloid: '#62B57A',
  'reactive-nonmetal': '#4FC1D9',
  'noble-gas': '#9A7BEA',
  lanthanide: '#C77DBA',
  actinide: '#A86CC9',
  unknown: '#6B7489',
};

const GLASS = new THREE.Color('#121a33');
const GOLD = new THREE.Color('#FFC857');

function tileColor(category: Category, mode: 'rest' | 'hover' | 'selected', out: THREE.Color): THREE.Color {
  const tint = new THREE.Color(CATEGORY_COLORS[category]);
  if (mode === 'selected') return out.copy(GLASS).lerp(GOLD, 0.62);
  return out.copy(GLASS).lerp(tint, mode === 'hover' ? 0.78 : 0.42);
}

const noRaycast = () => null;

interface PeriodicTable3DProps {
  /** Localized element names by atomic number; drawn under the symbols when available. */
  names?: ReadonlyMap<number, string>;
}

export function PeriodicTable3D({ names }: PeriodicTable3DProps) {
  const tilesRef = useRef<THREE.InstancedMesh>(null);
  const labelsRef = useRef<THREE.InstancedMesh>(null);
  const invalidate = useThree((state) => state.invalidate);

  const scene = useAppStore((state) => state.scene);
  const hoveredZ = useAppStore((state) => state.hoveredZ);
  const selection = useAppStore((state) => state.selection);
  const setHoveredZ = useAppStore((state) => state.setHoveredZ);
  const toggleSelection = useAppStore((state) => state.toggleSelection);

  const interactive = scene.kind === 'table';
  const activeZ = scene.kind === 'element' ? (ELEMENTS.find((e) => e.symbol === scene.symbol)?.z ?? null) : null;

  const positions = useMemo(() => ELEMENTS.map((cell) => tilePosition(cell)), []);

  const tileGeometry = useMemo(() => new RoundedBoxGeometry(TILE, TILE, TILE_DEPTH, 3, 0.075), []);
  const tileMaterial = useMemo(
    () => new THREE.MeshStandardMaterial({ roughness: 0.38, metalness: 0.12, transparent: true }),
    [],
  );

  const labelGeometry = useMemo(() => {
    const geometry = new THREE.PlaneGeometry(TILE * 0.96, TILE * 0.96);
    const cells = new Float32Array(COUNT * 2);
    ELEMENTS.forEach((_, index) => {
      const [col, row] = atlasCell(index);
      cells[index * 2] = col;
      cells[index * 2 + 1] = row;
    });
    geometry.setAttribute('aCell', new THREE.InstancedBufferAttribute(cells, 2));
    return geometry;
  }, []);
  const atlas = useMemo(() => createLabelAtlas(), []);
  const labelMaterial = useMemo(() => createLabelMaterial(atlas), [atlas]);

  // Animated per-tile state: current scale and lift towards the viewer.
  const animation = useRef({
    scale: new Float32Array(COUNT).fill(1),
    lift: new Float32Array(COUNT).fill(0),
    opacity: 1,
  });

  // Draw the label atlas once the fonts are ready, and again when names arrive.
  useEffect(() => {
    let cancelled = false;
    const entries: AtlasEntry[] = ELEMENTS.map((cell) => ({ z: cell.z, symbol: cell.symbol, name: names?.get(cell.z) }));
    const fontsReady = Promise.all([
      document.fonts.load(`600 46px ${DISPLAY_FONT}`),
      document.fonts.load(`500 21px ${TEXT_FONT}`),
    ]).catch(() => undefined);
    void fontsReady.then(() => {
      if (cancelled) return;
      drawLabelAtlas(atlas, entries);
      invalidate();
    });
    return () => {
      cancelled = true;
    };
  }, [atlas, names, invalidate]);

  // Initial matrices and colours.
  useLayoutEffect(() => {
    const tiles = tilesRef.current;
    const labels = labelsRef.current;
    if (!tiles || !labels) return;
    const matrix = new THREE.Matrix4();
    const color = new THREE.Color();
    ELEMENTS.forEach((cell, index) => {
      const position = positions[index]!;
      tiles.setMatrixAt(index, tileMatrix(position, matrix));
      labels.setMatrixAt(index, tileMatrix(position, matrix, { zOffset: TILE_DEPTH / 2 + 0.004 }));
      tiles.setColorAt(index, tileColor(cell.category, 'rest', color));
    });
    tiles.instanceMatrix.needsUpdate = true;
    labels.instanceMatrix.needsUpdate = true;
    if (tiles.instanceColor) tiles.instanceColor.needsUpdate = true;
    tiles.computeBoundingSphere();
    invalidate();
  }, [positions, invalidate]);

  // Colours react to hover and selection.
  useEffect(() => {
    const tiles = tilesRef.current;
    if (!tiles) return;
    const color = new THREE.Color();
    ELEMENTS.forEach((cell, index) => {
      const mode = selection.includes(cell.z) ? 'selected' : hoveredZ === cell.z ? 'hover' : 'rest';
      tiles.setColorAt(index, tileColor(cell.category, mode, color));
    });
    if (tiles.instanceColor) tiles.instanceColor.needsUpdate = true;
    invalidate();
  }, [hoveredZ, selection, invalidate]);

  useEffect(() => {
    document.body.style.cursor = interactive && hoveredZ != null ? 'pointer' : 'auto';
  }, [interactive, hoveredZ]);

  useEffect(() => invalidate(), [scene, invalidate]);

  useFrame((_, delta) => {
    const tiles = tilesRef.current;
    const labels = labelsRef.current;
    if (!tiles || !labels) return;
    const state = animation.current;
    const dt = Math.min(delta, 0.05);
    let moving = false;
    const matrix = new THREE.Matrix4();

    const targetOpacity = interactive ? 1 : 0.07;
    const nextOpacity = damp(state.opacity, targetOpacity, 6, dt);
    if (Math.abs(nextOpacity - state.opacity) > 0.002) moving = true;
    state.opacity = Math.abs(nextOpacity - targetOpacity) < 0.002 ? targetOpacity : nextOpacity;
    tileMaterial.opacity = state.opacity;
    tileMaterial.depthWrite = state.opacity > 0.5;
    labelMaterial.uniforms.uOpacity!.value = state.opacity;

    for (let index = 0; index < COUNT; index += 1) {
      const z = index + 1;
      const isHover = interactive && hoveredZ === z;
      const isSelected = selection.includes(z);
      const targetScale = activeZ === z ? 0.001 : isHover ? 1.1 : isSelected ? 1.05 : 1;
      const targetLift = isHover ? 0.32 : isSelected ? 0.18 : 0;
      const scale = damp(state.scale[index]!, targetScale, 14, dt);
      const lift = damp(state.lift[index]!, targetLift, 14, dt);
      if (Math.abs(scale - state.scale[index]!) > 1e-4 || Math.abs(lift - state.lift[index]!) > 1e-4) {
        moving = true;
        state.scale[index] = scale;
        state.lift[index] = lift;
        const position = positions[index]!;
        tiles.setMatrixAt(index, tileMatrix(position, matrix, { scale, lift }));
        labels.setMatrixAt(index, tileMatrix(position, matrix, { scale, lift, zOffset: (TILE_DEPTH / 2 + 0.004) * scale }));
      }
    }
    if (moving) {
      tiles.instanceMatrix.needsUpdate = true;
      labels.instanceMatrix.needsUpdate = true;
      invalidate();
    }
  });

  const handleMove = (event: ThreeEvent<PointerEvent>) => {
    if (!interactive || event.instanceId == null) return;
    event.stopPropagation();
    const z = event.instanceId + 1;
    if (z !== hoveredZ) setHoveredZ(z);
  };

  const handleOut = () => {
    if (hoveredZ != null) setHoveredZ(null);
  };

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    if (!interactive || event.instanceId == null || event.delta > 6) return;
    event.stopPropagation();
    const cell = ELEMENTS[event.instanceId];
    if (!cell) return;
    if (event.shiftKey || event.ctrlKey || event.metaKey) {
      toggleSelection(cell.z);
      return;
    }
    setHoveredZ(null);
    useAppStore.getState().navigate(`/e/${cell.symbol}`);
  };

  return (
    <group>
      <instancedMesh
        ref={tilesRef}
        args={[tileGeometry, tileMaterial, COUNT]}
        raycast={interactive ? THREE.InstancedMesh.prototype.raycast : noRaycast}
        onPointerMove={handleMove}
        onPointerOut={handleOut}
        onClick={handleClick}
      />
      <instancedMesh ref={labelsRef} args={[labelGeometry, labelMaterial, COUNT]} raycast={noRaycast} renderOrder={1} />
    </group>
  );
}
