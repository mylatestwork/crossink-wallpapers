# CrossInk compatibility

This repository targets **CrossInk only**. CrossPoint uses different overlay paths and is intentionally not packaged here.

The packaging rules were verified on 31 August 2026 against:

- Repository: <https://github.com/uxjulia/CrossInk>
- Branch: `main`
- Commit: [`cab4f24922f05811e7f44be1057f62ea2d978c52`](https://github.com/uxjulia/CrossInk/commit/cab4f24922f05811e7f44be1057f62ea2d978c52)
- Relevant implementation: [`SleepActivity.cpp`](https://github.com/uxjulia/CrossInk/blob/cab4f24922f05811e7f44be1057f62ea2d978c52/src/activities/boot_sleep/SleepActivity.cpp)

## Packaging contract

| Pack | Folder | Files considered by CrossInk |
| --- | --- | --- |
| Custom | `/.sleep/` | BMP only |
| Page Overlay | `/.sleep/` | BMP and PNG |

CrossInk also accepts `/sleep/` as a fallback and can use a preferred folder selected in its file browser. The two release archives both use `.sleep` because that is the default path, but they must not be merged: Page Overlay would otherwise also select the full-screen Custom BMPs.

The target display size is 480 × 800 px in portrait orientation for X4 and X4 Pro. PNG overlays should use hard transparency and high contrast because the verified CrossInk renderer thresholds alpha and brightness instead of performing smooth alpha blending.
