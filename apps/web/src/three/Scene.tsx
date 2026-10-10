import { CameraControls } from '@react-three/drei';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

import { demoCompound } from '../data/demo';
import { elementBySymbol } from '../data/periodic';
import { useAppStore } from '../state/store';
import { AtomModel } from './AtomModel';
import type { ControlsRef } from './CameraDirector';
import { CAMERA_FOV, CameraDirector } from './CameraDirector';
import { Dust } from './Dust';
import { STAGE_POSITION, tilePosition } from './layout';
import { PeriodicTable3D } from './PeriodicTable3D';
import { StructureView } from './StructureView';

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

function CompoundStage() {
  const scene = useAppStore((state) => state.scene);
  if (scene.kind !== 'compound') return null;
  const compound = demoCompound(scene.id);
  if (!compound) return null;
  return <StructureView key={compound.id} data={compound.structure} position={STAGE_POSITION} />;
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
      <Dust />
      <PeriodicTable3D />
      <ElementStage />
      <CompoundStage />
      <RenderStats />
    </Canvas>
  );
}
