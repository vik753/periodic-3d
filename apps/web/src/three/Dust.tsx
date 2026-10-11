import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

import { isTouchFirst } from '../lib/device';
import { useAppStore } from '../state/store';
import { framePacing } from './quality';
import { damp, prefersReducedMotion } from './useKeepRendering';

/** Background frames for the drifting dust: 30 per second is smooth for slow motion. */
const DUST_FPS = 30;
/** The dust lives behind the table: from just behind the tiles to deep space. */
const NEAR_Z = -4;
const FAR_Z = -58;
const WIDTH = 130;
const HEIGHT = 76;

/**
 * Cosmic dust behind the table on the home screen. Particles rise slowly and sway, the
 * near ones faster than the far ones (parallax), so the table seems to hover in space.
 * A few golden specks and a gentle twinkle keep it alive. Other scenes fade it out.
 *
 * All motion runs in the vertex shader; the CPU updates three uniforms per frame. The
 * canvas renders on demand, so the dust asks for 30 frames per second while it shows
 * (framePacing tells the quality controller these frames are paced, not slow).
 */
export function Dust() {
  const active = useAppStore((state) => state.scene.kind === 'table');
  const invalidate = useThree((state) => state.invalidate);
  const gl = useThree((state) => state.gl);
  const pointsRef = useRef<THREE.Points>(null);
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);
  const count = useMemo(() => (isTouchFirst() ? 380 : 700), []);

  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const seeds = new Float32Array(count);
    const sizes = new Float32Array(count);
    // Deterministic pseudo-random layout so screenshots are stable.
    let seed = 7;
    const random = () => {
      seed = (seed * 16807) % 2147483647;
      return seed / 2147483647;
    };
    for (let i = 0; i < count; i += 1) {
      positions[i * 3] = (random() - 0.5) * WIDTH;
      positions[i * 3 + 1] = (random() - 0.5) * HEIGHT;
      // More particles far away: the sky looks deep, the space near the table stays clear.
      positions[i * 3 + 2] = NEAR_Z + (FAR_Z - NEAR_Z) * Math.sqrt(random());
      seeds[i] = random();
      // Mostly fine dust, a few larger motes.
      sizes[i] = 1.1 + Math.pow(random(), 3) * 3.4;
    }
    const result = new THREE.BufferGeometry();
    result.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    result.setAttribute('aSeed', new THREE.BufferAttribute(seeds, 1));
    result.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1));
    return result;
  }, [count]);

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: {
          uTime: { value: 0 },
          uFade: { value: 1 },
          uHeight: { value: HEIGHT },
          uPixelRatio: { value: 1 },
          uCool: { value: new THREE.Color('#a9bcff') },
          uWarm: { value: new THREE.Color('#ffd27a') },
        },
        vertexShader: /* glsl */ `
          attribute float aSeed;
          attribute float aSize;
          uniform float uTime;
          uniform float uFade;
          uniform float uHeight;
          uniform float uPixelRatio;
          varying float vAlpha;
          varying float vWarm;
          void main() {
            vec3 p = position;
            // 0 next to the table, 1 in deep space.
            float depth = clamp((${(-NEAR_Z).toFixed(1)} - p.z) / ${(NEAR_Z - FAR_Z).toFixed(1)}, 0.0, 1.0);
            float rise = uTime * mix(0.55, 0.16, depth) * (0.6 + aSeed * 0.8);
            float wrapped = mod(p.y + rise + uHeight * 0.5, uHeight);
            p.y = wrapped - uHeight * 0.5;
            p.x += sin(uTime * 0.19 + aSeed * 41.0) * (0.6 + aSeed) + sin(uTime * 0.06 + aSeed * 13.0) * 1.4;
            p.z += sin(uTime * 0.15 + aSeed * 29.0) * 0.6;
            vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
            // Sizes in CSS pixels: 2–4 px motes next to the table, specks in deep space.
            gl_PointSize = max(aSize * (115.0 / max(-mvPosition.z, 1.0)), 1.4) * uPixelRatio;
            gl_Position = projectionMatrix * mvPosition;
            // Fade at the top and bottom of the loop so no mote pops in or out.
            float edge = wrapped / uHeight;
            float loopFade = smoothstep(0.0, 0.08, edge) * smoothstep(1.0, 0.92, edge);
            float twinkle = 0.72 + 0.28 * sin(uTime * (0.7 + aSeed * 1.9) + aSeed * 61.0);
            vAlpha = uFade * loopFade * twinkle * mix(0.9, 0.5, depth);
            vWarm = step(0.94, aSeed);
          }
        `,
        fragmentShader: /* glsl */ `
          uniform vec3 uCool;
          uniform vec3 uWarm;
          varying float vAlpha;
          varying float vWarm;
          void main() {
            float d = length(gl_PointCoord - 0.5);
            // Soft halo with a brighter core.
            float alpha = (smoothstep(0.5, 0.0, d) * 0.55 + smoothstep(0.14, 0.0, d) * 0.45) * vAlpha;
            gl_FragColor = vec4(mix(uCool, uWarm, vWarm), alpha);
            #include <colorspace_fragment>
          }
        `,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    [],
  );

  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => () => material.dispose(), [material]);

  // While the table shows, ask for frames at a steady 30 per second.
  useEffect(() => {
    invalidate();
    if (!active || reducedMotion) return;
    const interval = 1 / DUST_FPS;
    framePacing.interval = interval;
    const timer = window.setInterval(() => {
      if (!document.hidden) invalidate();
    }, interval * 1000);
    return () => {
      window.clearInterval(timer);
      if (framePacing.interval === interval) framePacing.interval = 0;
    };
  }, [active, reducedMotion, invalidate]);

  const time = useRef(0);
  const fade = useRef(active ? 1 : 0);
  useFrame((_, delta) => {
    const points = pointsRef.current;
    if (!points) return;
    const dt = Math.min(delta, 0.1); // no jump after idle time
    if (!reducedMotion && fade.current > 0.01) time.current += dt;
    const target = active ? 1 : 0;
    fade.current = damp(fade.current, target, active ? 2.2 : 5, dt);
    const settled = Math.abs(fade.current - target) < 0.01;
    if (settled) fade.current = target;
    else invalidate();
    material.uniforms.uTime!.value = time.current;
    material.uniforms.uFade!.value = fade.current;
    material.uniforms.uPixelRatio!.value = gl.getPixelRatio();
    points.visible = fade.current > 0;
  });

  return <points ref={pointsRef} geometry={geometry} material={material} frustumCulled={false} renderOrder={-1} />;
}
