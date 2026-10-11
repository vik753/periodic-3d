import { Html } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import * as THREE from 'three';

import { atomColor } from '../data/chemistry';
import type { Vec3 } from '../data/structure';
import { formatCount } from '../ui/format';
import { ClickGuard } from './ClickGuard';
import type { CompositionPart } from './composition';
import { partRadius, ringPositions, ringRadius } from './composition';
import { damp, prefersReducedMotion, useKeepRendering } from './useKeepRendering';

const FIT_EXTENT = 2.9;

interface CompositionViewProps {
  parts: CompositionPart[];
  position: Vec3;
  elementName?: (symbol: string) => string | undefined;
}

/**
 * Stand-in for compounds without a 3D model: one sphere per element, sized by the
 * number of its atoms in the formula. It shows composition, not geometry; the panel
 * says so (compound.noStructure).
 */
export function CompositionView({ parts, position, elementName }: CompositionViewProps) {
  const { i18n } = useTranslation();
  const groupRef = useRef<THREE.Group>(null);
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);
  const radii = useMemo(() => parts.map((part) => partRadius(part.count)), [parts]);
  const ring = useMemo(() => ringRadius(radii), [radii]);
  const positions = useMemo(() => ringPositions(parts.length, ring), [parts.length, ring]);
  // Same footprint as a fitted structure (StructureView FIT_RADIUS), so the camera fits both.
  const fit = Math.min(1, FIT_EXTENT / (ring + Math.max(...radii, 0)));
  const sphere = useMemo(() => new THREE.SphereGeometry(1, 32, 20), []);
  useKeepRendering(true);

  // A gentle sway around the vertical axis: labels stay under their spheres.
  const appear = useRef(0);
  const clock = useRef(0);
  useFrame((_, delta) => {
    const group = groupRef.current;
    if (!group) return;
    const dt = Math.min(delta, 0.05);
    appear.current = damp(appear.current, 1, 4, dt);
    group.scale.setScalar(0.3 + 0.7 * appear.current);
    if (reducedMotion) return;
    clock.current += dt;
    group.rotation.y = 0.35 * Math.sin(clock.current * 0.4);
  });

  return (
    <group position={position} scale={fit}>
      <group ref={groupRef}>
        <ClickGuard radius={ring + Math.max(...radii, 0) + 0.2} />
        {parts.map((part, index) => {
          const radius = radii[index] ?? partRadius(part.count);
          const at = positions[index] ?? [0, 0, 0];
          return (
            <group key={part.symbol} position={at}>
              <mesh geometry={sphere} scale={radius}>
                <meshStandardMaterial color={atomColor(part.symbol)} roughness={0.35} metalness={0.05} />
              </mesh>
              <Html
                position={[0, -radius - 0.25, 0]}
                center
                distanceFactor={9}
                zIndexRange={[15, 0]}
                pointerEvents="none"
              >
                <div className="pointer-events-none whitespace-nowrap rounded-full bg-panel/70 px-2.5 py-0.5 text-xs ring-1 ring-rim backdrop-blur-sm">
                  <span className="font-display font-semibold">{part.symbol}</span>
                  <span className="ml-1 tabular-nums">× {formatCount(part.count, i18n.language)}</span>
                  {elementName?.(part.symbol) ? (
                    <span className="ml-1.5 text-muted">{elementName(part.symbol)}</span>
                  ) : null}
                </div>
              </Html>
            </group>
          );
        })}
      </group>
    </group>
  );
}
