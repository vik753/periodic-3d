import { useFrame } from '@react-three/fiber';
import { useMemo } from 'react';
import * as THREE from 'three';

/**
 * Faint particles drifting in Brownian-like motion around the scene.
 * All motion happens in the vertex shader; the CPU only updates one uniform.
 */
export function Dust({ count = 420 }: { count?: number }) {
  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const seeds = new Float32Array(count);
    // Deterministic pseudo-random layout so screenshots are stable.
    let seed = 7;
    const random = () => {
      seed = (seed * 16807) % 2147483647;
      return seed / 2147483647;
    };
    for (let i = 0; i < count; i += 1) {
      positions[i * 3] = (random() - 0.5) * 80;
      positions[i * 3 + 1] = (random() - 0.5) * 48;
      positions[i * 3 + 2] = -40 + random() * 52;
      seeds[i] = random();
    }
    const result = new THREE.BufferGeometry();
    result.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    result.setAttribute('aSeed', new THREE.BufferAttribute(seeds, 1));
    return result;
  }, [count]);

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: {
          uTime: { value: 0 },
          uColor: { value: new THREE.Color('#9fb3ff') },
        },
        vertexShader: /* glsl */ `
          attribute float aSeed;
          uniform float uTime;
          void main() {
            vec3 p = position;
            float t = uTime * 0.35;
            p.x += sin(t * 0.37 + aSeed * 41.0) * 0.7 + sin(t * 1.13 + aSeed * 17.0) * 0.25;
            p.y += cos(t * 0.29 + aSeed * 23.0) * 0.7 + cos(t * 0.97 + aSeed * 11.0) * 0.25;
            p.z += sin(t * 0.23 + aSeed * 29.0) * 0.7;
            vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
            gl_PointSize = (1.4 + aSeed * 2.2) * (38.0 / max(-mvPosition.z, 1.0));
            gl_Position = projectionMatrix * mvPosition;
          }
        `,
        fragmentShader: /* glsl */ `
          uniform vec3 uColor;
          void main() {
            float d = length(gl_PointCoord - 0.5);
            float alpha = smoothstep(0.5, 0.0, d) * 0.32;
            gl_FragColor = vec4(uColor, alpha);
            #include <colorspace_fragment>
          }
        `,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    [],
  );

  useFrame((state) => {
    material.uniforms.uTime!.value = state.clock.elapsedTime;
  });

  return <points geometry={geometry} material={material} frustumCulled={false} />;
}
