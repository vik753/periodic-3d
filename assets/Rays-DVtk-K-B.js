import{a as n,j as c}from"./react-B7ulV_JK.js";import{H as D,V as H,J as B,K as I,X as S,Y as N,i as U,r as V,h as Y}from"./three-DVDdbfxe.js";import{c as A,p as k,u as L,h as X,t as K,R as $,d as q}from"./index-CuaAGVqC.js";import{a as J,H as Q}from"./r3f-BQlR8-_p.js";const Z=48,ee=72,te=6,oe=.16,ae=.45;function re(s,v,d){const l=new H(...s),g=Math.max(1,...v.map(t=>t.count)),r=[];for(const t of v.slice(0,Z)){const o=X(t.z);if(!o)continue;const a=new H(...K(o,d)),u=a.clone().sub(l),m=u.length();if(m<.001)continue;const f=new H(0,0,1).cross(u);f.lengthSq()<1e-6&&f.set(1,0,0),f.normalize();const x=l.clone().lerp(a,.45).addScaledVector(f,m*.07),h=l.clone().addScaledVector(u.normalize(),.12);r.push({z:t.z,symbol:t.symbol,count:t.count,weight:Math.log1p(t.count)/Math.log1p(g),curve:new B(h,x,a)})}return r}function j(s,v,d){if(s.length===0)return null;const l=s.map((r,t)=>{const o=new I(r.curve,d,v(r),te,!1),a=o.getAttribute("position").count;return o.setAttribute("aRay",new S(new Float32Array(a).fill(t),1)),o.setAttribute("aWeight",new S(new Float32Array(a).fill(r.weight),1)),o}),g=N(l);return l.forEach(r=>r.dispose()),g}function C(s){return new U({uniforms:{uTime:{value:0},uGrow:{value:0},uHover:{value:-1},uColor:{value:new Y($)},uOpacity:{value:1},uExpand:{value:s?.075:0},uHalo:{value:s?1:0}},vertexShader:`
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
    `,fragmentShader:`
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
    `,transparent:!0,depthWrite:!1,blending:V,toneMapped:!1})}function ue({origin:s,focusSymbol:v,partners:d,transform:l,labelFor:g,activeZ:r=null}){const t=n.useMemo(()=>re(s,d,l),[s,d,l]),o=n.useMemo(()=>j(t,e=>.01+.032*e.weight,ee),[t]),a=n.useMemo(()=>j(t,()=>oe,24),[t]),u=n.useMemo(()=>C(!1),[]),m=n.useMemo(()=>C(!0),[]),f=n.useMemo(()=>new D({visible:!1}),[]),x=A(e=>e.hoveredPartner),h=A(e=>e.setHoveredPartner),P=n.useMemo(()=>k(),[]),z=n.useRef(0);L(!0),n.useEffect(()=>()=>{o?.dispose(),a?.dispose()},[o,a]),n.useEffect(()=>()=>{u.dispose(),m.dispose()},[u,m]),n.useEffect(()=>()=>h(null),[h]);const F=r??x,w=t.findIndex(e=>e.z===F);J((e,i)=>{const M=Math.min(i,.05);z.current+=M;const y=u.uniforms;P||(y.uTime.value+=M);const E=P?1.05:z.current<ae?0:q(y.uGrow.value,1.05,2.6,M);y.uGrow.value=E,y.uHover.value=w;const R=m.uniforms;R.uTime.value=y.uTime.value,R.uGrow.value=E,R.uHover.value=w});const G=e=>{const i=e.face&&a?a.getAttribute("aRay").getX(e.face.a):-1;return t[Math.round(i)]},W=e=>{e.stopPropagation();const i=G(e);i&&i.z!==x&&h(i.z),document.body.style.cursor="pointer"},O=()=>{h(null),document.body.style.cursor="auto"},T=e=>{if(e.delta>6)return;e.stopPropagation();const i=G(e);i&&A.getState().navigate(`/e/${v}/${i.symbol}`)},p=t[w],b=p?g({z:p.z,symbol:p.symbol,count:p.count}):null,_=p?p.curve.getPoint(.97):null;return!o||!a?null:c.jsxs("group",{children:[c.jsx("mesh",{geometry:o,material:m,renderOrder:2,raycast:()=>null,frustumCulled:!1}),c.jsx("mesh",{geometry:o,material:u,renderOrder:3,raycast:()=>null,frustumCulled:!1}),c.jsx("mesh",{geometry:a,material:f,onPointerMove:W,onPointerOut:O,onClick:T}),c.jsx(Q,{position:_??[0,0,0],center:!0,zIndexRange:[20,0],style:{pointerEvents:"none",visibility:b&&r==null?"visible":"hidden"},children:c.jsxs("div",{className:"whitespace-nowrap rounded-xl bg-panel px-3 py-1.5 text-center ring-1 ring-ray/50 backdrop-blur-md",children:[c.jsx("div",{className:"font-display text-sm font-semibold text-text",children:b?.title}),c.jsx("div",{className:"text-xs text-muted",children:b?.subtitle})]})})]})}export{ue as Rays,re as buildRayCurves};
