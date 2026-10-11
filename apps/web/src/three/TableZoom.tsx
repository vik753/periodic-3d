import { useThree } from '@react-three/fiber';
import type { RefObject } from 'react';
import { useEffect } from 'react';
import * as THREE from 'three';

import type { Vec3 } from '../data/structure';
import { useAppStore } from '../state/store';
import type { ControlsRef } from './CameraDirector';
import { tablePose } from './CameraDirector';
import { PINCH_BOOST, wheelPixels, zoomDistance, zoomRig } from './zoom';

/** Smoothing of wheel steps: quicker than the scene flights (0.55 s). */
const WHEEL_SMOOTH_TIME = 0.22;
/** Keyboard + and − move as far as this much wheel scrolling. */
const KEY_STEP_PIXELS = 160;

const ray = new THREE.Raycaster();
const plane = new THREE.Plane();
const scratch = { position: new THREE.Vector3(), target: new THREE.Vector3(), normal: new THREE.Vector3() };

function toVec3(vector: THREE.Vector3): Vec3 {
  return [vector.x, vector.y, vector.z];
}

/**
 * Table view: the wheel (and + / − keys) zooms towards the element under the cursor,
 * from the whole table to one tile in about one scroll. Other scenes keep the default
 * camera-controls dolly. Touch pinch stays with camera-controls (dolly to the fingers).
 */
export function TableZoom({ controls }: { controls: RefObject<ControlsRef | null> }) {
  const camera = useThree((state) => state.camera);
  const gl = useThree((state) => state.gl);
  const eventSource = useThree((state) => state.events.connected) as HTMLElement | undefined;
  const size = useThree((state) => state.size);

  useEffect(() => {
    const element = eventSource ?? gl.domElement;

    const zoomAt = (clientX: number, clientY: number, pixels: number) => {
      const control = controls.current;
      if (!control) return;
      control.getPosition(scratch.position, true);
      control.getTarget(scratch.target, true);
      const distance = scratch.position.distanceTo(scratch.target);
      const next = zoomDistance(distance, pixels, control.minDistance, control.maxDistance);
      if (Math.abs(next - distance) < 1e-4) return;
      const rect = gl.domElement.getBoundingClientRect();
      const ndc = new THREE.Vector2(
        ((clientX - rect.left) / rect.width) * 2 - 1,
        -((clientY - rect.top) / rect.height) * 2 + 1,
      );
      ray.setFromCamera(ndc, camera);
      scratch.normal.subVectors(scratch.target, scratch.position).normalize();
      plane.setFromNormalAndCoplanarPoint(scratch.normal, scratch.target);
      const hit = ray.ray.intersectPlane(plane, new THREE.Vector3()) ?? scratch.target.clone();
      const home = tablePose(size.width / Math.max(size.height, 1));
      const rig = zoomRig(
        { position: toVec3(scratch.position), target: toVec3(scratch.target) },
        toVec3(hit),
        distance,
        next,
        home,
        control.maxDistance,
      );
      control.smoothTime = WHEEL_SMOOTH_TIME;
      void control.setLookAt(...rig.position, ...rig.target, true);
    };

    const onWheel = (event: WheelEvent) => {
      if (useAppStore.getState().scene.kind !== 'table') return;
      event.preventDefault();
      event.stopPropagation(); // camera-controls would dolly as well
      const pixels = wheelPixels(event.deltaY, event.deltaMode) * (event.ctrlKey ? PINCH_BOOST : 1);
      zoomAt(event.clientX, event.clientY, pixels);
    };

    const onKey = (event: KeyboardEvent) => {
      if (useAppStore.getState().scene.kind !== 'table' || event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      if (target && (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable)) return;
      const direction = event.key === '+' || event.key === '=' ? -1 : event.key === '-' || event.key === '_' ? 1 : 0;
      if (!direction) return;
      event.preventDefault();
      const rect = gl.domElement.getBoundingClientRect();
      zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, direction * KEY_STEP_PIXELS);
    };

    element.addEventListener('wheel', onWheel, { passive: false, capture: true });
    window.addEventListener('keydown', onKey);
    return () => {
      element.removeEventListener('wheel', onWheel, { capture: true });
      window.removeEventListener('keydown', onKey);
    };
  }, [camera, controls, eventSource, gl, size.height, size.width]);

  return null;
}
