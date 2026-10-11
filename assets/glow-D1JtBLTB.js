import{x as e,i as o,r}from"./three-DVDdbfxe.js";function t(){return new e(1,1)}function i(){return new o({uniforms:{uOpacity:{value:1}},vertexShader:`
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
    `,fragmentShader:`
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
    `,transparent:!0,depthWrite:!1,blending:r,toneMapped:!1})}export{i as c,t as g};
