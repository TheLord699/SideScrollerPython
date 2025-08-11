#version 330

in vec3 fragmentColor;
in vec2 fragmentTexCoord;
uniform sampler2D imageTexture;
uniform float time; // elapsed time

out vec4 color;

// Simple pseudo-random hash function for noise
float hash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

// 2D noise function based on hash
float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    // Four corners noise
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    // Smooth interpolation
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(a, b, u.x) + (c - a)* u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
}

// HSV to RGB helper
vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1., 2./3., 1./3., 3.);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6. - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0., 1.), c.y);
}

void main() {
    vec2 uv = fragmentTexCoord;

    // Fractal iterative distortion: warp UV coords multiple times with sin/cos and noise
    vec2 p = uv * 3.0;
    float iter = 4.0;
    for(float i = 1.0; i < iter; i++) {
        p += 0.1 * sin(p.yx * 3.0 + time * i);
        p += 0.05 * noise(p * 3.0 + time * i);
    }
    
    // Chromatic aberration: offset channels differently
    float chromaOffset = 0.005;
    vec2 offsetR = vec2(chromaOffset * sin(time * 3.0), chromaOffset * cos(time * 2.0));
    vec2 offsetG = vec2(chromaOffset * cos(time * 1.5), -chromaOffset * sin(time * 1.7));
    vec2 offsetB = vec2(-chromaOffset * sin(time * 2.5), chromaOffset * cos(time * 3.3));

    vec4 colR = texture(imageTexture, p + offsetR);
    vec4 colG = texture(imageTexture, p + offsetG);
    vec4 colB = texture(imageTexture, p + offsetB);

    vec3 colorChroma = vec3(colR.r, colG.g, colB.b);

    // Hue rotation over time
    float hue = mod(time * 0.2 + uv.x + uv.y, 1.0);
    vec3 hsv = vec3(hue, 0.6, 1.0);
    vec3 hueColor = hsv2rgb(hsv);

    // Combine chroma color with hue shift
    vec3 combined = mix(colorChroma, hueColor, 0.3);

    // Scanline effect (subtle horizontal lines)
    float scanline = 0.85 + 0.15 * sin(uv.y * 800.0 + time * 50.0);

    // Dynamic vignette with noise
    float dist = distance(uv, vec2(0.5));
    float vignette = smoothstep(0.75, 0.4, dist);
    vignette *= 0.8 + 0.2 * noise(uv * 50.0 + time * 5.0);

    // Final color with scanline and vignette
    vec3 finalColor = combined * vignette * scanline;

    color = vec4(finalColor, 1.0);
}
