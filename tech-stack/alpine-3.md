[TECH] alpine-3
[OBJ] Alpine.js v3.x Standards.
[RULES]
1. [REQ] Design: Keep logic inside `x-data`. Use `Alpine.store()` for globals.
2. [REQ] Reactivity: Prefer `x-show` over `x-if` for frequent toggles. Use `x-on` with `.prevent`/`.stop`/`.window`.
3. [REQ] Livewire: Sync with `$wire.entangle()`. Protect DOM mutations with `wire:ignore`.
