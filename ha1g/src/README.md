# Tempest HA1G source code

This folder is the complete source of **Tempest HA1G v1.0.1 (build D022)**: the add-on code that
runs on the radio, and the scripts that hook it into the stock firmware. It builds the exact file the
[web flasher](https://tempitor.github.io/Tempest/ha1g/) produces, byte for byte.

There is no manufacturer firmware here. You supply your own stock file, the same one the flasher
asks for: **`HA1G_V1.01.14.002_20260422.bin`** (V1.01.14.002) from the
[Ailunce HA1G software page](https://www.ailunce.com/supports-ha1g-software). Every script checks the
sha256 of its input and refuses anything else.

## Build

You need Linux, macOS or WSL with:

- Python 3.9 or newer, and `pip install keystone-engine pillow capstone unicorn`
- clang, ld.lld and llvm-objcopy (LLVM 14 or newer; on Debian/Ubuntu `apt install clang lld llvm`)

Then:

```sh
cd ha1g/src
./build.sh /path/to/HA1G_V1.01.14.002_20260422.bin          # writes out/HA1G_V1.01.14.002_D022.bin
./build.sh /path/to/HA1G_V1.01.14.002_20260422.bin out --test   # also runs the emulator checks
```

The script checks the stock file, builds each stage, and stops unless the result has the released
sha256 `2048b495e06c8f9a04ce98e52b5e407d37febed36e0b67075a2c317cb67eb123`. With `--test` it also runs
the checks in `verify_*.py`, which execute the patched code in the Unicorn CPU emulator (about a minute).

The built `.bin` contains Retevis firmware, so keep it to yourself; share the source or a patch instead.
To flash it, use the web flasher on the stock file (it builds the same image), or any YMODEM tool
with the radio in update mode (hold PTT + SK1 at power on).

## How it fits together

| Stage | Files | What it does |
|---|---|---|
| 1 | `tools/build_mon.py` | Monitor opens the squelch on every channel (hook in the RX status poll) |
| 1 | `tools/build_tafr.py` | Talk Around / Freq Reversal show the right frequency (display only) |
| 2 | `tools/vfo3/scope/scope.c`, `glue.S`, `link.ld`, `make_cave_clang.sh` | The add-on: S-meter, band scope, waterfall, 3-VFO screens, Side Key PTT, Band Scope and Theme pages, themes. Compiled for address 0x73350, after the end of the stock image |
| 3 | `tools/vfo3/scope/build_scope.py` | Appends the compiled add-on and points the stock code at it (radio tick, key handling, main screen, menus) |
| 4 | `tools/vfo3/build_vfo3.py` | Turns on the stock but disabled third VFO (Band C), 4-decimal frequencies, version string `D022` |
| 5 | `tools/vfo3/logo/build_logo.py`, `logo.c` | Draws the Tempest boot logo in place of the boot picture and blocks CPS boot-picture uploads into that area. The logo shapes come from `tools/vfo3/mock_bootlogo.py` |
| | `tools/ha1g_patch.py` | Makes the patch file the web flasher uses (only the bytes Tempest changes or adds), and applies one |

Each patch script lists its patch sites and explains the stock behaviour it changes in its header.
Before writing, it checks a few original bytes at every site, so a wrong input file fails loudly.

`tools/vfo3/font.py` reads the radio's own font tables from your stock file (`HA1G_IMG`, set by
`build.sh`), so the logo can measure text.

## Making changes

Edit `scope.c` (or a patch script), then run the stages by hand in the order above; `build.sh`
shows the exact commands. `build.sh` itself stops at the end because a changed build no longer
matches the D022 hash, which is expected. To share your build, make a patch for it:

```sh
python3 tools/ha1g_patch.py make STOCK.bin MY_BUILD.bin --name MYBUILD -o MYBUILD.ha1gpatch.json
python3 tools/ha1g_patch.py apply STOCK.bin MYBUILD.ha1gpatch.json OUT.bin
```

If you share a changed version, the GPL asks you to share its source too. Contributions are welcome,
see [CONTRIBUTING.md](https://github.com/Tempitor/Tempest/blob/main/CONTRIBUTING.md).

## License

GPL-3.0-or-later, copyright Tempitor. See
[LICENSE](https://github.com/Tempitor/Tempest/blob/main/LICENSE) and
[NOTICE](https://github.com/Tempitor/Tempest/blob/main/NOTICE).
