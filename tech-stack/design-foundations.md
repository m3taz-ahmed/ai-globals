# Global Design Foundations (2024-2025)

## 1. MODERN AESTHETICS & LAYOUTS
- **Bento Grids:** Use modular, card-based layouts with varying spans. Ensure consistent gaps using `gap-4` or `gap-6`. Use `aspect-ratio` to maintain visual balance.
- **Glassmorphism:** Implement using `backdrop-blur-md`, `bg-white/10`, and subtle `border-white/20`. Always include a fallback background color for non-supporting browsers.
- **Neumorphism:** Use soft shadows for depth. `shadow-[5px_5px_10px_#bebebe,-5px_-5px_10px_#ffffff]`. Best used for subtle UI controls, not entire layouts.
- **Modern Gradients:** Favor mesh gradients or multi-stop linear gradients. Example: `bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500`.

## 2. THE WOW FACTOR RULES
- **Micro-interactions:** Every button hover, card click, and transition must feel "alive".
- **Visual Hierarchy:** Use bold typography and scale to guide the eye.
- **Empty States:** Never show a blank screen. Use illustrations or stylized placeholders.
- **Dark Mode Excellence:** Don't just flip colors. Adjust saturation and contrast for eye comfort. Use `zinc` or `slate` palettes instead of pure black `#000000`.

## 3. TYPOGRAPHY STANDARDS
- **English Fonts:** Primary: `Inter`, `Outfit`, or `Geist`.
- **Arabic Fonts:** Primary: `IBM Plex Sans Arabic`, `Readex Pro`, or `Noto Sans Arabic`.
- **Harmony:** Ensure font-weight and line-height are balanced between languages. Arabic typically requires `1.5` to `1.7` line-height for readability.
