import { CameraControls } from '@react-three/drei';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import type { RefObject } from 'react';
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import * as THREE from 'three';

import type { CompoundSummary, Partner } from '../data/api';
import { pickName } from '../data/api';
import { demoCompound } from '../data/demo';
import { useCompound, useElement, useElements, usePair } from '../data/hooks';
import { elementBySymbol } from '../data/periodic';
import type { StructureData } from '../data/structure';
import { pairPath } from '../data/source';
import type { IndexEntry } from '../data/compoundIndex';
import { useAppStore } from '../state/store';
import { formulaOrder } from '../ui/format';
import { useCloud } from '../state/useCloud';
import type { ControlsRef } from './CameraDirector';
import { CAMERA_FOV, CameraDirector, cloudOverviewPose, SIDE_PANEL_MIN_WIDTH } from './CameraDirector';
import type { CloudLabel } from './CompoundCloud';
import type { CompositionPart } from './composition';
import { Dust } from './Dust';
import { backdropTable, CLOUD_CENTER, recededTable, STAGE_POSITION, TABLE_AT_REST, tilePosition } from './layout';
import { PeriodicTable3D } from './PeriodicTable3D';
import type { RayLabel } from './Rays';
import type { BeadLabel } from './RayWalk';
import { damp } from './useKeepRendering';

// Scene parts beyond the table load on demand: the first screen needs only the table.
const AtomModel = lazy(() => import('./AtomModel').then((module) => ({ default: module.AtomModel })));
const CompositionView = lazy(() => import('./CompositionView').then((module) => ({ default: module.CompositionView })));
const CompoundCloud = lazy(() => import('./CompoundCloud').then((module) => ({ default: module.CompoundCloud })));
const Rays = lazy(() => import('./Rays').then((module) => ({ default: module.Rays })));
const RayWalk = lazy(() => import('./RayWalk').then((module) => ({ default: module.RayWalk })));
const StructureView = lazy(() => import('./StructureView').then((module) => ({ default: module.StructureView })));

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

interface ElementWorldProps {
  controls: RefObject<ControlsRef | null>;
  names?: ReadonlyMap<number, string>;
  partners?: Partner[];
  /** 3D structure of the element's simple substance, if the dataset has one. */
  substance?: StructureData | null;
  labelFor: (partner: Partner) => RayLabel;
  /** Walk along a ray: the pair's compounds and the 3D model of the one in focus. */
  walk?: {
    compounds: CompoundSummary[];
    focusStructure: StructureData | null;
    labelFor: (compound: CompoundSummary) => BeadLabel;
  };
  /** Multi-element cloud: matching compounds, other elements in them, the one in focus. */
  cloud?: {
    entries: IndexEntry[];
    selected: number[];
    extras: ReadonlySet<number>;
    strongExtras: ReadonlySet<number>;
    focusStructure: StructureData | null;
    labelFor: (entry: IndexEntry) => CloudLabel;
  };
  elementName?: (symbol: string) => string | undefined;
}

/**
 * The table, and in the element scene the atom with its rays. Falling into an element
 * pushes the table far back; the rays then run from the atom to the partner tiles.
 */
function ElementWorld({ controls, names, partners, substance, labelFor, walk, cloud, elementName }: ElementWorldProps) {
  const scene = useAppStore((state) => state.scene);
  const elementView = useAppStore((state) => state.elementView);
  const size = useThree((state) => state.size);
  const cell = scene.kind === 'element' ? elementBySymbol(scene.symbol) : undefined;
  const partnerSymbol = scene.kind === 'element' ? scene.partner : undefined;
  const width = size.width;
  const height = size.height;
  const setScene = scene.kind === 'set';
  const transform = useMemo(() => {
    if (cell) return recededTable(cell, { width, height }, CAMERA_FOV);
    if (setScene) {
      const pose = cloudOverviewPose(width, height);
      return backdropTable({ width, height }, CAMERA_FOV, pose.position[2] - CLOUD_CENTER[2]);
    }
    return TABLE_AT_REST;
  }, [cell, setScene, width, height]);
  const origin = useMemo(() => (cell ? tilePosition(cell) : null), [cell]);
  const partnerSet = useMemo(() => new Set((cell && partners ? partners : []).map((partner) => partner.z)), [cell, partners]);
  const activeZ = partnerSymbol ? (elementBySymbol(partnerSymbol)?.z ?? null) : null;
  const activePartner = partners?.find((partner) => partner.z === activeZ);

  return (
    <>
      <PeriodicTable3D
        names={names}
        transform={transform}
        partners={partnerSet}
        extras={cloud?.extras}
        strongExtras={cloud?.strongExtras}
      />
      <Suspense fallback={null}>
        {scene.kind === 'set' && cloud && cloud.entries.length > 0 && (
          <CompoundCloud
            key={scene.symbols.join('-')}
            controls={controls}
            entries={cloud.entries}
            selected={cloud.selected}
            focusStructure={cloud.focusStructure}
            labelFor={cloud.labelFor}
            elementName={elementName}
          />
        )}
        {/* The atom steps aside during a walk: the camera travels right past it. */}
        {cell && origin && !activePartner && (elementView === 'atom' || !substance) && (
          <AtomModel key={cell.z} z={cell.z} position={origin} />
        )}
        {cell && origin && !activePartner && elementView === 'substance' && substance && (
          <StructureView key={`substance-${cell.symbol}`} data={substance} position={origin} fitRadius={1.7} elementName={elementName} />
        )}
        {cell && origin && partners && partners.length > 0 && (
          <Rays
            key={`${cell.symbol}-${width}x${height}`}
            origin={origin}
            focusSymbol={cell.symbol}
            partners={partners}
            transform={transform}
            labelFor={labelFor}
            activeZ={activeZ}
          />
        )}
        {cell && origin && activePartner && walk && (
          <RayWalk
            key={`${cell.symbol}-${activePartner.symbol}-${width}x${height}`}
            controls={controls}
            origin={origin}
            transform={transform}
            partner={activePartner}
            compounds={walk.compounds}
            focusStructure={walk.focusStructure}
            labelFor={walk.labelFor}
            elementName={elementName}
          />
        )}
      </Suspense>
    </>
  );
}

interface CompoundStageProps {
  id: string | null;
  structure: StructureData | null;
  /** Composition for compounds without a 3D model (proteins, alloys, mixtures). */
  parts: CompositionPart[] | null;
  elementName?: (symbol: string) => string | undefined;
}

function CompoundStage({ id, structure, parts, elementName }: CompoundStageProps) {
  if (!id) return null;
  if (structure) {
    return (
      <Suspense fallback={null}>
        <StructureView key={id} data={structure} position={STAGE_POSITION} elementName={elementName} elementLabels />
      </Suspense>
    );
  }
  if (!parts || parts.length === 0) return null;
  return (
    <Suspense fallback={null}>
      <CompositionView key={id} parts={parts} position={STAGE_POSITION} elementName={elementName} />
    </Suspense>
  );
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
      : size.width >= SIDE_PANEL_MIN_WIDTH
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
  const { t, i18n } = useTranslation();

  // Data hooks run here, outside the Canvas, and reach the 3D tree as props.
  const elements = useElements();
  const names = useMemo(
    () =>
      elements.data
        ? new Map(elements.data.elements.map((element) => [element.z, pickName(element.names, i18n.language)] as const))
        : undefined,
    [elements.data, i18n.language],
  );
  const elementName = useMemo(() => {
    const bySymbol = new Map(
      elements.data?.elements.map((element) => [element.symbol, pickName(element.names, i18n.language)] as const) ?? [],
    );
    return (symbol: string) => bySymbol.get(symbol);
  }, [elements.data, i18n.language]);
  const scene = useAppStore((state) => state.scene);
  const element = useElement(scene.kind === 'element' ? scene.symbol : null);
  const labelFor = useCallback(
    (partner: Partner): RayLabel => ({
      title: [partner.symbol, elementName(partner.symbol)].filter(Boolean).join(' '),
      subtitle: t('rays.compounds', { count: partner.count }),
    }),
    [elementName, t],
  );
  // Walk along a ray: the pair and the compound in focus.
  const walkCell = scene.kind === 'element' && scene.partner ? elementBySymbol(scene.symbol) : undefined;
  const walkPartner = scene.kind === 'element' && scene.partner ? elementBySymbol(scene.partner) : undefined;
  const pair = usePair(walkCell && walkPartner ? pairPath(walkCell, walkPartner) : null);
  const walkIndex = useAppStore((state) => state.walkIndex);
  const focusId = pair.data?.compounds[walkIndex]?.id ?? null;
  const focusCompound = useCompound(focusId);
  const beadLabel = useCallback(
    (item: CompoundSummary): BeadLabel => ({ formula: item.formula, name: pickName(item.names, i18n.language) }),
    [i18n.language],
  );
  const walk = useMemo(
    () =>
      pair.data
        ? { compounds: pair.data.compounds, focusStructure: focusCompound.data?.structure ?? null, labelFor: beadLabel }
        : undefined,
    [pair.data, focusCompound.data, beadLabel],
  );

  // Multi-element cloud.
  const cloudState = useCloud();
  const cloudHover = useAppStore((state) => state.cloudHover);
  const cloudFocus = useAppStore((state) => state.cloudFocus);
  const cloudFocusCompound = useCompound(scene.kind === 'set' ? cloudFocus : null);
  const cloudLabel = useCallback(
    (entry: IndexEntry): CloudLabel => ({ formula: entry.formula, name: pickName(entry.names, i18n.language) }),
    [i18n.language],
  );
  const cloud = useMemo(() => {
    const result = cloudState.result;
    if (scene.kind !== 'set' || !result) return undefined;
    const hovered = result.items.find((entry) => entry.id === (cloudHover ?? cloudFocus));
    return {
      entries: result.items,
      selected: cloudState.zs,
      extras: new Set(result.extras.keys()),
      strongExtras: new Set(hovered ? hovered.zs.filter((z) => !cloudState.zs.includes(z)) : []),
      focusStructure: cloudFocusCompound.data?.structure ?? null,
      labelFor: cloudLabel,
    };
  }, [scene.kind, cloudState.result, cloudState.zs, cloudHover, cloudFocus, cloudFocusCompound.data, cloudLabel]);

  const compoundId = scene.kind === 'compound' ? scene.id : null;
  const compound = useCompound(compoundId);
  const structure = compoundId ? (demoCompound(compoundId)?.structure ?? compound.data?.structure ?? null) : null;
  const parts = useMemo(() => {
    const data = compound.data;
    if (!data || data.structure) return null;
    return formulaOrder(data.formula, data.elements).map((symbol) => ({ symbol, count: data.composition[symbol] ?? 0 }));
  }, [compound.data]);

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
      <ElementWorld
        controls={controls}
        names={names}
        partners={element.data?.partners}
        substance={element.data?.substance?.structure ?? null}
        labelFor={labelFor}
        walk={walk}
        cloud={cloud}
        elementName={elementName}
      />
      <CompoundStage id={compoundId} structure={structure} parts={parts} elementName={elementName} />
      <RenderStats />
    </Canvas>
  );
}
