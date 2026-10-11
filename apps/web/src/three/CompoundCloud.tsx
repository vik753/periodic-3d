import { Html } from '@react-three/drei';
import type { ThreeEvent } from '@react-three/fiber';
import { useFrame, useThree } from '@react-three/fiber';
import type { RefObject } from 'react';
import { useEffect, useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

import type { IndexEntry } from '../data/compoundIndex';
import type { StructureData } from '../data/structure';
import { useHoverIntent } from '../lib/hoverIntent';
import { useAppStore } from '../state/store';
import type { ControlsRef } from './CameraDirector';
import { cloudOverviewPose } from './CameraDirector';
import { createGlowMaterial, glowGeometry } from './glow';
import { CLOUD_MAX } from './cloudLimits';
import { VIOLET_COLOR } from './colors';
import { CLOUD_CENTER, CLOUD_RADIUS } from './layout';
import { StructureView } from './StructureView';
import { damp, prefersReducedMotion, useKeepRendering } from './useKeepRendering';

export { CLOUD_MAX };
const ORB_RADIUS = 0.085;
const FOCUS_RADIUS = 0.75;
const LABELED = 8;
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

/**
 * Colours: compounds of exactly the selected elements are gold, those with other elements
 * cyan, predicted materials (GNoME) violet.
 */
const GOLD = new THREE.Color('#ffc857');
const CYAN = new THREE.Color('#62d2ff');
const VIOLET = new THREE.Color(VIOLET_COLOR);
const WHITE = new THREE.Color('#ffffff');

/**
 * Orb positions: a Fibonacci ball. The most famous compounds sit near the centre,
 * the rest spread outwards, so the cloud reads from the middle.
 */
export function cloudPositions(count: number, radius = CLOUD_RADIUS): THREE.Vector3[] {
  const points: THREE.Vector3[] = [];
  for (let i = 0; i < count; i += 1) {
    const y = 1 - (2 * (i + 0.5)) / Math.max(count, 1);
    const ring = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = GOLDEN_ANGLE * i;
    const r = radius * (0.35 + 0.65 * Math.cbrt((i + 1) / Math.max(count, 1)));
    points.push(new THREE.Vector3(Math.cos(theta) * ring * r, y * r * 0.8, Math.sin(theta) * ring * r));
  }
  return points;
}

/** Predicted materials (GNoME) sit on a thin shell around the known compounds: a violet halo. */
export function shellPositions(count: number, radius: number): THREE.Vector3[] {
  const points: THREE.Vector3[] = [];
  for (let i = 0; i < count; i += 1) {
    const y = 1 - (2 * (i + 0.5)) / Math.max(count, 1);
    const ring = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = GOLDEN_ANGLE * i + 0.9;
    const r = radius * (1 + 0.06 * Math.sin(i * 2.3));
    points.push(new THREE.Vector3(Math.cos(theta) * ring * r, y * r * 0.8, Math.sin(theta) * ring * r));
  }
  return points;
}

export interface CloudLabel {
  formula: string;
  name: string;
}

interface CompoundCloudProps {
  controls: RefObject<ControlsRef | null>;
  entries: IndexEntry[];
  /** Atomic numbers of the selected elements (orbs with only these are gold). */
  selected: number[];
  focusStructure: StructureData | null;
  labelFor: (entry: IndexEntry) => CloudLabel;
  elementName?: (symbol: string) => string | undefined;
}

/**
 * The compounds of a multi-element selection float as a slowly turning cloud. Hover an
 * orb to see what it is; click it to bring it closer and unfold its 3D model; click
 * again to open its card.
 */
export function CompoundCloud({ controls, entries, selected, focusStructure, labelFor, elementName }: CompoundCloudProps) {
  const groupRef = useRef<THREE.Group>(null);
  const orbsRef = useRef<THREE.InstancedMesh>(null);
  const glowRef = useRef<THREE.InstancedMesh>(null);
  const hover = useAppStore((state) => state.cloudHover);
  const focus = useAppStore((state) => state.cloudFocus);
  const setHover = useAppStore((state) => state.setCloudHover);
  const setFocus = useAppStore((state) => state.setCloudFocus);
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);
  const size = useThree((state) => state.size);
  useKeepRendering(true);

  const items = useMemo(() => entries.slice(0, CLOUD_MAX), [entries]);
  // Known compounds come first in `items`; predicted ones (if any) follow.
  const knownCount = useMemo(() => items.filter((entry) => !entry.predicted).length, [items]);
  const positions = useMemo(
    () =>
      knownCount === items.length
        ? cloudPositions(items.length)
        : [
            ...cloudPositions(knownCount, CLOUD_RADIUS * 0.78),
            ...shellPositions(items.length - knownCount, CLOUD_RADIUS * 1.1),
          ],
    [items.length, knownCount],
  );
  const strongest = useMemo(() => Math.max(1, ...items.map((entry) => entry.fame)), [items]);
  const selectedSet = useMemo(() => new Set(selected), [selected]);
  const focusIndex = items.findIndex((entry) => entry.id === focus);
  const hoverIndex = items.findIndex((entry) => entry.id === hover);
  /** Size an orb grows or shrinks to: by fame, larger when hovered, 0 under a 3D model. */
  const targetSize = (index: number, hovered: number): number => {
    const entry = items[index];
    if (!entry) return 0;
    if (index === focusIndex) return focusStructure ? 0 : 2.2;
    const base = 0.7 + 0.9 * (Math.log1p(entry.fame) / Math.log1p(strongest));
    return index === hovered ? base * 1.7 : base;
  };

  const sphere = useMemo(() => new THREE.SphereGeometry(1, 18, 12), []);
  const material = useMemo(() => new THREE.MeshBasicMaterial({ toneMapped: false }), []);
  const quad = useMemo(() => glowGeometry(), []);
  const glowMaterial = useMemo(() => createGlowMaterial(), []);
  useEffect(
    () => () => {
      sphere.dispose();
      material.dispose();
      quad.dispose();
      glowMaterial.dispose();
    },
    [sphere, material, quad, glowMaterial],
  );
  const sizes = useRef(new Float32Array(CLOUD_MAX).fill(0));

  useLayoutEffect(() => {
    const orbs = orbsRef.current;
    const glow = glowRef.current;
    if (!orbs || !glow) return;
    orbs.count = items.length;
    glow.count = items.length;
    const color = new THREE.Color();
    items.forEach((entry, index) => {
      const exact = entry.zs.every((z) => selectedSet.has(z));
      color.copy(entry.predicted ? VIOLET : exact ? GOLD : CYAN);
      glow.setColorAt(index, color);
      orbs.setColorAt(index, color.lerp(WHITE, 0.45));
    });
    if (orbs.instanceColor) orbs.instanceColor.needsUpdate = true;
    if (glow.instanceColor) glow.instanceColor.needsUpdate = true;
    sizes.current.fill(0);
  }, [items, selectedSet]);

  // The cloud turns slowly; it stops while something is in focus so the camera can stay on it.
  useFrame((_, delta) => {
    const group = groupRef.current;
    const orbs = orbsRef.current;
    const glow = glowRef.current;
    if (!group || !orbs || !glow) return;
    const dt = Math.min(delta, 0.05);
    if (!reducedMotion && focusIndex < 0) group.rotation.y += dt * 0.05;
    const matrix = new THREE.Matrix4();
    items.forEach((_, index) => {
      const target = targetSize(index, hoverIndex);
      sizes.current[index] = damp(sizes.current[index]!, target, 7, dt);
      const radius = ORB_RADIUS * sizes.current[index]!;
      matrix.makeScale(radius, radius, radius).setPosition(positions[index]!);
      orbs.setMatrixAt(index, matrix);
      const halo = radius * 7;
      matrix.makeScale(halo, halo, halo).setPosition(positions[index]!);
      glow.setMatrixAt(index, matrix);
    });
    orbs.instanceMatrix.needsUpdate = true;
    glow.instanceMatrix.needsUpdate = true;
  });

  // Focus: the camera comes close to the orb, from the outside of the cloud.
  useEffect(() => {
    const control = controls.current;
    const group = groupRef.current;
    if (!control || !group) return;
    const center = new THREE.Vector3(...CLOUD_CENTER);
    if (focusIndex < 0) {
      const pose = cloudOverviewPose(size.width, size.height);
      void control.setLookAt(...pose.position, ...pose.target, !reducedMotion);
      return;
    }
    const local = positions[focusIndex];
    if (!local) return;
    const world = local.clone().applyMatrix4(group.matrixWorld);
    const outward = world.clone().sub(center);
    if (outward.lengthSq() < 1e-4) outward.set(0, 0, 1);
    outward.normalize();
    // Look at the orb from outside the cloud, a little from above and from the camera side.
    const direction = outward.add(new THREE.Vector3(0, 0.35, 1.2)).normalize();
    const position = world.clone().addScaledVector(direction, 3.4);
    void control.setLookAt(position.x, position.y, position.z, world.x, world.y, world.z, !reducedMotion);
    // Re-run on focus changes only; the overview pose follows the viewport at that moment.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [controls, focusIndex, positions, reducedMotion]);

  // Picking. The hovered orb grows to 1.7×; picking the drawn spheres made it flicker: it
  // grew, a neighbour or the edge took the pointer, it shrank, and again. Picking now
  // uses the target sizes, not the animated ones: a resting orb answers in a slightly
  // larger sphere than it shows, the hovered one in its full grown size (hysteresis),
  // so the pointer stays on it until it really leaves. Analytic ray–sphere tests also
  // never use a stale bounding sphere of the instanced mesh.
  const pickState = useRef({ hoverIndex, targetSize });
  pickState.current = { hoverIndex, targetSize };
  const pickRaycast = useMemo(() => {
    const center = new THREE.Vector3();
    const toCenter = new THREE.Vector3();
    const scale = new THREE.Vector3();
    return (raycaster: THREE.Raycaster, intersects: THREE.Intersection[]) => {
      const orbs = orbsRef.current;
      if (!orbs) return;
      const { hoverIndex: hovered, targetSize: sizeOf } = pickState.current;
      const ray = raycaster.ray;
      scale.setFromMatrixScale(orbs.matrixWorld);
      for (let index = 0; index < orbs.count; index += 1) {
        const local = positions[index];
        if (!local) continue;
        const size = sizeOf(index, hovered) * (index === hovered ? 1 : 1.15);
        if (size <= 0) continue;
        const radius = ORB_RADIUS * size * scale.x;
        center.copy(local).applyMatrix4(orbs.matrixWorld);
        const distanceSq = ray.distanceSqToPoint(center);
        if (distanceSq > radius * radius) continue;
        const along = toCenter.subVectors(center, ray.origin).dot(ray.direction);
        const distance = along - Math.sqrt(radius * radius - distanceSq);
        if (distance < raycaster.near || distance > raycaster.far) continue;
        intersects.push({ distance, point: ray.at(distance, new THREE.Vector3()), object: orbs, instanceId: index });
      }
    };
  }, [positions]);

  // Hover intent: an orb lights up under a pointer that slows down (lib/hoverIntent.ts).
  const hoverIntent = useHoverIntent<string>(setHover, () => useAppStore.getState().cloudHover);
  const onMove = (event: ThreeEvent<PointerEvent>) => {
    if (event.instanceId == null) return;
    event.stopPropagation();
    const entry = items[event.instanceId];
    if (entry) hoverIntent.over(entry.id, event.pointerType === 'touch');
    document.body.style.cursor = 'pointer';
  };
  const onOut = () => {
    hoverIntent.out();
    document.body.style.cursor = 'auto';
  };
  const onClick = (event: ThreeEvent<MouseEvent>) => {
    if (event.instanceId == null || event.delta > 6) return;
    event.stopPropagation();
    const entry = items[event.instanceId];
    if (!entry) return;
    if (entry.id === focus) useAppStore.getState().navigate(entry.predicted ? `/m/${entry.id}` : `/c/${entry.id}`);
    else setFocus(entry.id);
  };

  // Labels: the most famous few, plus the hovered and the focused orb (fixed slots).
  const labelSlots = useMemo(() => {
    const slots: Array<{ key: string; index: number; strong: boolean }> = [];
    for (let i = 0; i < Math.min(LABELED, items.length); i += 1) slots.push({ key: `top-${i}`, index: i, strong: false });
    slots.push({ key: 'hover', index: hoverIndex, strong: true });
    return slots;
  }, [items.length, hoverIndex]);

  const focusEntry = items[focusIndex];
  const focusPosition = positions[focusIndex];
  return (
    <group position={CLOUD_CENTER}>
      <group ref={groupRef}>
        <instancedMesh
          ref={orbsRef}
          args={[sphere, material, CLOUD_MAX]}
          raycast={pickRaycast}
          onPointerMove={onMove}
          onPointerOut={onOut}
          onClick={onClick}
          frustumCulled={false}
        />
        <instancedMesh
          ref={glowRef}
          args={[quad, glowMaterial, CLOUD_MAX]}
          raycast={() => null}
          frustumCulled={false}
          renderOrder={2}
        />
        {focusEntry && focusPosition && focusStructure && (
          <StructureView
            key={focusEntry.id}
            data={focusStructure}
            position={[focusPosition.x, focusPosition.y, focusPosition.z]}
            fitRadius={FOCUS_RADIUS}
            hoverLabel={false}
            elementName={elementName}
          />
        )}
        {labelSlots.map((slot) => {
          const entry = items[slot.index];
          const position = positions[slot.index] ?? positions[0] ?? new THREE.Vector3();
          const hidden = !entry || (slot.key !== 'hover' && (slot.index === hoverIndex || slot.index === focusIndex));
          const label = entry ? labelFor(entry) : null;
          const lift = slot.index === focusIndex ? FOCUS_RADIUS + 0.25 : 0.24;
          return (
            <Html
              key={slot.key}
              position={[position.x, position.y + lift, position.z]}
              center
              zIndexRange={[20, 0]}
              style={{ pointerEvents: 'none', visibility: hidden ? 'hidden' : 'visible' }}
            >
              <div
                className={`whitespace-nowrap rounded-xl px-2.5 py-0.5 text-center backdrop-blur-md ${
                  slot.strong
                    ? `bg-panel ring-1 ${entry?.predicted ? 'ring-violet/60' : 'ring-cyan/50'}`
                    : 'bg-panel/40'
                }`}
              >
                <div className={`font-display font-semibold text-text ${slot.strong ? 'text-sm' : 'text-[11px] opacity-80'}`}>
                  {label?.formula}
                </div>
                {slot.strong && label?.name ? <div className="text-xs text-muted">{label.name}</div> : null}
              </div>
            </Html>
          );
        })}
      </group>
    </group>
  );
}
