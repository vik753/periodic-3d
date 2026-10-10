import type { CameraControls } from '@react-three/drei';
import { useThree } from '@react-three/fiber';
import type { ComponentRef, RefObject } from 'react';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';

import { elementBySymbol } from '../data/periodic';
import { useAppStore } from '../state/store';
import { CLOUD_CENTER, CLOUD_RADIUS, PANEL_LAYOUT, STAGE_POSITION, tableFitDistance, tilePosition } from './layout';
import { prefersReducedMotion } from './useKeepRendering';

export type ControlsRef = ComponentRef<typeof CameraControls>;

export const CAMERA_FOV = 40;

export type Pose = { position: [number, number, number]; target: [number, number, number] };

/** Panel layout breakpoint: side panel from this width, bottom sheet below it. */
export const SIDE_PANEL_MIN_WIDTH = PANEL_LAYOUT.sideMinWidth;
const SIDE_PANEL_WIDTH = PANEL_LAYOUT.sideWidth;
const SHEET_FRACTION = PANEL_LAYOUT.sheetFraction;
/** Radius of the structure viewer's bounding sphere plus a margin. */
const STAGE_RADIUS = 2.6 * 1.18;

/** Camera distance that keeps a ball of `radius` inside the area the info panel leaves free. */
export function fitDistance(width: number, height: number, radius: number, minimum = 0): number {
  const tanV = Math.tan(THREE.MathUtils.degToRad(CAMERA_FOV) / 2);
  const tanH = tanV * (width / Math.max(height, 1));
  const side = width >= SIDE_PANEL_MIN_WIDTH;
  const freeV = side ? tanV : tanV * (1 - SHEET_FRACTION);
  const freeH = side ? tanH * Math.max(0.35, 1 - SIDE_PANEL_WIDTH / width) : tanH;
  const halfAngle = Math.atan(Math.min(freeV, freeH));
  return Math.max(minimum, radius / Math.sin(halfAngle));
}

export function compoundDistance(width: number, height: number): number {
  return fitDistance(width, height, STAGE_RADIUS, 10.5);
}

/** The whole multi-element cloud in view, slightly from above. */
export function cloudOverviewPose(width: number, height: number): Pose {
  const [x, y, z] = CLOUD_CENTER;
  const distance = fitDistance(width, height, CLOUD_RADIUS * 1.2, 11);
  return { position: [x, y + distance * 0.12, z + distance], target: [x, y, z] };
}

function tablePose(aspect: number): Pose {
  const distance = tableFitDistance(aspect, CAMERA_FOV);
  // A slight low angle shows the depth of the curved table without cropping its edges.
  return { position: [0, -distance * 0.09, distance], target: [0, -0.1, 0] };
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
    // The walk along a ray drives the camera itself (RayWalk).
    if (scene.kind === 'element' && scene.partner) {
      previousKind.current = scene.kind;
      return;
    }
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
    } else if (scene.kind === 'set') {
      pose = cloudOverviewPose(size.width, size.height);
      control.minDistance = 2;
      control.maxDistance = 40;
    } else if (scene.kind === 'compound') {
      const [x, y, z] = STAGE_POSITION;
      const distance = compoundDistance(size.width, size.height);
      const direction = new THREE.Vector3(1.4, 1.0, 10.5).normalize().multiplyScalar(distance);
      pose = { position: [x + direction.x, y + direction.y, z + direction.z], target: [x, y, z] };
      control.minDistance = 3;
      control.maxDistance = Math.max(24, distance * 1.6);
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
