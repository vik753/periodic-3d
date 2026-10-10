import { CameraControls } from '@react-three/drei';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import * as THREE from 'three';

import { pickName } from '../data/api';
import { demoCompound } from '../data/demo';
import { useCompound, useElements } from '../data/hooks';
import { elementBySymbol } from '../data/periodic';
import type { StructureData } from '../data/structure';
import { useAppStore } from '../state/store';
import { AtomModel } from './AtomModel';
import type { ControlsRef } from './CameraDirector';
import { CAMERA_FOV, CameraDirector } from './CameraDirector';
import { Dust } from './Dust';
import { STAGE_POSITION, tilePosition } from './layout';
import { PeriodicTable3D } from './PeriodicTable3D';
import { StructureView } from './StructureView';
import { damp } from './useKeepRendering';

declare global {
  interface Window {
    /** Exposed for screenshot tests: readiness flag, render stats and a tile projector. */
    __p3d?: {
      ready?: boolean;
      calls?: number;
      triangles?: number;
      scene?: string;
      project?: (symbol: string) => { x: number; y: number } | null;
    };
  }
}

function ElementStage() {
  const scene = useAppStore((state) => state.scene);
  if (scene.kind !== 'element') return null;
  const cell = elementBySymbol(scene.symbol);
  if (!cell) return null;
  return <AtomModel key={cell.z} z={cell.z} position={tilePosition(cell)} />;
}

function CompoundStage({ id, structure }: { id: string | null; structure: StructureData | null }) {
  if (!id || !structure) return null;
  return <StructureView key={id} data={structure} position={STAGE_POSITION} />;
}

/**
 * Shifts the rendered image away from the info panel so the object stays in the free
 * area: left of the side panel on wide screens, above the bottom sheet on phones.
 */
function PanelAwareViewOffset() {
  const camera = useThree((state) => state.camera);
  const size = useThree((state) => state.size);
  const invalidate = useThree((state) => state.invalidate);
  const sceneKind = useAppStore((state) => state.scene.kind);
  const current = useRef({ x: 0, y: 0, width: 0, height: 0 });

  const target =
    sceneKind === 'table'
      ? { x: 0, y: 0 }
      : size.width >= 640
        ? { x: 180, y: 0 }
        : { x: 0, y: Math.round(size.height * 0.2) };

  useEffect(() => invalidate(), [target.x, target.y, invalidate]);

  useFrame((_, delta) => {
    if (!(camera instanceof THREE.PerspectiveCamera)) return;
    const state = current.current;
    const dt = Math.min(delta, 0.05);
    let x = damp(state.x, target.x, 6, dt);
    let y = damp(state.y, target.y, 6, dt);
    const settled = Math.abs(x - target.x) < 0.5 && Math.abs(y - target.y) < 0.5;
    if (settled) {
      x = target.x;
      y = target.y;
    }
    const changed = x !== state.x || y !== state.y || size.width !== state.width || size.height !== state.height;
    if (!changed) return;
    current.current = { x, y, width: size.width, height: size.height };
    camera.setViewOffset(size.width, size.height, x, y, size.width, size.height);
    if (!settled) invalidate();
  });
  return null;
}

/** Publishes render stats and a readiness flag for the screenshot script. */
function RenderStats() {
  const gl = useThree((state) => state.gl);
  const camera = useThree((state) => state.camera);
  const size = useThree((state) => state.size);
  const scene = useAppStore((state) => state.scene);

  useEffect(() => {
    window.__p3d = {
      ...window.__p3d,
      project: (symbol: string) => {
        const cell = elementBySymbol(symbol);
        if (!cell) return null;
        const point = new THREE.Vector3(...tilePosition(cell)).project(camera);
        return { x: ((point.x + 1) / 2) * size.width, y: ((1 - point.y) / 2) * size.height };
      },
    };
  }, [camera, size]);
  useFrame(() => {
    window.__p3d = {
      ...window.__p3d,
      calls: gl.info.render.calls,
      triangles: gl.info.render.triangles,
      scene: scene.kind,
    };
  });
  useEffect(() => {
    let timer = 0;
    void document.fonts.ready.then(() => {
      timer = window.setTimeout(() => {
        window.__p3d = { ...window.__p3d, ready: true };
      }, 400);
    });
    return () => window.clearTimeout(timer);
  }, []);
  return null;
}

export function Scene() {
  const controls = useRef<ControlsRef>(null);
  const dpr = useMemo(() => Math.min(window.devicePixelRatio || 1, 1.75), []);
  const { i18n } = useTranslation();

  // Data hooks run here, outside the Canvas, and reach the 3D tree as props.
  const elements = useElements();
  const names = useMemo(
    () =>
      elements.data
        ? new Map(elements.data.elements.map((element) => [element.z, pickName(element.names, i18n.language)] as const))
        : undefined,
    [elements.data, i18n.language],
  );
  const scene = useAppStore((state) => state.scene);
  const compoundId = scene.kind === 'compound' ? scene.id : null;
  const compound = useCompound(compoundId);
  const structure = compoundId ? (demoCompound(compoundId)?.structure ?? compound.data?.structure ?? null) : null;

  return (
    <Canvas
      className="!fixed inset-0"
      dpr={dpr}
      frameloop="demand"
      camera={{ position: [0, 0, 26], fov: CAMERA_FOV, near: 0.1, far: 400 }}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      aria-label="3D scene"
    >
      <color attach="background" args={['#070b1a']} />
      <fog attach="fog" args={['#070b1a', 34, 95]} />
      <ambientLight intensity={0.6} />
      <directionalLight position={[8, 14, 18]} intensity={1.8} />
      <directionalLight position={[-12, -6, 10]} intensity={0.5} color="#8fa2ff" />
      <CameraControls ref={controls} makeDefault smoothTime={0.55} draggingSmoothTime={0.12} />
      <CameraDirector controls={controls} />
      <PanelAwareViewOffset />
      <Dust />
      <PeriodicTable3D names={names} />
      <ElementStage />
      <CompoundStage id={compoundId} structure={structure} />
      <RenderStats />
    </Canvas>
  );
}
