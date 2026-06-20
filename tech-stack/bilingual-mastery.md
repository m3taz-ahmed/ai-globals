[TECH] bilingual-mastery
[OBJ] Global standard for RTL/LTR bilingual app architecture.
[RULES]
1. [REQ] Global Direction: Dynamically inject `dir="rtl"` or `dir="ltr"` on `<html>` or `<body>`.
2. [REQ] Logical Properties: 100% adoption of CSS logical properties (`margin-inline`, `padding-block`, `inset-inline-start`).
3. [REQ] Typography Harmony: Adjust `base` font-size and increase `line-height` (target `1.6+`) for Arabic to prevent diacritic clipping.
4. [REQ] Mixed-Language Rendering: Isolate English technical terms inside Arabic prose with `<span dir="ltr">`.
5. [REQ] Symbol Isolation: Use `؟` for Arabic instead of `?`. Use standardized numerals (either `٠١٢٣` or `0123` consistently).
