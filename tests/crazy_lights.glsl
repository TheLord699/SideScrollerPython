#version 330

in vec2 fragmentTexCoord;
uniform sampler2D imageTexture;
uniform float time;
uniform vec2 resolution;

out vec4 color;

// Function to create smooth radial gradient (vignette base)
float vignette(vec2 uv, float radius, float softness) {
    float dist = length(uv - 0.5);
    return smoothstep(radius, radius - softness, dist);
}

// Function to create animated god rays
float godRays(vec2 uv, vec2 lightPos) {
    const int NUM_SAMPLES = 30;
    float decay = 0.95;
    float exposure = 0.06;
    float weight = 0.5;

    vec2 deltaTex = (uv - lightPos) / float(NUM_SAMPLES) * 0.8;

    float illuminationDecay = 1.0;
    float rays = 0.0;

    vec2 coord = uv;

    for(int i = 0; i < NUM_SAMPLES; i++) {
        coord -= deltaTex;
        float sample = texture(imageTexture, coord).r;  // brightness approx.
        sample *= illuminationDecay * weight;
        rays += sample;
        illuminationDecay *= decay;
    }
    return rays * exposure;
}

// Simple bloom (glow) by brightening bright areas
vec3 bloom(vec2 uv) {
    float brightness = max(max(texture(imageTexture, uv).r, texture(imageTexture, uv).g), texture(imageTexture, uv).b);
    float glow = smoothstep(0.6, 1.0, brightness);
    return vec3(glow);
}

// Color grading - subtle blue-green cinematic tone
vec3 colorGrade(vec3 col) {
    col = pow(col, vec3(0.9)); // slight gamma correction
    col.r *= 0.9;
    col.g *= 1.1;
    col.b *= 1.2;
    return col;
}

void main() {
    vec2 uv = fragmentTexCoord;

    // Base scene texture color
    vec3 baseColor = texture(imageTexture, uv).rgb;

    // Position of light source in UV coords, oscillates over time
    vec2 lightPos = vec2(0.5) + 0.3 * vec2(cos(time * 0.3), sin(time * 0.4));

    // God rays effect
    float rays = godRays(uv, lightPos);

    // Bloom effect
    vec3 glow = bloom(uv);

    // Vignette effect
    float vig = vignette(uv, 0.75, 0.25);

    // Combine all
    vec3 finalColor = baseColor + glow * 1.5 + rays * 1.8;
    finalColor = colorGrade(finalColor);
    finalColor *= vig;

    color = vec4(finalColor, 1.0);
}
