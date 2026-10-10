import { Html } from '@react-three/drei';
import type { ThreeEvent } from '@react-three/fiber';
import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

import { atomColor, covalentRadius } from '../data/chemistry';
import type { StructureData, Vec3 } from '../data/structure';
import { boundingRadius, centroid } from '../data/structure';
import { useAppStore } from '../state/store';
import { damp, prefersReducedMotion, useKeepRendering } from './useKeepRendering';

/** The structure is scaled so its bounding sphere has this radius in world units. */
export const FIT_RADIUS = 2.6;
/** Small molecules are not blown up beyond this many world units per ångström. */
const MAX_SCALE = 1.25;
const BOND_RADIUS = 0.1; // ångström
const RESUME_ROTATION_MS = 5000;
const Y_AXIS = new THREE.Vector3(0, 1, 0);

function displayRadius(symbol: string): number {
  // Ball-and-stick: small balls that still show relative atom size.
  return 0.2 + 0.25 * covalentRadius(symbol);
}

interface BondInstance {
  start: THREE.Vector3;
  end: THREE.Vector3;
  color: string;
}

function buildBondHalves(data: StructureData, center: Vec3, scale: number): BondInstance[] {
  const halves: BondInstance[] = [];
  const offsetAxis = new THREE.Vector3();
  for (const [a, b, order] of data.bonds) {
    const atomA = data.atoms[a];
    const atomB = data.atoms[b];
    if (!atomA || !atomB) continue;
    const pa = new THREE.Vector3(atomA.x - center[0], atomA.y - center[1], atomA.z - center[2]).multiplyScalar(scale);
    const pb = new THREE.Vector3(atomB.x - center[0], atomB.y - center[1], atomB.z - center[2]).multiplyScalar(scale);
    const direction = pb.clone().sub(pa).normalize();
    // A perpendicular axis for drawing double and triple bonds side by side.
    offsetAxis.set(0, 0, 1).cross(direction);
    if (offsetAxis.lengthSq() < 1e-6) offsetAxis.set(1, 0, 0).cross(direction);
    offsetAxis.normalize().multiplyScalar(0.13 * scale);
    const lines = order >= 3 ? 3 : order >= 2 ? 2 : 1;
    for (let line = 0; line < lines; line += 1) {
      const shift = offsetAxis.clone().multiplyScalar(lines === 1 ? 0 : line - (lines - 1) / 2);
      const start = pa.clone().add(shift);
      const end = pb.clone().add(shift);
      const middle = start.clone().lerp(end, 0.5);
      halves.push({ start, end: middle, color: atomColor(atomA.el) });
      halves.push({ start: middle.clone(), end, color: atomColor(atomB.el) });
    }
  }
  return halves;
}

interface StructureViewProps {
  data: StructureData;
  position: Vec3;
  /** Localized element names for the hover label. */
  elementName?: (symbol: string) => string | undefined;
  /** Radius of the fitted structure in world units (smaller for previews on a ray). */
  fitRadius?: number;
}

export function StructureView({ data, position, elementName, fitRadius = FIT_RADIUS }: StructureViewProps) {
  const groupRef = useRef<THREE.Group>(null);
  const atomsRef = useRef<THREE.InstancedMesh>(null);
  const bondsRef = useRef<THREE.InstancedMesh>(null);
  const controls = useThree((state) => state.controls) as unknown as THREE.EventDispatcher<{
    controlstart: object;
    controlend: object;
  }> | null;
  const hoveredAtom = useAppStore((state) => state.hoveredAtom);
  const setHoveredAtom = useAppStore((state) => state.setHoveredAtom);
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);
  useKeepRendering(true);

  const center = useMemo(() => centroid(data.atoms), [data]);
  const scale = useMemo(
    () => Math.min(fitRadius / Math.max(boundingRadius(data.atoms), 1.2), (MAX_SCALE * fitRadius) / FIT_RADIUS),
    [data, fitRadius],
  );
  const halves = useMemo(() => buildBondHalves(data, center, scale), [data, center, scale]);
  const isCrystal = data.kind === 'crystal';

  const sphere = useMemo(() => new THREE.SphereGeometry(1, 28, 18), []);
  const cylinder = useMemo(() => new THREE.CylinderGeometry(1, 1, 1, 14, 1, true), []);
  const atomMaterial = useMemo(() => new THREE.MeshStandardMaterial({ roughness: 0.32, metalness: 0.06 }), []);
  const bondMaterial = useMemo(() => new THREE.MeshStandardMaterial({ roughness: 0.5, metalness: 0.02 }), []);

  const atomPositions = useMemo(
    () =>
      data.atoms.map(
        (atom) => new THREE.Vector3(atom.x - center[0], atom.y - center[1], atom.z - center[2]).multiplyScalar(scale),
      ),
    [data, center, scale],
  );

  useLayoutEffect(() => {
    const atoms = atomsRef.current;
    if (!atoms) return;
    const matrix = new THREE.Matrix4();
    const color = new THREE.Color();
    data.atoms.forEach((atom, index) => {
      const radius = displayRadius(atom.el) * scale * (isCrystal ? 1.15 : 1);
      matrix.makeScale(radius, radius, radius).setPosition(atomPositions[index]!);
      atoms.setMatrixAt(index, matrix);
      atoms.setColorAt(index, color.set(atomColor(atom.el)));
    });
    atoms.instanceMatrix.needsUpdate = true;
    if (atoms.instanceColor) atoms.instanceColor.needsUpdate = true;
    atoms.computeBoundingSphere();
  }, [data, atomPositions, scale, isCrystal]);

  useLayoutEffect(() => {
    const bonds = bondsRef.current;
    if (!bonds) return;
    const matrix = new THREE.Matrix4();
    const quaternion = new THREE.Quaternion();
    const color = new THREE.Color();
    const radius = BOND_RADIUS * scale * (isCrystal ? 0.7 : 1);
    halves.forEach((half, index) => {
      const direction = half.end.clone().sub(half.start);
      const length = direction.length();
      quaternion.setFromUnitVectors(Y_AXIS, direction.normalize());
      const middle = half.start.clone().lerp(half.end, 0.5);
      matrix.compose(middle, quaternion, new THREE.Vector3(radius, length, radius));
      bonds.setMatrixAt(index, matrix);
      bonds.setColorAt(index, color.set(half.color));
    });
    bonds.instanceMatrix.needsUpdate = true;
    if (bonds.instanceColor) bonds.instanceColor.needsUpdate = true;
  }, [halves, scale, isCrystal]);

  const cellLines = useMemo(() => {
    if (!data.cell) return null;
    const origin = new THREE.Vector3(...(data.cellOrigin ?? [0, 0, 0])).sub(new THREE.Vector3(...center)).multiplyScalar(scale);
    const [a, b, c] = data.cell.map((v) => new THREE.Vector3(...v).multiplyScalar(scale)) as [
      THREE.Vector3,
      THREE.Vector3,
      THREE.Vector3,
    ];
    const corners = [0, 1].flatMap((i) =>
      [0, 1].flatMap((j) => [0, 1].map((k) => origin.clone().addScaledVector(a, i).addScaledVector(b, j).addScaledVector(c, k))),
    );
    const edges: Array<[number, number]> = [
      [0, 1], [0, 2], [0, 4], [1, 3], [1, 5], [2, 3], [2, 6], [3, 7], [4, 5], [4, 6], [5, 7], [6, 7],
    ];
    const points = edges.flatMap(([from, to]) => [corners[from]!, corners[to]!]);
    return new THREE.BufferGeometry().setFromPoints(points);
  }, [data, center, scale]);
  const cellMaterial = useMemo(
    () => new THREE.LineBasicMaterial({ color: '#8b9cf2', transparent: true, opacity: 0.5 }),
    [],
  );

  // Slow rotation that pauses while the visitor drags, and resumes after a few seconds.
  const interaction = useRef({ active: false, last: -Infinity });
  useEffect(() => {
    if (!controls) return;
    const onStart = () => {
      interaction.current.active = true;
    };
    const onEnd = () => {
      interaction.current.active = false;
      interaction.current.last = performance.now();
    };
    controls.addEventListener('controlstart', onStart);
    controls.addEventListener('controlend', onEnd);
    return () => {
      controls.removeEventListener('controlstart', onStart);
      controls.removeEventListener('controlend', onEnd);
    };
  }, [controls]);

  const appear = useRef(0);
  useFrame((_, delta) => {
    const group = groupRef.current;
    if (!group) return;
    const dt = Math.min(delta, 0.05);
    appear.current = damp(appear.current, 1, 4, dt);
    group.scale.setScalar(0.3 + 0.7 * appear.current);
    const idle = !interaction.current.active && performance.now() - interaction.current.last > RESUME_ROTATION_MS;
    if (idle && !reducedMotion) group.rotation.y += dt * 0.16;
  });

  const handleMove = (event: ThreeEvent<PointerEvent>) => {
    if (event.instanceId == null) return;
    event.stopPropagation();
    if (event.instanceId !== hoveredAtom) setHoveredAtom(event.instanceId);
  };

  const hovered = hoveredAtom != null ? data.atoms[hoveredAtom] : undefined;
  const hoveredPosition = hoveredAtom != null ? atomPositions[hoveredAtom] : undefined;

  return (
    <group ref={groupRef} position={position}>
      <instancedMesh
        ref={atomsRef}
        args={[sphere, atomMaterial, data.atoms.length]}
        onPointerMove={handleMove}
        onPointerOut={() => setHoveredAtom(null)}
      />
      {halves.length > 0 && <instancedMesh ref={bondsRef} args={[cylinder, bondMaterial, halves.length]} raycast={() => null} />}
      {cellLines && <lineSegments geometry={cellLines} material={cellMaterial} />}
      {hovered && hoveredPosition && (
        <Html
          position={hoveredPosition}
          center
          distanceFactor={9 * (fitRadius / FIT_RADIUS)}
          zIndexRange={[20, 0]}
          pointerEvents="none"
        >
          <div className="pointer-events-none -translate-y-7 whitespace-nowrap rounded-full bg-panel px-3 py-1 text-sm ring-1 ring-rim backdrop-blur-md">
            <span className="font-display font-semibold">{hovered.el}</span>
            {elementName?.(hovered.el) ? <span className="ml-2 text-muted">{elementName(hovered.el)}</span> : null}
          </div>
        </Html>
      )}
    </group>
  );
}
