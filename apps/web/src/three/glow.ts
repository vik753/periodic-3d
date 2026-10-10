import * as THREE from 'three';

/**
 * Soft glowing points: camera-facing quads with a radial falloff, drawn additively.
 * Use with an InstancedMesh of `glowGeometry()`; each instance's matrix gives the
 * centre and size, setColorAt gives the colour. The shader turns the quads to face
 * the camera, so the glow looks round from every side. Not raycastable: pair it with
 * small spheres for picking.
 */
export function glowGeometry(): THREE.PlaneGeometry {
  return new THREE.PlaneGeometry(1, 1);
}

export function createGlowMaterial(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: { uOpacity: { value: 1 } },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      varying vec3 vColor;
      void main() {
        vUv = uv;
        #ifdef USE_INSTANCING_COLOR
          vColor = instanceColor;
        #else
          vColor = vec3(1.0);
        #endif
        vec4 center = modelViewMatrix * instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
        float scale = length(vec3(instanceMatrix[0][0], instanceMatrix[0][1], instanceMatrix[0][2]));
        center.xy += position.xy * scale;
        gl_Position = projectionMatrix * center;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uOpacity;
      varying vec2 vUv;
      varying vec3 vColor;
      void main() {
        float d = length(vUv - 0.5) * 2.0;
        if (d > 1.0) discard;
        float glow = pow(1.0 - d, 2.4);
        float core = 1.0 - smoothstep(0.12, 0.24, d);
        vec3 color = mix(vColor, vec3(1.0), core * 0.85);
        gl_FragColor = vec4(color, max(glow * 0.85, core) * uOpacity);
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    toneMapped: false,
  });
}
