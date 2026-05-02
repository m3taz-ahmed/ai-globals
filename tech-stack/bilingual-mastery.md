# Bilingual (RTL/LTR) Mastery Standards

## 1. LAYOUT ARCHITECTURE
- **Global Direction:** Use the `dir` attribute on the `<html>` or `<body>` tag.
- **Logical Properties:** 100% adoption of CSS logical properties (`margin-inline`, `padding-block`, `inset-inline-start`).
- **Layout Mirroring:** Ensure grids and flexboxes flow correctly. `justify-start` and `text-start` are mandatory.

## 2. ARABIC TYPOGRAPHY HARMONY
- **Font Scaling:** Arabic characters often appear smaller than English at the same pixel size. Adjust `base` font-size if necessary.
- **Line Height:** Increase `line-height` for Arabic (target `1.6+`) to prevent diacritics from clipping.
- **Contextual Shapes:** Use fonts that support full OpenType features for Arabic script.

## 3. MIXED-LANGUAGE RENDERING
- **Isolate Technical Terms:** Wrap English terms in a separate `<span>` with `dir="ltr"` if they break the Arabic flow.
- **Neutral Symbols:** Be careful with punctuation like `?` and `!`. In Arabic, use `؟`.
- **Numbers:** Consistently use either Eastern Arabic numerals (`٠١٢٣`) or Western Arabic numerals (`0123`) as per project preference, but do not mix them.
