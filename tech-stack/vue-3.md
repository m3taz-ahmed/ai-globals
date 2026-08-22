[TECH] Vue 3
[OBJ] Progressive JavaScript framework with Composition API, `<script setup>`, fine-grained reactivity, and Pinia state management.
[RULES]
1. [REQ] Use `<script setup>` SFC syntax for all new components; access `defineProps` / `defineEmits` / `defineExpose` as compiler macros (no import needed).
2. [REQ] Use `ref()` for primitive reactive state and `reactive()` for objects; never mix `ref` and `reactive` for the same logical entity.
3. [REQ] Use `computed()` for derived state; never compute derived values in `watch` or inline in template expressions.
4. [REQ] Use `watch()` / `watchEffect()` for side-effects; provide `onCleanup` or return a cleanup function to prevent memory leaks and stale callbacks.
5. [REQ] Use `defineModel()` for two-way binding between parent and child: `const model = defineModel<T>()` replaces manual `props` + `emit('update:modelValue')`.
6. [REQ] Use Pinia for state management: define stores with `defineStore("name", () => { ... })` (setup syntax); never use Vuex for new projects.
7. [REQ] Use Vue Router 4 with lazy-loaded route components: `component: () => import("./views/About.vue")` to enable code-splitting.
8. [REQ] Use `<Suspense>` for async component orchestration with `#fallback` slot; handle errors with `onErrorCaptured` in parent.
9. [REQ] Use `provide()` / `inject()` for dependency injection across deeply nested components; type the injection key with `InjectionKey<T>`.
10. [REQ] Use `<Teleport>` for modals, tooltips, and overlays to render outside the DOM hierarchy of the parent component.
11. [REQ] Use `vite` for build tooling; configure `@vitejs/plugin-vue` and enable `define: { __VUE_PROD_DEVTOOLS__: false }` in production.
12. [REQ] Use Nuxt 3 / 4 for SSR projects; use `useAsyncData` / `useFetch` for server-side data fetching with hydration matching.
13. [REQ] Use `shallowRef` / `shallowReactive` for large immutable data structures (charts, tables) to avoid deep reactivity overhead.
14. [PROHIBIT] Never mutate `props` directly — use `defineEmits` to notify the parent. Never use Options API (`data()`, `methods`) for new components.
15. [PROHIBIT] Never use `v-html` with untrusted input — use DOMPurify to sanitize. Never use `index` as `:key` for lists that can reorder.
[COMPAT]
- v3.4: `defineModel` stable, `v-bind` shorthand for CSS, improved hydration mismatch warnings.
- v3.5: `useTemplateRef`, reactive props destructure, `useId()` for SSR-safe IDs.
[REFS]
- https://vuejs.org/guide/introduction.html
- https://pinia.vuejs.org/
- https://router.vuejs.org/
