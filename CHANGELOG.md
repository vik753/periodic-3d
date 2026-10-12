# Changelog

**English** · [Українська](CHANGELOG.uk.md) · [Русский](CHANGELOG.ru.md)

All notable changes to the site. Versions follow [Semantic Versioning](https://semver.org):
MAJOR.MINOR.PATCH — a fix raises PATCH, a new feature raises MINOR, an incompatible change
raises MAJOR. The site shows its version in **How to use** → **Site**. Datasets have their
own versions (`data-…`, `gnome-…` releases).

## [Unreleased]

- Where a substance is used: ten spheres (industry, medicine, agriculture, energy, defence…)
  from checked sources (in progress).

## [1.5.0] — 2026-10-11

### Added
- A two-minute video guide in Ukrainian, Russian and English with calm music, opened from
  **How to use**; `/about?video` opens it directly.
- Beginner guides in README (three languages) and the section "How we make sure the data is
  right".
- The site version, build and a link to this changelog in **How to use**.

### Changed
- Hover intent: tiles, rays, cloud orbs, atoms and panel lists react when the pointer
  slows down, not on every pass.
- Long formulas in lists push the name to the next line instead of running into it.

### Fixed
- A blank screen after a new deploy: the page now reloads once, and an error notice
  replaces a blank page.
- Cloud orbs no longer flicker between large and small under the pointer.

## [1.4.0] — 2026-10-11

### Added
- Data quality: formulas cross-checked between Wikidata, PubChem and SMILES; a golden set
  of 19 substances guards each dataset; a data-quality report; **Report an error** buttons.
- Crystals marked "structure from experiment (ICSD)" or "computed structure only".
- Fast zoom to the element under the pointer, a magnified tile on hover and tap, the
  **To the table** button, cosmic dust behind the table.

### Changed
- Sharp tile labels at any zoom (distance-field text).
- The selection bar is taller and stays at the bottom of the screen.

## [1.3.0] — 2026-10-11

### Added
- 554 054 crystals predicted by GNoME (Google DeepMind) as a separate violet layer: rays,
  walks, cloud orbs and material cards with the unit cell. The site stays non-commercial
  (CC BY-NC 4.0).

## [1.2.0] — 2026-10-11

### Added
- Photos of substances and elements from Wikimedia Commons with author and license.
- Cloud filter: all, organic, inorganic, minerals.

## [1.1.0] — 2026-10-10

### Added
- Similar elements and compounds from a vector model (PPMI + SVD, pgvector).

## [1.0.0] — 2026-10-10

### Added
- The 3D periodic table, flights into elements, red rays to partners, walks along a ray,
  compound cards with 3D models, the cloud of compounds for several elements, search in
  three languages, an address for every scene; the API and the static demo.

[Unreleased]: https://github.com/vik753/periodic-3d/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/vik753/periodic-3d/releases/tag/v1.5.0
[1.4.0]: https://github.com/vik753/periodic-3d/commit/f02d2b49
[1.3.0]: https://github.com/vik753/periodic-3d/commit/89f0b7b8
[1.2.0]: https://github.com/vik753/periodic-3d/commit/ea2cfbb4
[1.1.0]: https://github.com/vik753/periodic-3d/commit/72ecceee
[1.0.0]: https://github.com/vik753/periodic-3d/commit/8f517d14
