import { useFrame } from '@react-three/fiber';
import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

import { approximateMassNumber, shellsOf } from '../data/periodic';
import type { Vec3 } from '../data/structure';
import { ClickGuard } from './ClickGuard';
import { damp, prefersReducedMotion, useKeepRendering } from './useKeepRendering';

const MAX_NUCLEONS = 72;
const NUCLEON_RADIUS = 0.07;
const ELECTRON_RADIUS = 0.034;
const SHELL_BASE = 0.6;
const SHELL_STEP = 0.3;
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

/** Points spread evenly inside a ball: a compact, organic-looking nucleus. */
function nucleusPoints(count: number): THREE.Vector3[] {
  const radius = NUCLEON_RADIUS * 1.25 * Math.cbrt(count);
  const points: THREE.Vector3[] = [];
  for (let i = 0; i < count; i += 1) {
    const y = 1 - (2 * (i + 0.5)) / count;
    const ring = Math.sqrt(1 - y * y);
    const theta = GOLDEN_ANGLE * i;
    const r = radius * Math.cbrt((i + 0.5) / count);
    points.push(new THREE.Vector3(Math.cos(theta) * ring * r, y * r, Math.sin(theta) * ring * r));
  }
  return points;
}

function shellRadius(index: number): number {
  return SHELL_BASE + SHELL_STEP * index;
}

/** Each shell gets its own tilt so the orbits read as 3D. */
function shellQuaternion(index: number): THREE.Quaternion {
  const euler = new THREE.Euler(Math.PI / 2 + 0.38 * Math.sin(index * 1.7), index * 0.9, 0.22 * Math.cos(index * 1.3));
  return new THREE.Quaternion().setFromEuler(euler);
}

interface AtomModelProps {
  z: number;
  position: Vec3;
}

/** Bohr-style atom: nucleus of protons and neutrons, tilted shells, orbiting electrons. */
export function AtomModel({ z, position }: AtomModelProps) {
  const groupRef = useRef<THREE.Group>(null);
  const nucleusRef = useRef<THREE.InstancedMesh>(null);
  const electronsRef = useRef<THREE.InstancedMesh>(null);
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);
  useKeepRendering(true);

  const shells = useMemo(() => shellsOf(z), [z]);
  const massNumber = approximateMassNumber(z);
  const nucleonCount = Math.min(massNumber, MAX_NUCLEONS);
  const protonCount = Math.max(1, Math.round((nucleonCount * z) / massNumber));
  const electronCount = shells.reduce((sum, n) => sum + n, 0);

  const shellRotations = useMemo(() => shells.map((_, index) => shellQuaternion(index)), [shells]);

  const ringGeometries = useMemo(
    () =>
      shells.map((_, index) => {
        const radius = shellRadius(index);
        const points = Array.from({ length: 129 }, (_, i) => {
          const angle = (i / 128) * Math.PI * 2;
          return new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0);
        });
        return new THREE.BufferGeometry().setFromPoints(points);
      }),
    [shells],
  );
  const ringMaterial = useMemo(
    () => new THREE.LineBasicMaterial({ color: '#8b9cf2', transparent: true, opacity: 0.38 }),
    [],
  );

  const sphere = useMemo(() => new THREE.SphereGeometry(1, 20, 14), []);
  const nucleusMaterial = useMemo(() => new THREE.MeshStandardMaterial({ roughness: 0.45, metalness: 0.05 }), []);
  const electronMaterial = useMemo(() => new THREE.MeshBasicMaterial({ color: '#d6ecff' }), []);

  // Electron slots: shell index and starting angle for each electron.
  const electrons = useMemo(() => {
    const slots: Array<{ shell: number; phase: number }> = [];
    shells.forEach((count, shell) => {
      for (let i = 0; i < count; i += 1) slots.push({ shell, phase: (i / count) * Math.PI * 2 + shell * 0.7 });
    });
    return slots;
  }, [shells]);

  useLayoutEffect(() => {
    const nucleus = nucleusRef.current;
    if (!nucleus) return;
    const matrix = new THREE.Matrix4();
    const color = new THREE.Color();
    const points = nucleusPoints(nucleonCount);
    // Interleave protons and neutrons so both colours show on the surface.
    points.forEach((point, index) => {
      matrix.makeScale(NUCLEON_RADIUS, NUCLEON_RADIUS, NUCLEON_RADIUS).setPosition(point);
      nucleus.setMatrixAt(index, matrix);
      const isProton = index % Math.max(1, Math.round(nucleonCount / protonCount)) === 0;
      nucleus.setColorAt(index, color.set(isProton ? '#ff7a66' : '#a9b6d6'));
    });
    nucleus.instanceMatrix.needsUpdate = true;
    if (nucleus.instanceColor) nucleus.instanceColor.needsUpdate = true;
  }, [nucleonCount, protonCount]);

  const time = useRef(0);
  const appear = useRef(0);
  const scratch = useMemo(
    () => ({ matrix: new THREE.Matrix4(), vector: new THREE.Vector3(), scale: new THREE.Vector3() }),
    [],
  );

  useFrame((_, delta) => {
    const group = groupRef.current;
    const electronsMesh = electronsRef.current;
    if (!group || !electronsMesh) return;
    const dt = Math.min(delta, 0.05);
    if (!reducedMotion) time.current += dt;
    appear.current = damp(appear.current, 1, 4, dt);
    group.scale.setScalar(0.2 + 0.8 * appear.current);
    if (!reducedMotion) group.rotation.y += dt * 0.12;

    electrons.forEach((slot, index) => {
      const radius = shellRadius(slot.shell);
      const speed = 0.9 / (1 + slot.shell * 0.55);
      const angle = slot.phase + time.current * speed;
      scratch.vector.set(Math.cos(angle) * radius, Math.sin(angle) * radius, 0).applyQuaternion(shellRotations[slot.shell]!);
      scratch.matrix.makeScale(ELECTRON_RADIUS, ELECTRON_RADIUS, ELECTRON_RADIUS).setPosition(scratch.vector);
      electronsMesh.setMatrixAt(index, scratch.matrix);
    });
    electronsMesh.instanceMatrix.needsUpdate = true;
  });

  return (
    <group ref={groupRef} position={position}>
      <ClickGuard radius={shellRadius(Math.max(shells.length - 1, 0)) + ELECTRON_RADIUS * 3} />
      <instancedMesh ref={nucleusRef} args={[sphere, nucleusMaterial, nucleonCount]} />
      {ringGeometries.map((geometry, index) => (
        <lineLoop key={index} geometry={geometry} material={ringMaterial} quaternion={shellRotations[index]!} />
      ))}
      <instancedMesh ref={electronsRef} args={[sphere, electronMaterial, Math.max(electronCount, 1)]} />
    </group>
  );
}
