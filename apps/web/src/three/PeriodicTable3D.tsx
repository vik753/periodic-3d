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
import type { TableTransform } from './layout';
import { TABLE_AT_REST, TILE, TILE_DEPTH, tileMatrix, tilePosition } from './layout';
import { RAY_COLOR } from './Rays';
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
const RAY = new THREE.Color(RAY_COLOR);
const CYAN = new THREE.Color('#62D2FF');

type TileMode = 'rest' | 'hover' | 'selected' | 'partner' | 'partner-hover' | 'extra' | 'extra-strong' | 'dim';

function tileColor(category: Category, mode: TileMode, out: THREE.Color): THREE.Color {
  const tint = new THREE.Color(CATEGORY_COLORS[category]);
  switch (mode) {
    case 'selected':
      return out.copy(GLASS).lerp(GOLD, 0.62);
    case 'hover':
      return out.copy(GLASS).lerp(tint, 0.72);
    case 'partner':
      return out.copy(GLASS).lerp(tint, 0.55);
    case 'partner-hover':
      return out.copy(GLASS).lerp(RAY, 0.7);
    case 'extra':
      return out.copy(GLASS).lerp(CYAN, 0.38);
    case 'extra-strong':
      return out.copy(GLASS).lerp(CYAN, 0.78);
    case 'dim':
      return out.copy(GLASS).lerp(tint, 0.08).multiplyScalar(0.7);
    default:
      return out.copy(GLASS).lerp(tint, 0.36);
  }
}

const noRaycast = () => null;

interface PeriodicTable3DProps {
  /** Localized element names by atomic number; drawn under the symbols when available. */
  names?: ReadonlyMap<number, string>;
  /** Element scene: where the receded table goes. */
  transform?: TableTransform;
  /** Element scene: partners of the focused element (atomic numbers); their tiles light up. */
  partners?: ReadonlySet<number>;
  /** Set scene: other elements in the cloud's compounds (cyan); `strong` for the hovered compound. */
  extras?: ReadonlySet<number>;
  strongExtras?: ReadonlySet<number>;
}

const NONE: ReadonlySet<number> = new Set();

export function PeriodicTable3D({
  names,
  transform = TABLE_AT_REST,
  partners = NONE,
  extras = NONE,
  strongExtras = NONE,
}: PeriodicTable3DProps) {
  const groupRef = useRef<THREE.Group>(null);
  const tilesRef = useRef<THREE.InstancedMesh>(null);
  const labelsRef = useRef<THREE.InstancedMesh>(null);
  const invalidate = useThree((state) => state.invalidate);

  const scene = useAppStore((state) => state.scene);
  const hoveredZ = useAppStore((state) => state.hoveredZ);
  const selection = useAppStore((state) => state.selection);
  const setHoveredZ = useAppStore((state) => state.setHoveredZ);
  const toggleSelection = useAppStore((state) => state.toggleSelection);
  const hoveredPartner = useAppStore((state) => state.hoveredPartner);
  const setHoveredPartner = useAppStore((state) => state.setHoveredPartner);

  const interactive = scene.kind === 'table';
  const elementScene = scene.kind === 'element';
  const setScene = scene.kind === 'set';
  const pickable = interactive || elementScene || setScene;
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
    geometry.setAttribute('aAlpha', new THREE.InstancedBufferAttribute(new Float32Array(COUNT).fill(1), 1));
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

  // Colours react to hover and selection; in the element scene partners light up.
  useEffect(() => {
    const tiles = tilesRef.current;
    if (!tiles) return;
    const color = new THREE.Color();
    const alpha = labelGeometry.getAttribute('aAlpha') as THREE.InstancedBufferAttribute;
    ELEMENTS.forEach((cell, index) => {
      let mode: TileMode;
      if (elementScene) {
        const isPartner = partners.has(cell.z);
        mode = isPartner ? (hoveredPartner === cell.z ? 'partner-hover' : 'partner') : hoveredZ === cell.z ? 'hover' : 'dim';
        alpha.setX(index, isPartner || hoveredZ === cell.z ? 1 : 0.22);
      } else if (setScene) {
        mode = selection.includes(cell.z)
          ? 'selected'
          : strongExtras.has(cell.z)
            ? 'extra-strong'
            : extras.has(cell.z)
              ? 'extra'
              : hoveredZ === cell.z
                ? 'hover'
                : 'dim';
        alpha.setX(index, mode === 'dim' ? 0.25 : 1);
      } else {
        mode = selection.includes(cell.z) ? 'selected' : hoveredZ === cell.z ? 'hover' : 'rest';
        alpha.setX(index, 1);
      }
      tiles.setColorAt(index, tileColor(cell.category, mode, color));
    });
    alpha.needsUpdate = true;
    if (tiles.instanceColor) tiles.instanceColor.needsUpdate = true;
    invalidate();
  }, [hoveredZ, selection, invalidate, elementScene, setScene, partners, hoveredPartner, extras, strongExtras, labelGeometry]);

  useEffect(() => {
    document.body.style.cursor = pickable && hoveredZ != null ? 'pointer' : 'auto';
  }, [pickable, hoveredZ]);

  useEffect(() => invalidate(), [scene, invalidate]);

  useFrame((_, delta) => {
    const tiles = tilesRef.current;
    const labels = labelsRef.current;
    if (!tiles || !labels) return;
    const state = animation.current;
    const dt = Math.min(delta, 0.05);
    let moving = false;
    const matrix = new THREE.Matrix4();

    // The group moves back (element scene) or returns to rest.
    const group = groupRef.current;
    if (group) {
      const [tx, ty, tz] = transform.position;
      const before = group.position.x + group.position.y + group.position.z + group.scale.x;
      group.position.set(damp(group.position.x, tx, 5, dt), damp(group.position.y, ty, 5, dt), damp(group.position.z, tz, 5, dt));
      group.scale.setScalar(damp(group.scale.x, transform.scale, 5, dt));
      const after = group.position.x + group.position.y + group.position.z + group.scale.x;
      if (Math.abs(after - before) > 1e-4) moving = true;
    }

    const targetOpacity = interactive || elementScene || setScene ? 1 : 0.06;
    const nextOpacity = damp(state.opacity, targetOpacity, 6, dt);
    if (Math.abs(nextOpacity - state.opacity) > 0.002) moving = true;
    state.opacity = Math.abs(nextOpacity - targetOpacity) < 0.002 ? targetOpacity : nextOpacity;
    tileMaterial.opacity = state.opacity;
    tileMaterial.depthWrite = state.opacity > 0.5;
    labelMaterial.uniforms.uOpacity!.value = state.opacity < 1 ? state.opacity * 0.6 : 1;

    for (let index = 0; index < COUNT; index += 1) {
      const z = index + 1;
      const isHover = pickable && hoveredZ === z;
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
    if (!pickable || event.instanceId == null) return;
    event.stopPropagation();
    const z = event.instanceId + 1;
    if (z === activeZ) return;
    if (z !== hoveredZ) setHoveredZ(z);
    if (elementScene) setHoveredPartner(partners.has(z) ? z : null);
  };

  const handleOut = () => {
    if (hoveredZ != null) setHoveredZ(null);
    if (elementScene && hoveredPartner != null) setHoveredPartner(null);
  };

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    if (!pickable || event.instanceId == null || event.delta > 6) return;
    event.stopPropagation();
    const cell = ELEMENTS[event.instanceId];
    if (!cell || cell.z === activeZ) return;
    if (interactive && (event.shiftKey || event.ctrlKey || event.metaKey || useAppStore.getState().selectMode)) {
      toggleSelection(cell.z);
      return;
    }
    setHoveredZ(null);
    const { navigate } = useAppStore.getState();
    if (scene.kind === 'set') {
      // In the cloud a tile adds its element to the set or removes it.
      const symbols = scene.symbols.includes(cell.symbol)
        ? scene.symbols.filter((symbol) => symbol !== cell.symbol)
        : [...scene.symbols, cell.symbol];
      navigate(symbols.length > 0 ? `/set/${symbols.join('-')}` : '/');
      return;
    }
    // In the element scene a partner tile opens the walk along its ray; any other tile jumps there.
    if (elementScene && scene.kind === 'element' && partners.has(cell.z)) navigate(`/e/${scene.symbol}/${cell.symbol}`);
    else navigate(`/e/${cell.symbol}`);
  };

  return (
    <group ref={groupRef}>
      <instancedMesh
        ref={tilesRef}
        args={[tileGeometry, tileMaterial, COUNT]}
        raycast={pickable ? THREE.InstancedMesh.prototype.raycast : noRaycast}
        onPointerMove={handleMove}
        onPointerOut={handleOut}
        onClick={handleClick}
      />
      <instancedMesh ref={labelsRef} args={[labelGeometry, labelMaterial, COUNT]} raycast={noRaycast} renderOrder={1} />
    </group>
  );
}
