![build](https://github.com/matyalatte/FF7R-DDS-tools/actions/workflows/build.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# FF7R-DDS-tools ver0.1.5
Texture mod tools for FF7R<br>
All you need to do is drop files or folders on batch files.<br>

## Features

- Inject any size DDS and any number of mipmaps.
- Export assets as DDS.
- Remove mipmaps from assets.

## Supported Formats

- DXT1
- BC4/ATI1
- BC5/ATI2
- BC6H
- B8G8R8A8(sRGB)

## Download
Download `FF7R-DDS-tools*.zip` from [here](https://github.com/matyalatte/FF7R-DDS-Injector/releases)

## Basic Usage
1. Drop `.uexp` onto `1_copy_uasset*.bat`.<br>
   The asset will be copied in `./workspace/uasset`.<br>

2. Drop `.dds` onto `2_inject_dds*.bat`.<br>
   A new asset will be generated in `./injected`.<br>

## Advanced Usage
You can inject multiple assets at the same time.

1. Put texture assets you want to mod in a folder.

2. Put dds images you want to inject in another folder.

3. Rename dds images to the same name as the assets you want to mod.<br>
   e.g. If you want to inject `sample.dds` into `abc.uasset`, `abc.uexp`, and `abc.ubluk`, rename `sample.dds` to `abc.dds`.

4. Drop the asset folder onto `1_copy_uasset*.bat`.<br>
   The assets will be copied in `./workspace/uasset`.<br>

5. Drop the dds folder onto `2_inject_dds*.bat`.<br>
   New assets will be generated in `./injected`.<br>

## Batch files
- `1_copy_uasset*.bat`<br>
    Make or clear `./workspace`.<br>
    Then, copy an asset to workspace.

- `2_inject_dds*.bat`<br>
    Inject dds into the asset copied to workspace.<br>
    A new asset will be generated in `./injected`.

- `_export_as_dds*.bat`<br>
    Export texture assets as dds.<br>

- `_remove_mipmaps*.bat`<br>
    Remove all mipmaps from an asset.<br>
    A new asset will be generated in `./removed`.

- `_parse*.bat`<br>
    Parse files.<br>
    You can check the format with this batch file.

## How to Build
You can build my tool with Github Actions.<br>
See here for the details.<br>
[How to Build with Github Actions · matyalatte/FF7R-mesh-importer Wiki](https://github.com/matyalatte/FF7R-mesh-importer/wiki/How-to-Build-with-Github-Actions)

## FAQ

### Is there any point in removing mipmaps?
Basically no.<br>
But there are minor mipmap problems with model mods.<br>
The removal function will resolve them.

### I got the `UE4 requires BC6H(unsigned)...` warning. What should I do?
Nothing needs to be done.<br>
There are two types of BC6H: `signed` and `unsigned`.<br>
UE4 will use the `unsigned` format.<br>
But `signed` format will work fine if all pixels have positive values.

### I got the `Mipmaps should have power of 2 as...` warning. What should I do?
Change its width and height to power of 2.<br>
Or export dds without mipmaps.
