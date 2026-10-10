import { Html } from '@react-three/drei';
import type { ThreeEvent } from '@react-three/fiber';
import { useFrame } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

import type { Partner } from '../data/api';
import { elementByZ } from '../data/periodic';
import type { Vec3 } from '../data/structure';
import { useAppStore } from '../state/store';
import { RAY_COLOR } from './colors';
import type { TableTransform } from './layout';
import { tileWorldPosition } from './layout';
import { damp, prefersReducedMotion, useKeepRendering } from './useKeepRendering';

const MAX_RAYS = 48;
const SEGMENTS = 72;
const RADIAL = 6;
const HIT_RADIUS = 0.16;
/** The rays start growing once the table has moved back. */
const GROW_DELAY_S = 0.45;

export interface RayCurve {
  z: number;
  symbol: string;
  count: number;
  /** 0…1: share of the strongest partner on a log scale; sets thickness and brightness. */
  weight: number;
  curve: THREE.QuadraticBezierCurve3;
}

/**
 * One gently curved ray per partner: from the atom to the partner's tile on the
 * receded table. The bend turns the same way for all rays, like a slow spiral.
 */
export function buildRayCurves(origin: Vec3, partners: Partner[], transform: TableTransform): RayCurve[] {
  const start = new THREE.Vector3(...origin);
  const strongest = Math.max(1, ...partners.map((partner) => partner.count));
  const curves: RayCurve[] = [];
  for (const partner of partners.slice(0, MAX_RAYS)) {
    const cell = elementByZ(partner.z);
    if (!cell) continue;
    const end = new THREE.Vector3(...tileWorldPosition(cell, transform));
    const direction = end.clone().sub(start);
    const length = direction.length();
    if (length < 1e-3) continue;
    const side = new THREE.Vector3(0, 0, 1).cross(direction);
    if (side.lengthSq() < 1e-6) side.set(1, 0, 0);
    side.normalize();
    const control = start.clone().lerp(end, 0.45).addScaledVector(side, length * 0.07);
    const from = start.clone().addScaledVector(direction.normalize(), 0.12);
    curves.push({
      z: partner.z,
      symbol: partner.symbol,
      count: partner.count,
      weight: Math.log1p(partner.count) / Math.log1p(strongest),
      curve: new THREE.QuadraticBezierCurve3(from, control, end),
    });
  }
  return curves;
}

function rayGeometry(curves: RayCurve[], radius: (ray: RayCurve) => number, segments: number): THREE.BufferGeometry | null {
  if (curves.length === 0) return null;
  const parts = curves.map((ray, index) => {
    const tube = new THREE.TubeGeometry(ray.curve, segments, radius(ray), RADIAL, false);
    const vertices = tube.getAttribute('position').count;
    tube.setAttribute('aRay', new THREE.Float32BufferAttribute(new Float32Array(vertices).fill(index), 1));
    tube.setAttribute('aWeight', new THREE.Float32BufferAttribute(new Float32Array(vertices).fill(ray.weight), 1));
    return tube;
  });
  const merged = mergeGeometries(parts);
  parts.forEach((part) => part.dispose());
  return merged;
}

/**
 * Two passes share one geometry: a bright core and a wide, faint halo (the vertex shader
 * pushes the halo out along the normals). Together they read as a beam of light.
 */
function createRayMaterial(halo: boolean): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uGrow: { value: 0 },
      uHover: { value: -1 },
      uColor: { value: new THREE.Color(RAY_COLOR) },
      uOpacity: { value: 1 },
      uExpand: { value: halo ? 0.075 : 0 },
      uHalo: { value: halo ? 1 : 0 },
    },
    vertexShader: /* glsl */ `
      attribute float aRay;
      attribute float aWeight;
      uniform float uExpand;
      varying vec2 vUv;
      varying float vRay;
      varying float vWeight;
      varying float vFacing;
      varying float vDepth;
      void main() {
        vUv = uv;
        vRay = aRay;
        vWeight = aWeight;
        vec3 expanded = position + normal * uExpand * (0.45 + 0.55 * aWeight);
        vec4 mvPosition = modelViewMatrix * vec4(expanded, 1.0);
        vDepth = -mvPosition.z;
        vec3 viewNormal = normalize(normalMatrix * normal);
        vFacing = abs(dot(viewNormal, normalize(-mvPosition.xyz)));
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uTime;
      uniform float uGrow;
      uniform float uHover;
      uniform vec3 uColor;
      uniform float uOpacity;
      uniform float uHalo;
      varying vec2 vUv;
      varying float vRay;
      varying float vWeight;
      varying float vFacing;
      varying float vDepth;
      void main() {
        float along = vUv.x;
        if (along > uGrow) discard;
        // Bright core where the tube faces the viewer, soft edges: reads as light, not plastic.
        float core = pow(vFacing, 1.6);
        // Pulses flow from the atom towards the partner.
        float wave = 0.5 + 0.5 * sin(along * 28.0 - uTime * 3.0 + vRay * 1.7);
        float pulse = smoothstep(0.6, 1.0, wave);
        float hovered = 1.0 - step(0.5, abs(vRay - uHover));
        float someoneHovered = step(-0.5, uHover);
        float strength = mix(0.45, 1.15, vWeight) * mix(1.0, mix(0.28, 1.6, hovered), someoneHovered);
        float front = 1.0 - smoothstep(uGrow - 0.05, uGrow, along);
        float base = smoothstep(0.0, 0.05, along);
        float shape = uHalo > 0.5 ? 0.34 * pow(vFacing, 2.0) : 0.75 + 0.25 * core;
        // Fade the part of a ray that passes right by the camera (walk view).
        float near = smoothstep(0.9, 2.8, vDepth);
        float alpha = shape * (0.72 + 0.28 * pulse) * strength * base * max(front, 0.35) * near * uOpacity;
        vec3 hot = vec3(1.0, 0.9, 0.9);
        float heat = uHalo > 0.5 ? 0.0 : pow(core, 3.0) * (0.55 + 0.45 * pulse);
        vec3 color = mix(uColor * (uHalo > 0.5 ? 1.0 : 1.8), hot, heat);
        gl_FragColor = vec4(color, clamp(alpha, 0.0, 1.0));
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    toneMapped: false,
  });
}

export interface RayLabel {
  title: string;
  subtitle: string;
}

interface RaysProps {
  origin: Vec3;
  focusSymbol: string;
  partners: Partner[];
  transform: TableTransform;
  /** Text for the hover label of each partner (built outside the canvas, where i18n lives). */
  labelFor: (partner: Partner) => RayLabel;
  /** The ray of the walk (if any) stays bright; the others fade. */
  activeZ?: number | null;
}

export function Rays({ origin, focusSymbol, partners, transform, labelFor, activeZ = null }: RaysProps) {
  const curves = useMemo(() => buildRayCurves(origin, partners, transform), [origin, partners, transform]);
  const geometry = useMemo(() => rayGeometry(curves, (ray) => 0.01 + 0.032 * ray.weight, SEGMENTS), [curves]);
  const hitGeometry = useMemo(() => rayGeometry(curves, () => HIT_RADIUS, 24), [curves]);
  const material = useMemo(() => createRayMaterial(false), []);
  const haloMaterial = useMemo(() => createRayMaterial(true), []);
  const hitMaterial = useMemo(() => new THREE.MeshBasicMaterial({ visible: false }), []);
  const hoveredPartner = useAppStore((state) => state.hoveredPartner);
  const setHoveredPartner = useAppStore((state) => state.setHoveredPartner);
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);
  const age = useRef(0);
  useKeepRendering(true);

  useEffect(
    () => () => {
      geometry?.dispose();
      hitGeometry?.dispose();
    },
    [geometry, hitGeometry],
  );
  useEffect(
    () => () => {
      material.dispose();
      haloMaterial.dispose();
    },
    [material, haloMaterial],
  );
  useEffect(() => () => setHoveredPartner(null), [setHoveredPartner]);

  const highlighted = activeZ ?? hoveredPartner;
  const highlightedIndex = curves.findIndex((ray) => ray.z === highlighted);

  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.05);
    age.current += dt;
    const uniforms = material.uniforms;
    if (!reducedMotion) uniforms.uTime!.value += dt;
    const grow = reducedMotion ? 1.05 : age.current < GROW_DELAY_S ? 0 : damp(uniforms.uGrow!.value as number, 1.05, 2.6, dt);
    uniforms.uGrow!.value = grow;
    uniforms.uHover!.value = highlightedIndex;
    const halo = haloMaterial.uniforms;
    halo.uTime!.value = uniforms.uTime!.value;
    halo.uGrow!.value = grow;
    halo.uHover!.value = highlightedIndex;
  });

  const rayAt = (event: ThreeEvent<PointerEvent | MouseEvent>): RayCurve | undefined => {
    const index = event.face && hitGeometry ? hitGeometry.getAttribute('aRay').getX(event.face.a) : -1;
    return curves[Math.round(index)];
  };

  const onMove = (event: ThreeEvent<PointerEvent>) => {
    event.stopPropagation();
    const ray = rayAt(event);
    if (ray && ray.z !== hoveredPartner) setHoveredPartner(ray.z);
    document.body.style.cursor = 'pointer';
  };
  const onOut = () => {
    setHoveredPartner(null);
    document.body.style.cursor = 'auto';
  };
  const onClick = (event: ThreeEvent<MouseEvent>) => {
    if (event.delta > 6) return;
    event.stopPropagation();
    const ray = rayAt(event);
    if (ray) useAppStore.getState().navigate(`/e/${focusSymbol}/${ray.symbol}`);
  };

  const hovered = curves[highlightedIndex];
  const label = hovered ? labelFor({ z: hovered.z, symbol: hovered.symbol, count: hovered.count }) : null;
  const labelPosition = hovered ? hovered.curve.getPoint(0.97) : null;

  if (!geometry || !hitGeometry) return null;
  return (
    <group>
      <mesh geometry={geometry} material={haloMaterial} renderOrder={2} raycast={() => null} frustumCulled={false} />
      <mesh geometry={geometry} material={material} renderOrder={3} raycast={() => null} frustumCulled={false} />
      <mesh geometry={hitGeometry} material={hitMaterial} onPointerMove={onMove} onPointerOut={onOut} onClick={onClick} />
      {/* Always mounted, hidden when idle: mounting DOM portals on every hover is fragile. */}
      <Html
        position={labelPosition ?? [0, 0, 0]}
        center
        zIndexRange={[20, 0]}
        style={{ pointerEvents: 'none', visibility: label && activeZ == null ? 'visible' : 'hidden' }}
      >
        <div className="whitespace-nowrap rounded-xl bg-panel px-3 py-1.5 text-center ring-1 ring-ray/50 backdrop-blur-md">
          <div className="font-display text-sm font-semibold text-text">{label?.title}</div>
          <div className="text-xs text-muted">{label?.subtitle}</div>
        </div>
      </Html>
    </group>
  );
}
