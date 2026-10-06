# Design Library

Brand design systems consumed by `runtime/design_library.py` (`kernel.design_library`).

## Layout

```
design-library/
└── <brand>/DESIGN.md     # one folder per brand
```

Each `DESIGN.md` is plain markdown with these `##` sections (any subset works):

- `## Colors` — palette tokens
- `## Typography` — type scale, families
- `## Components` — buttons, cards, inputs
- `## Layout` — grid, spacing, breakpoints
- `## Elevation` — shadows, layering

## Usage

- `DesignLibrary.available_brands` — catalog + on-disk brands.
- `DesignLibrary.load("<brand>")` — load a brand's system (None when absent).
- `DesignLibrary.mix(["a", "b"])` — fuse sections from 2–3 brands.
- `DesignLibrary.import_brand(name, source)` — import a `DESIGN.md` file or raw markdown (e.g. an external export).

## Note on the catalog

`DesignLibrary.CATALOG` lists 56 well-known brand names as *reference* entries —
they are suggestions for systems you can import on demand, not bundled files.
Only brands with a real `<brand>/DESIGN.md` on disk can be loaded or mixed.
The bundled seeds (`minimal`, `midnight`, `editorial`) are original systems
authored for aiZee; import real brand systems via `import_brand` when needed.
