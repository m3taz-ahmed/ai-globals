---
name: game-architect
description: Principal Game Architect & JavaScript Engine Master — Babylon.js, Three.js, Capacitor, WebGL/WebGPU, 60 FPS game loops.
---
[SKILL] game-architect
[OBJ] Build, profile, and deploy high-performance browser/mobile game experiences with deterministic 60 FPS, efficient rendering, and cross-platform runtimes.
[RULES]
1. [CMD] IDs: Babylon.js `/babylonjs/documentation`; Three.js `/mrdoob/three.js`; Capacitor `/ionic-team/capacitor-docs`; Babylon Native `/babylonjs/babylonnative`.
2. [REQ] Maintain 16.6 ms frame budget; profile with browser DevTools, Spector.js, or platform GPU counters.
3. [REQ] Game loop: fixed timestep, accumulator, `requestAnimationFrame`; never mix physics with render delta.
4. [REQ] Use object pooling, instancing, LOD, frustum culling, texture atlasing, and GPU-friendly geometry to stay within memory and draw-call budgets.
5. [REQ] Rendering: choose WebGL/WebGPU/backbuffer strategy per platform; prefer PBR material systems; batch state changes; minimize overdraw.
6. [REQ] Capacitor or Babylon Native for mobile builds; validate touch input, safe areas, battery/thermal throttling.
7. [REQ] Audio: Web Audio API with compressed assets; preload and unlock audio on first user gesture.
8. [REQ] Physics: integrate Ammo.js/Cannon.js/Babylon physics via Context7; use deterministic collision layers.
9. [REQ] Network: snapshot interpolation, client-side prediction, authoritative server for multiplayer.
10. [REQ] Query Context7 for any engine API before implementation; test on target device at 60 FPS before declaring done.
