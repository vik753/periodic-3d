import type { CameraControls } from '@react-three/drei';
import { useThree } from '@react-three/fiber';
import type { ComponentRef, RefObject } from 'react';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';

import { elementBySymbol } from '../data/periodic';
import { useAppStore } from '../state/store';
import { STAGE_POSITION, tableFitDistance, tilePosition } from './layout';
import { prefersReducedMotion } from './useKeepRendering';

export type ControlsRef = ComponentRef<typeof CameraControls>;

export const CAMERA_FOV = 40;

type Pose = { position: [number, number, number]; target: [number, number, number] };

function tablePose(aspect: number): Pose {
  const distance = tableFitDistance(aspect, CAMERA_FOV);
  // A slight low, left angle shows the depth of the curved table.
  return { position: [-distance * 0.06, -distance * 0.11, distance], target: [0, -0.15, 0] };
}

/**
 * Moves the camera when the scene changes. Every transition is a smooth,
 * interruptible flight (camera-controls); reduced motion jumps instantly.
 */
export function CameraDirector({ controls }: { controls: RefObject<ControlsRef | null> }) {
  const scene = useAppStore((state) => state.scene);
  const size = useThree((state) => state.size);
  const aspect = size.width / Math.max(size.height, 1);
  const previousKind = useRef<string | null>(null);

  useEffect(() => {
    const control = controls.current;
    if (!control) return;
    const animate = previousKind.current !== null && !prefersReducedMotion();
    previousKind.current = scene.kind;

    // Free orbit while flying; the table view gets gentle limits afterwards.
    control.minPolarAngle = 0;
    control.maxPolarAngle = Math.PI;
    control.minAzimuthAngle = -Infinity;
    control.maxAzimuthAngle = Infinity;

    let pose: Pose;
    if (scene.kind === 'element') {
      const cell = elementBySymbol(scene.symbol);
      const [x, y, z] = cell ? tilePosition(cell) : [0, 0, 0];
      pose = { position: [x + 0.6, y - 0.4, z + 6.4], target: [x, y, z] };
      control.minDistance = 2.5;
      control.maxDistance = 16;
    } else if (scene.kind === 'compound') {
      const [x, y, z] = STAGE_POSITION;
      pose = { position: [x + 1.2, y + 0.9, z + 9], target: [x, y, z] };
      control.minDistance = 3;
      control.maxDistance = 24;
    } else {
      pose = tablePose(aspect);
      control.minDistance = 6;
      control.maxDistance = pose.position[2] * 1.8;
    }

    void control.setLookAt(...pose.position, ...pose.target, animate).then(() => {
      if (scene.kind !== 'table') return;
      // Keep the table readable: limited tilt and turn around the current view.
      const azimuth = control.azimuthAngle;
      const polar = control.polarAngle;
      control.minAzimuthAngle = azimuth - 0.75;
      control.maxAzimuthAngle = azimuth + 0.75;
      control.minPolarAngle = Math.max(0.15, polar - 0.6);
      control.maxPolarAngle = Math.min(Math.PI - 0.15, polar + 0.6);
    });
    // Re-fit only the table view on resize; other scenes keep the visitor's camera.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene, scene.kind === 'table' ? aspect : 0, controls]);

  return null;
}

/** Utility for tests and debugging: current camera distance to its target. */
export function cameraDistance(control: ControlsRef | null): number {
  if (!control) return 0;
  const target = new THREE.Vector3();
  control.getTarget(target);
  return control.camera.position.distanceTo(target);
}
