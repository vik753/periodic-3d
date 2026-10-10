import { Html } from '@react-three/drei';
import type { ThreeEvent } from '@react-three/fiber';
import { useFrame, useThree } from '@react-three/fiber';
import type { RefObject } from 'react';
import { useEffect, useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

import type { CompoundSummary, Partner } from '../data/api';
import type { StructureData, Vec3 } from '../data/structure';
import { useAppStore } from '../state/store';
import type { ControlsRef } from './CameraDirector';
import type { TableTransform } from './layout';
import { buildRayCurves } from './Rays';
import { StructureView } from './StructureView';
import { damp, prefersReducedMotion, useKeepRendering } from './useKeepRendering';

const MAX_BEADS = 30;
const T_START = 0.2;
const T_END = 0.94;
const BEAD_RADIUS = 0.075;
const DRAG_STEP_PX = 70;
/** Size of the 3D model of the compound in focus (world units). */
const FOCUS_RADIUS = 0.36;
/** Labels exist for the bead in focus and two neighbours on each side. */
const LABEL_SLOTS = [-2, -1, 0, 1, 2] as const;
const WHEEL_STEP = 90;
/** camera-controls ACTION.NONE: the walk takes over drag and wheel. */
const ACTION_NONE = 0;

/** Position of bead i of n along the ray (0…1 along the curve). */
export function beadT(index: number, count: number): number {
  if (count <= 1) return (T_START + T_END) / 2;
  return T_START + ((T_END - T_START) * index) / (count - 1);
}

export interface BeadLabel {
  formula: string;
  name: string;
}

interface RayWalkProps {
  controls: RefObject<ControlsRef | null>;
  origin: Vec3;
  transform: TableTransform;
  partner: Partner;
  compounds: CompoundSummary[];
  /** 3D structure of the compound in focus, once loaded. */
  focusStructure: StructureData | null;
  labelFor: (compound: CompoundSummary) => BeadLabel;
  elementName?: (symbol: string) => string | undefined;
}

/**
 * Walking along one ray: the compounds of the pair sit on the ray like beads. Drag along
 * the ray, scroll or use the arrow keys to move from bead to bead; the camera follows and
 * the compound in focus unfolds into its 3D model.
 */
export function RayWalk({
  controls,
  origin,
  transform,
  partner,
  compounds,
  focusStructure,
  labelFor,
  elementName,
}: RayWalkProps) {
  const camera = useThree((state) => state.camera);
  const gl = useThree((state) => state.gl);
  const size = useThree((state) => state.size);
  const walkIndex = useAppStore((state) => state.walkIndex);
  const setWalkIndex = useAppStore((state) => state.setWalkIndex);
  const beadsRef = useRef<THREE.InstancedMesh>(null);
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);
  useKeepRendering(true);

  const curve = useMemo(() => buildRayCurves(origin, [partner], transform)[0]?.curve ?? null, [origin, partner, transform]);
  const beads = useMemo(() => compounds.slice(0, MAX_BEADS), [compounds]);
  const count = beads.length;
  const index = Math.min(walkIndex, Math.max(count - 1, 0));
  const positions = useMemo(
    () => (curve ? beads.map((_, i) => curve.getPoint(beadT(i, count))) : []),
    [curve, beads, count],
  );

  const sphere = useMemo(() => new THREE.SphereGeometry(1, 16, 12), []);
  const material = useMemo(
    () => new THREE.MeshBasicMaterial({ color: '#ffd6da', transparent: true, opacity: 0.9, toneMapped: false }),
    [],
  );
  const sizes = useRef<Float32Array>(new Float32Array(MAX_BEADS));

  // The camera follows the bead in focus: a little behind it on the ray, off to the side.
  useEffect(() => {
    const control = controls.current;
    if (!control || !curve || count === 0) return;
    const t = beadT(index, count);
    const point = curve.getPoint(t);
    const tangent = curve.getTangent(t).normalize();
    const side = new THREE.Vector3(0, 1, 0).cross(tangent);
    if (side.lengthSq() < 1e-6) side.set(1, 0, 0);
    side.normalize();
    const position = point
      .clone()
      .addScaledVector(tangent, -2.7)
      .addScaledVector(side, 1.45)
      .add(new THREE.Vector3(0, 0.9, 0));
    control.minDistance = 1.5;
    control.maxDistance = 12;
    void control.setLookAt(position.x, position.y, position.z, point.x, point.y, point.z, !reducedMotion);
  }, [controls, curve, index, count, reducedMotion]);

  // Drag and wheel move along the ray instead of orbiting the camera.
  const screenDirection = useRef(new THREE.Vector2(0, -1));
  useEffect(() => {
    const control = controls.current;
    const element = gl.domElement;
    const saved = control
      ? {
          left: control.mouseButtons.left,
          wheel: control.mouseButtons.wheel,
          one: control.touches.one,
          two: control.touches.two,
        }
      : null;
    if (control) {
      control.mouseButtons.left = ACTION_NONE;
      control.mouseButtons.wheel = ACTION_NONE;
      control.touches.one = ACTION_NONE;
      control.touches.two = ACTION_NONE;
    }
    const step = (direction: number) => {
      const state = useAppStore.getState();
      const next = Math.max(0, Math.min(count - 1, state.walkIndex + direction));
      if (next !== state.walkIndex) state.setWalkIndex(next);
    };
    let dragging = false;
    let lastX = 0;
    let lastY = 0;
    let dragged = 0;
    let wheel = 0;
    const onDown = (event: PointerEvent) => {
      if (event.button !== 0) return;
      dragging = true;
      lastX = event.clientX;
      lastY = event.clientY;
      dragged = 0;
    };
    const onMove = (event: PointerEvent) => {
      if (!dragging) return;
      const dx = event.clientX - lastX;
      const dy = event.clientY - lastY;
      lastX = event.clientX;
      lastY = event.clientY;
      dragged += dx * screenDirection.current.x + dy * screenDirection.current.y;
      while (dragged > DRAG_STEP_PX) {
        step(1);
        dragged -= DRAG_STEP_PX;
      }
      while (dragged < -DRAG_STEP_PX) {
        step(-1);
        dragged += DRAG_STEP_PX;
      }
    };
    const onUp = () => {
      dragging = false;
    };
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      wheel += event.deltaY;
      if (Math.abs(wheel) >= WHEEL_STEP) {
        step(Math.sign(wheel));
        wheel = 0;
      }
    };
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return;
      if (event.key === 'ArrowRight' || event.key === 'ArrowUp') {
        event.preventDefault();
        step(1);
      } else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') {
        event.preventDefault();
        step(-1);
      }
    };
    element.addEventListener('pointerdown', onDown);
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
    element.addEventListener('wheel', onWheel, { passive: false });
    window.addEventListener('keydown', onKey);
    return () => {
      element.removeEventListener('pointerdown', onDown);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
      element.removeEventListener('wheel', onWheel);
      window.removeEventListener('keydown', onKey);
      if (control && saved) {
        control.mouseButtons.left = saved.left;
        control.mouseButtons.wheel = saved.wheel;
        control.touches.one = saved.one;
        control.touches.two = saved.two;
      }
    };
  }, [controls, gl, count]);

  useLayoutEffect(() => {
    const mesh = beadsRef.current;
    if (!mesh) return;
    mesh.count = count;
    sizes.current.fill(0);
  }, [count]);

  const scratch = useMemo(() => ({ matrix: new THREE.Matrix4(), a: new THREE.Vector3(), b: new THREE.Vector3() }), []);
  useFrame((_, delta) => {
    const mesh = beadsRef.current;
    if (!mesh || !curve) return;
    const dt = Math.min(delta, 0.05);
    const pulse = reducedMotion ? 1 : 1 + 0.12 * Math.sin(performance.now() / 300);
    for (let i = 0; i < count; i += 1) {
      // The focused bead opens into the 3D model; its neighbours are a little larger.
      // Beads already passed shrink: they sit between the camera and the focus.
      const target =
        i === index ? (focusStructure ? 0 : 2.2 * pulse) : i < index ? 0.45 : i === index + 1 ? 1.3 : 1;
      sizes.current[i] = damp(sizes.current[i]!, target, 8, dt);
      const radius = BEAD_RADIUS * sizes.current[i]!;
      scratch.matrix.makeScale(radius, radius, radius).setPosition(positions[i]!);
      mesh.setMatrixAt(i, scratch.matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;
    // Screen direction of the ray at the bead in focus: dragging along it walks forward.
    const t = beadT(index, count);
    scratch.a.copy(curve.getPoint(t)).project(camera);
    scratch.b.copy(curve.getPoint(Math.min(1, t + 0.05))).project(camera);
    const dx = (scratch.b.x - scratch.a.x) * size.width;
    const dy = -(scratch.b.y - scratch.a.y) * size.height;
    const length = Math.hypot(dx, dy);
    if (length > 8) screenDirection.current.set(dx / length, dy / length);
    else screenDirection.current.set(0, -1); // the ray points into the screen: drag up to go forward
  });

  const onBeadClick = (event: ThreeEvent<MouseEvent>) => {
    if (event.instanceId == null || event.delta > 6) return;
    event.stopPropagation();
    if (event.instanceId === index) {
      const compound = beads[index];
      if (compound) useAppStore.getState().navigate(`/c/${compound.id}`);
    } else {
      setWalkIndex(event.instanceId);
    }
  };

  const focus = beads[index];
  const focusPosition = positions[index];
  if (!curve || count === 0) return null;
  return (
    <group>
      <instancedMesh
        ref={beadsRef}
        args={[sphere, material, MAX_BEADS]}
        onClick={onBeadClick}
        onPointerOver={() => {
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={() => {
          document.body.style.cursor = 'auto';
        }}
        frustumCulled={false}
        renderOrder={3}
      />
      {focus && focusPosition && focusStructure && (
        <StructureView
          key={focus.id}
          data={focusStructure}
          position={[focusPosition.x, focusPosition.y, focusPosition.z]}
          fitRadius={FOCUS_RADIUS}
          hoverLabel={false}
          elementName={elementName}
        />
      )}
      {LABEL_SLOTS.map((slot) => {
        // Fixed slots keep the DOM labels mounted while the walk moves (no churn of portals).
        const i = index + slot;
        const compound = beads[i];
        const position = positions[i] ?? positions[index] ?? new THREE.Vector3();
        const focused = slot === 0;
        const label = compound ? labelFor(compound) : null;
        return (
          <Html
            key={slot}
            position={[position.x, position.y + (focused ? FOCUS_RADIUS + 0.3 : 0.22), position.z]}
            center
            zIndexRange={[20, 0]}
            style={{ pointerEvents: 'none', visibility: label ? 'visible' : 'hidden' }}
          >
            <div
              className={`whitespace-nowrap rounded-xl px-3 py-1 text-center backdrop-blur-md ${
                focused ? 'bg-panel ring-1 ring-ray/60' : 'bg-panel/50 opacity-70'
              }`}
            >
              <div className={`font-display font-semibold text-text ${focused ? 'text-base' : 'text-xs'}`}>
                {label?.formula}
              </div>
              {focused && label?.name ? <div className="text-xs text-muted">{label.name}</div> : null}
            </div>
          </Html>
        );
      })}
    </group>
  );
}
