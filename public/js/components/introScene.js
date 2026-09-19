// PRIME.FINDS entrance -- "The Portal".
//
// One full-screen WebGL fragment shader, no dependencies. The whole
// sequence is a single timeline (T, in seconds) evaluated per pixel, so
// every layer can carry its own easing and its own job:
//
//   0.0 - 1.3   Darkness. A haze of warm, domain-warped light drifts in
//               from nothing; particles start streaming toward the centre.
//   0.7 - 3.0   A seed of light gathers at the centre with an anamorphic
//               streak; three chromatic light trails tighten around it.
//   1.3 - 2.75  The logo materialises out of noise: a dissolve front
//               travels outward from the mark, its edge burning, while
//               liquid displacement and chromatic aberration settle to
//               nothing. Volumetric rays stream from the finished shape.
//   2.55 - 3.1  A glint crosses the logo; it breathes in (anticipation).
//   3.1 - 4.3   The portal. A shockwave lenses the space, the camera
//               pushes through the logo, and an organic, iridescent-rimmed
//               aperture opens onto the REAL homepage underneath -- the
//               canvas is transparent inside the aperture, so the site is
//               revealed, not faded to.
//
// Gold stays the hero. Iridescence (thin-film hues) only ever appears in
// fringes -- ring edges, the portal rim, the dissolve burn -- never as a
// wash. Performance: transform-free full-screen pass, resolution scaled to
// a pixel budget (lower on phones), an adaptive drop if frames run long,
// a lite shader path (fewer octaves / taps / layers) for touch devices,
// and time driven by the clock rather than the frame count so slow
// devices finish on schedule instead of dragging the entrance out.

export const T_PORTAL = 2.95;
export const T_PORTAL_LEN = 1.45;
export const T_END = T_PORTAL + T_PORTAL_LEN + 0.12;
export const T_REVEAL = T_PORTAL + 0.15;
const QUICK_START = 0.9;
const QUICK_SPEED = 1.8;
const LOGO_ASPECT = 1075 / 580;

const VERT = `
attribute vec2 aPos;
void main(){ gl_Position = vec4(aPos, 0.0, 1.0); }
`;

const FRAG = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

uniform vec2 uRes;
uniform float uT;
uniform vec2 uMouse;
uniform float uPointer;
uniform sampler2D uLogo;
uniform vec2 uLogoSize;
uniform float uLite;

const float PI2 = 6.28318530718;
const float TP = ${T_PORTAL.toFixed(3)};
const float TPD = ${T_PORTAL_LEN.toFixed(3)};

float hash21(vec2 p){
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}
float vnoise(vec2 p){
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = hash21(i);
  float b = hash21(i + vec2(1.0, 0.0));
  float c = hash21(i + vec2(0.0, 1.0));
  float d = hash21(i + vec2(1.0, 1.0));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
float fbm(vec2 p){
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 4; i++) {
    if (uLite > 0.5 && i >= 2) break;
    v += a * vnoise(p);
    p = p * 2.03 + vec2(1.7, 9.2);
    a *= 0.5;
  }
  return v / (uLite > 0.5 ? 0.75 : 0.9375);
}
// Thin-film palette: gold-dominant, with rose / violet / teal only at the edges.
vec3 pal(float t){
  return vec3(0.62, 0.50, 0.32) + vec3(0.38, 0.34, 0.30) * cos(PI2 * (t + vec3(0.0, 0.10, 0.25)));
}
float eoC(float x){ x = clamp(x, 0.0, 1.0); return 1.0 - pow(1.0 - x, 3.0); }
float sq(float x){ return x * x; }

// Streaming particles in polar space: cells are indexed by (angle, radius),
// radius scrolls with time so they fall inward and stretch into streaks.
float particles(vec2 p, float layer, float Tw, vec2 par){
  vec2 pp = p - par * (0.4 + layer * 0.55);
  float rr = length(pp);
  float aa = atan(pp.y, pp.x);
  float N = 24.0 + layer * 20.0;
  float M = 5.0 + layer * 3.2;
  float ry = (rr + Tw * (0.045 + layer * 0.032)) * M;
  float cx = (aa / PI2 + 0.5) * N;
  vec2 id = vec2(floor(cx), floor(ry));
  vec2 f = vec2(fract(cx), fract(ry));
  float h = hash21(id + layer * 17.3);
  float h2 = hash21(id.yx + 3.7 + layer * 5.0);
  float present = step(0.88 - layer * 0.03, h);
  vec2 pos = vec2(0.2 + 0.6 * h2, 0.2 + 0.6 * fract(h * 7.13));
  vec2 dv = (f - pos) * vec2(PI2 * rr / N, 1.0 / M);
  float d = length(vec2(dv.x, dv.y * 0.32));
  float sz = (0.0016 + 0.0017 * h2) * (0.6 + layer * 0.55);
  float tw = 0.5 + 0.5 * sin(Tw * (2.0 + h * 4.0) + h * 40.0);
  // Energy gathers toward the mark: dense near it, thinning to nothing at the edges.
  float fade = smoothstep(0.03, 0.17, rr) * (1.0 - smoothstep(0.35, 1.05, rr));
  return present * (1.0 - smoothstep(0.0, sz, d)) * (0.4 + 0.6 * tw) * fade;
}

void main(){
  float aspect = uRes.x / uRes.y;
  float S = min(1.0, aspect * 1.25);
  vec2 uv = (gl_FragCoord.xy - 0.5 * uRes) / uRes.y / S;
  float T = uT;
  vec2 mp = uMouse * vec2(aspect * 0.5, 0.5) / S;
  vec2 par = uMouse * 0.03 * uPointer + vec2(sin(T * 0.37), cos(T * 0.29)) * 0.008;

  // Shockwave lensing: space is pulled toward the centre as the wave passes.
  float swR = (1.0 - pow(1.0 - clamp((T - TP) / 0.8, 0.0, 1.0), 2.0)) * 1.45;
  float swLife = 1.0 - clamp((T - TP) / 0.9, 0.0, 1.0);
  float r0 = length(uv);
  float bump = exp(-sq((r0 - swR) / 0.11)) * step(TP, T) * swLife;
  uv -= uv / (r0 + 1e-4) * bump * 0.05;

  float r = length(uv);
  float ang = atan(uv.y, uv.x);
  float pW = max(T - TP, 0.0);
  float Tw = T + pW * pW * 5.0;

  vec3 col = vec3(0.0235, 0.0235, 0.0275);

  // ---- 1. Atmosphere: warm volumetric haze, domain-warped, near-invisible at first.
  float atmo = smoothstep(0.15, 2.2, T) * (1.0 - smoothstep(TP + 0.1, TP + 1.0, T));
  vec2 q = uv * 1.45 - par * 0.7;
  float haze;
  if (uLite > 0.5) {
    haze = fbm(q + vec2(T * 0.04, 0.0));
  } else {
    vec2 w = vec2(fbm(q + vec2(T * 0.05, 0.0)), fbm(q + vec2(5.2, 1.3) - vec2(0.0, T * 0.04)));
    haze = fbm(q + 1.7 * (w - 0.5) + vec2(0.0, T * 0.02));
  }
  float shaft = pow(max(haze - 0.18, 0.0) / 0.76, 2.0);
  vec3 iri = pal(haze * 1.1 + ang * 0.09 + T * 0.05);
  col += mix(vec3(0.80, 0.62, 0.28), iri, 0.38) * shaft * exp(-r * 1.35) * 0.42 * atmo;

  // ---- 2. Seed of light + anamorphic streak (anticipation).
  float seed = smoothstep(0.7, 1.6, T) * (1.0 - smoothstep(2.3, 3.0, T));
  float core = (0.0011 / (r * r + 0.0011)) * seed;
  float hot = exp(-r * 70.0) * seed;
  float fl = smoothstep(1.0, 1.9, T) * (1.0 - smoothstep(2.5, 3.2, T));
  float streak = exp(-abs(uv.y) * (90.0 + 40.0 * (1.0 - fl))) * exp(-abs(uv.x) * 2.6) * fl;
  col += vec3(1.0, 0.80, 0.45) * (core * 0.9 + hot * 1.4) + vec3(1.0, 0.72, 0.34) * streak * 0.55;

  // ---- 3. Light trails: three arcs with comet tails, RGB split radially.
  float tr = smoothstep(0.6, 1.4, T) * (1.0 - smoothstep(TP - 0.15, TP + 0.3, T));
  if (tr > 0.002) {
    vec3 trails = vec3(0.0);
    for (int i = 0; i < 3; i++) {
      float fi = float(i);
      float rad = 0.16 + fi * 0.085 + 0.02 * sin(T * (0.7 + fi * 0.3) + fi * 2.0);
      float wob = 0.024 * (vnoise(vec2(ang * (2.0 + fi), T * (0.6 + 0.25 * fi) + fi * 10.0)) - 0.5);
      float gather = mix(1.35, 1.0, 1.0 - pow(1.0 - clamp((T - 0.6 - fi * 0.18) / 1.6, 0.0, 1.0), 3.0));
      float rr = (rad + wob) * gather;
      float dir = (mod(fi, 2.0) < 0.5) ? 1.0 : -1.0;
      float a = mod(ang - T * (0.9 - fi * 0.3) * dir - fi * 2.1, PI2);
      float tail = exp(-a * (1.6 + fi * 0.7));
      float w = 0.0011 + 0.0006 * fi;
      vec3 ringRGB = vec3(
        w / (abs(r - rr * 0.994) + 0.0016),
        w / (abs(r - rr) + 0.0016),
        w / (abs(r - rr * 1.006) + 0.0016)
      );
      trails += ringRGB * tail * vec3(0.98, 0.80, 0.44);
    }
    col += trails * 0.5 * tr;
  }

  // ---- 4. Particles: depth layers streaming inward, accelerating through the portal.
  float pa = smoothstep(0.65, 1.8, T) * (1.0 - smoothstep(TP + 0.5, TP + 1.1, T));
  if (pa > 0.002) {
    for (int k = 0; k < 3; k++) {
      if (uLite > 0.5 && k >= 2) break;
      float fk = float(k);
      float pv = particles(uv, fk, Tw, par);
      vec3 pc = mix(vec3(1.0, 0.83, 0.52), pal(fk * 0.31 + T * 0.1), 0.25);
      col += pc * pv * pa * (0.5 + 0.28 * fk);
    }
  }

  // ---- 5. The logo, materialising.
  float prog = clamp((T - 1.3) / 1.45, 0.0, 1.0);
  float pe = prog * prog * (3.0 - 2.0 * prog);
  float zoomP = clamp((T - (TP + 0.12)) / 1.2, 0.0, 1.0);
  float zoom = 1.0 + pow(zoomP, 3.0) * 20.0;
  float ant = smoothstep(TP - 0.32, TP, T) * (1.0 - smoothstep(TP, TP + 0.16, T));
  float sc = zoom * (1.0 - 0.04 * ant) * (1.0 + 0.010 * sin(T * 2.4) * smoothstep(2.4, 3.0, T));
  vec2 lp = (uv - par * 0.35) / (uLogoSize * sc);
  vec2 luv = lp + 0.5;
  float fadeOut = 1.0 - smoothstep(0.30, 0.80, zoomP);

  if (pe > 0.002 && fadeOut > 0.003 && abs(lp.x) < 1.7 && abs(lp.y) < 1.7) {
    float nz = fbm(luv * 5.5 + vec2(0.0, T * 0.12));
    float rd = length((luv - 0.5) * vec2(1.0, 1.55));
    float rv = 0.62 * (1.05 - rd * 1.15) + 0.38 * nz;
    float thr = 1.0 - pe * 1.28;
    float vis = smoothstep(thr, thr + 0.05, rv);
    float edge = smoothstep(thr - 0.035, thr + 0.005, rv) * (1.0 - smoothstep(thr + 0.005, thr + 0.13, rv));
    float loose = 1.0 - pe;

    vec2 dsp = vec2(fbm(luv * 4.0 + vec2(T * 0.32, 0.0)), fbm(luv * 4.0 + vec2(7.3, T * 0.27))) - 0.5;
    dsp *= loose * 0.09 + 0.004;
    vec2 cdir = luv - 0.5;
    cdir /= (length(cdir) + 1e-3);
    vec2 ca = cdir * (loose * 0.011 + 0.0022);
    vec4 tR = texture2D(uLogo, luv + dsp + ca);
    vec4 tG = texture2D(uLogo, luv + dsp);
    vec4 tB = texture2D(uLogo, luv + dsp - ca);
    vec3 lc = vec3(tR.r, tG.g, tB.b);
    float lA = max(tG.a, max(tR.a, tB.a));

    float bright = (0.30 + 0.70 * pe) * (1.0 + 0.55 * ant);
    bright *= 1.0 + 0.28 * exp(-length(uv - mp) * 2.6) * uPointer;

    float sp = mix(-0.5, 1.5, eoC((T - 2.3) / 0.75));
    float gl = exp(-sq((luv.x + luv.y * 0.3 - sp) * 8.0)) * step(2.25, T) * (1.0 - step(3.15, T));
    lc += vec3(1.0, 0.9, 0.65) * gl * tG.a * 0.9;
    vec3 hotc = mix(vec3(1.0, 0.78, 0.42), pal(nz * 1.6 + T * 0.4), 0.45);
    lc += hotc * edge * tG.a * 2.4;

    float lv = vis * fadeOut;
    col = col * (1.0 - lA * lv) + lc * bright * lv;

    float rayAmt = pe * pe * (1.0 - smoothstep(0.35, 0.9, zoomP));
    if (rayAmt > 0.003) {
      float raySteps = uLite > 0.5 ? 6.0 : 14.0;
      vec2 dv = (vec2(0.5) - luv) * 0.85;
      float acc = 0.0;
      float wg = 1.0;
      // Per-pixel jitter turns the discrete tap spacing into fine grain
      // instead of visible ghost copies of the wordmark.
      float jit = hash21(gl_FragCoord.xy + 7.7);
      for (int i = 0; i < 14; i++) {
        if (float(i) >= raySteps) break;
        acc += texture2D(uLogo, luv + dv * ((float(i) + jit) / raySteps)).a * wg;
        wg *= 0.9;
      }
      col += vec3(1.0, 0.78, 0.42) * acc * (uLite > 0.5 ? 0.16 : 0.075) * rayAmt * exp(-r * 1.3);
    }

    float gacc = 0.0;
    float gj = hash21(gl_FragCoord.xy + 31.1);
    for (int j = 0; j < 8; j++) {
      if (uLite > 0.5 && j >= 4) break;
      float a = (float(j) + gj) * 0.785398;
      gacc += texture2D(uLogo, luv + vec2(cos(a), sin(a)) * (0.045 + 0.05 * gj)).a;
    }
    col += vec3(0.95, 0.70, 0.32) * (gacc / (uLite > 0.5 ? 4.0 : 8.0)) * 0.55 * pe * fadeOut * (1.0 - lA * lv);
  }

  // ---- 6. The portal: an organic aperture, iridescent rim, echoing rings.
  float blob = 1.0 + 0.11 * (vnoise(vec2(ang * 2.2 + 1.7, T * 0.9)) - 0.5) + 0.04 * (vnoise(vec2(ang * 4.3, -T * 1.1)) - 0.5);
  float pr = pow(max(0.0, (T - (TP + 0.20)) / 1.20), 1.75) * 1.95 * blob - 0.05;
  float dH = r - pr;
  float opaque = smoothstep(-0.004, 0.022, dH);
  float pIn = smoothstep(TP + 0.18, TP + 0.5, T);
  float rimI = pIn * (1.0 - smoothstep(0.72, 1.0, (T - TP) / TPD));
  float flick = 0.65 + 0.7 * vnoise(vec2(ang * 7.0, T * 9.0));
  vec3 rimRGB = vec3(
    exp(-sq((dH + 0.008) / 0.026)),
    exp(-sq(dH / 0.026)),
    exp(-sq((dH - 0.008) / 0.026))
  );
  vec3 rimTint = mix(vec3(1.0, 0.84, 0.52), pal(ang * 0.32 + T * 0.7 + r * 1.6), 0.55);
  vec3 add = rimRGB * rimTint * flick * rimI * 1.25;
  // Prismatic echoes trailing the aperture: a fine cascade of thin-film hues.
  for (int k = 1; k < 6; k++) {
    float fk = float(k);
    float dk = r - (pr - 0.058 * fk * (1.0 + 0.15 * blob));
    add += vec3(exp(-sq(dk / 0.011))) * pal(fk * 0.19 + T * 0.45 + ang * 0.05) * rimI * (0.55 / (fk * 0.8 + 0.2)) * pIn;
  }
  float swd = r - swR * blob;
  add += vec3(1.0, 0.85, 0.55) * exp(-swd * swd * 1400.0) * swLife * step(TP, T) * 0.9;

  // ---- 7. Finish: vignette, grain, premultiplied output.
  vec2 vv = uv / vec2(0.5 * aspect / S, 0.5 / S);
  col *= mix(0.6, 1.0, 1.0 - smoothstep(0.3, 1.45, length(vv)));
  vec3 outc = col * opaque + add;
  float outA = clamp(opaque + max(add.r, max(add.g, add.b)) * 0.85, 0.0, 1.0);
  float g = hash21(gl_FragCoord.xy + fract(T * 13.7) * 97.3);
  outc += (g - 0.5) * 0.03 * outA;
  gl_FragColor = vec4(outc, outA);
}
`;

function compile(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(s);
    gl.deleteShader(s);
    throw new Error('shader compile failed: ' + log);
  }
  return s;
}

function loadImage(url, timeoutMs) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const timer = setTimeout(() => reject(new Error('logo timeout')), timeoutMs);
    img.onload = () => { clearTimeout(timer); resolve(img); };
    img.onerror = () => { clearTimeout(timer); reject(new Error('logo failed')); };
    img.src = url;
  });
}

/**
 * Builds the scene. Throws if WebGL, the shader, or the logo texture is
 * unavailable -- the caller falls back to the CSS entrance in that case.
 */
export async function createIntroScene({ canvas, logoUrl, quick, lite, debugT, onReveal, onDone }) {
  const gl = canvas.getContext('webgl', {
    alpha: true,
    premultipliedAlpha: true,
    antialias: false,
    depth: false,
    stencil: false,
    powerPreference: 'high-performance',
  });
  if (!gl) throw new Error('no webgl');
  const hp = gl.getShaderPrecisionFormat(gl.FRAGMENT_SHADER, gl.HIGH_FLOAT);
  if (!hp || hp.precision === 0) throw new Error('no highp');

  const prog = gl.createProgram();
  gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VERT));
  gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, FRAG));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error('link failed');
  gl.useProgram(prog);

  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, 'aPos');
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

  const img = await loadImage(logoUrl, 2500);
  const tex = gl.createTexture();
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

  const u = {};
  ['uRes', 'uT', 'uMouse', 'uPointer', 'uLogo', 'uLogoSize', 'uLite'].forEach((n) => { u[n] = gl.getUniformLocation(prog, n); });
  gl.uniform1i(u.uLogo, 0);
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  gl.clearColor(0, 0, 0, 0);

  let liteMode = !!lite;
  let renderScale = 1;
  let budget = liteMode ? 0.7e6 : 2.1e6;
  let cssW = 0;
  let cssH = 0;
  const dpr = Math.min(window.devicePixelRatio || 1, 3);

  const resize = () => {
    cssW = canvas.clientWidth || window.innerWidth;
    cssH = canvas.clientHeight || window.innerHeight;
    const fit = Math.sqrt(budget / Math.max(1, cssW * cssH));
    const scale = Math.max(0.4, Math.min(dpr, fit)) * renderScale;
    const w = Math.max(2, Math.round(cssW * scale));
    const h = Math.max(2, Math.round(cssH * scale));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    gl.viewport(0, 0, w, h);
    const aspect = w / h;
    const S = Math.min(1, aspect * 1.25);
    const sceneAspect = aspect / S;
    const logoW = Math.min(0.64, 0.8 * sceneAspect);
    gl.uniform2f(u.uRes, w, h);
    gl.uniform2f(u.uLogoSize, logoW, logoW / LOGO_ASPECT);
  };
  resize();

  // Cursor light / parallax: fine pointers only, smoothed, very subtle.
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  const target = { x: 0, y: 0 };
  const mouse = { x: 0, y: 0 };
  const onMove = (e) => {
    target.x = (e.clientX / window.innerWidth) * 2 - 1;
    target.y = -((e.clientY / window.innerHeight) * 2 - 1);
  };
  if (finePointer) window.addEventListener('pointermove', onMove, { passive: true });
  gl.uniform1f(u.uPointer, finePointer ? 1 : 0);
  gl.uniform1f(u.uLite, liteMode ? 1 : 0);

  let T = quick ? QUICK_START : 0;
  const speed = quick ? QUICK_SPEED : 1;
  let boost = 1;
  let raf = 0;
  let last = 0;
  let revealed = false;
  let done = false;
  let skipping = false;
  let slowFrames = 0;
  let frameCount = 0;
  let dtSum = 0;

  const draw = () => {
    gl.uniform1f(u.uT, T);
    gl.uniform2f(u.uMouse, mouse.x, mouse.y);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  };

  const destroy = () => {
    done = true;
    cancelAnimationFrame(raf);
    window.removeEventListener('pointermove', onMove);
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  };

  const frame = (now) => {
    if (done) return;
    const dt = last ? Math.min(0.12, (now - last) / 1000) : 1 / 60;
    last = now;

    // Adaptive quality: if the first frames run long, shed resolution, then effects.
    frameCount++;
    dtSum += dt;
    if (frameCount === 20) {
      const avg = dtSum / 20;
      if (avg > 0.032) {
        renderScale = Math.max(0.5, renderScale * 0.75);
        slowFrames++;
        if (slowFrames >= 1 && !liteMode) {
          liteMode = true;
          gl.uniform1f(u.uLite, 1);
          budget = 0.9e6;
        }
        resize();
      }
      frameCount = 0;
      dtSum = 0;
    }
    if (canvas.clientWidth !== cssW || canvas.clientHeight !== cssH) resize();

    const k = 1 - Math.exp(-dt * 4);
    mouse.x += (target.x - mouse.x) * k;
    mouse.y += (target.y - mouse.y) * k;

    if (skipping) boost = T < T_PORTAL - 0.12 ? 5 : 1.5;
    T += dt * speed * boost;

    if (!revealed && T >= T_REVEAL) {
      revealed = true;
      const realSecs = (T_END - T_REVEAL) / (speed * boost);
      onReveal?.(realSecs);
    }
    draw();
    if (T >= T_END) {
      destroy();
      onDone?.();
      return;
    }
    raf = requestAnimationFrame(frame);
  };

  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault();
    if (done) return;
    destroy();
    onDone?.();
  });

  return {
    start() {
      if (typeof debugT === 'number' && !Number.isNaN(debugT)) {
        T = debugT;
        draw();
        return;
      }
      draw();
      raf = requestAnimationFrame(frame);
    },
    skip() { skipping = true; },
    destroy,
  };
}
