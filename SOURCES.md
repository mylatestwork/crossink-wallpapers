# Artwork and conversion sources

## Design source

- `source/custom-png/`
- Final named 480 × 800 transparent PNG masters for the Custom collection
- The author’s working Figma file is intentionally kept outside the public repository because it contains private reference screenshots that are not required by the released artwork.

## Artwork credits

- [Shapes, Symbols & Icons - Vol. 1](https://www.figma.com/community/file/1219674796615198415/shapes-symbols-icons-vol-1) by Counterfeit
- [Shapes, Symbols & Icons - Vol. 2](https://www.figma.com/community/file/1446631459390076153/shapes-symbols-icons-vol-2) by Counterfeit
- Both source files are published under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/) (CC BY 4.0).
- Changes: selected shapes were resized, repositioned, recolored, converted into monochrome masks, and exported as 480 × 800 CrossInk Custom BMP and Page Overlay PNG assets.
- Source and license details verified on the linked Figma Community pages on 31 August 2026.

## Device mockup

- `site/media/device.png`
- `site/media/book-page.png`
- X4 Pro front-device mockup supplied by the repository author on 31 August 2026
- Rights-cleared fictional 480 × 800 book page created specifically as the Page Overlay preview background
- The gallery rebuilds the mockup from the device frame, fictional book page, and selected live overlay using the frame's exact 480 × 800 screen coordinates.
- `assets/x4/page-overlays/overlay-003-reactor.png` is the reference overlay used in the supplied Page Overlay mockup.

## Branding

- `site/media/crossink-logo.png`
- `site/media/social-preview.png`
- Official CrossInk logo downloaded from [crossink.dev/logo.png](https://crossink.dev/logo.png) on 31 August 2026 and used in the gallery header and favicon.
- Social preview created for the CrossInk Wallpapers gallery on 31 August 2026 and exported at 1200 × 630 px.
- CrossInk and its logo belong to the CrossInk project; their inclusion does not imply affiliation or endorsement.

## Exported assets

- `assets/x4/page-overlays/`: numbered and named transparent PNG exports used directly by CrossInk Page Overlay
- `assets/x4/custom/`: numbered and named BMP exports for CrossInk Custom mode
- `source/custom-png/`: matching named transparent PNG masters used to create the Custom BMP files

The current Custom files were flattened onto white and exported locally as uncompressed 24-bit BMPs with ImageMagick. [Wallpaper Converter](https://wallpaperconverter.jakegreen.dev/) provides an equivalent browser-based workflow for the X4 480 × 800 target and supports uncompressed 24-, 8-, 4-, and 1-bit BMP output. The converter is an external service and is not bundled with this repository.

## Publication notes

The public repository contains only the 12 released assets per mode and their final Custom PNG masters. Discarded working frames, the private Figma file, and third-party reading screenshots are excluded. Device and preview assets were created or supplied by the repository author and are not covered by the Counterfeit attribution.

Released wallpaper artwork, source PNG masters, and repository-specific device and preview artwork are licensed by [My Latest Work](https://mylatestwork.net/) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The official CrossInk logo is excluded from this license grant.
