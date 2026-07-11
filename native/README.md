# TeachCut native engine sources

TeachCut is a permanent Windows-focused fork. Its native editing engine is kept in this repository so application and engine changes can be built, reviewed, and rolled back together.

## Imported sources

| Directory | Upstream | Imported revision |
|---|---|---|
| `libopenshot` | `https://github.com/OpenShot/libopenshot.git` | `8f1f091c1d90f9b1acbef45ed09fb3f440d85a94` |
| `libopenshot-audio` | `https://github.com/OpenShot/libopenshot-audio.git` | `48516e0b64b9f3ddf2ab79975a42ba2f37023703` |

The imported `libopenshot` tree includes the Windows fixes previously carried as build-time patches: GCC 16 `<cstdint>` compatibility, HEVC/AV1 hardware decode enablement, and modern NVENC options with explicit VBR rate control.

Keep the original license files and source headers when modifying or redistributing these components. Windows builds compile these directories directly; `build/deps` is no longer part of the source pipeline.
