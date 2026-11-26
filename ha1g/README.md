# Tempest for the Retevis HA1G

Custom firmware for the Retevis / Ailunce **HA1G**, flashed straight from your browser.

**Open the flasher: https://tempitor.github.io/Tempest/ha1g/**

**Video: [HA1G Tempest firmware walkthrough](https://youtu.be/S8D3sTKIlws)** (waterfall, band scope, multi-VFO)

This repository contains no proprietary firmware, you supply the firmware for your radio. The page
checks that it is the exact stock file, adds the mod to it on your computer, checks the result,
and flashes it to your radio. Nothing is uploaded anywhere.

Current release: **Tempest HA1G v1.0.0** (build D020). After flashing, Menu → Radio Information shows `V1.1.14.002D020`.
Your channels and settings are kept, and CHIRP and the Retevis CPS still recognize the radio.

## What you need

- A Windows, Mac, Linux or ChromeOS computer with **Chrome or Edge** (or Chromium). Firefox,
  Safari and phones do not work, because they have no Web Serial.
- The normal HA1G programming cable.
- The stock firmware **`HA1G_V1.01.14.002_20260422.bin`** (version **V1.01.14.002**). Download it from
  the Ailunce HA1G software page: https://www.ailunce.com/supports-ha1g-software
  Make sure you download exactly this version (V1.01.14.002); newer or older versions do not work
  and are refused. Unzip it first.

## How to flash

1. Back up your codeplug with CHIRP or the Retevis CPS.
2. Open the flasher link above.
3. Choose the stock `.bin` (V1.01.14.002 from the [Ailunce HA1G software page](https://www.ailunce.com/supports-ha1g-software)). You should see two green ticks:
   stock file confirmed, and patched file matches D020.
4. Click **Select COM port** and choose the cable.
5. Turn the radio off. Hold **PTT + SK1** while turning it on (update mode).
6. Click **Flash** and wait for "done" (about a minute).
7. Check Menu → Radio Information.

If something fails, click **Save log**. The radio stays in update mode, so you can just flash again.

## Return to stock

1. Open the flasher and choose the same stock `.bin` as above.
2. Under **Flash**, pick **Stock V1.01.14.002 (your file as is, return to stock)**.
3. Select the COM port, put the radio in update mode (**PTT + SK1** at power on), and click **Flash stock V1.01.14.002**.

The flasher only re-flashes the verified stock file you chose, exactly as it is. The Retevis / Ailunce firmware update tool works too.

After flashing, the red LED may stay on until you transmit, receive or power cycle. That is the
bootloader, not a fault.

**Offline:** download this repository (Code → Download ZIP) and open `ha1g/index.html` in Chrome or Edge.

## Features

**S-meter.** A signal bar from S1 to S9+40 with a reading such as `S7` or `S9+12`. It shows a
green **RX** badge while receiving. While transmitting, it shows a red bar for the power level,
the battery voltage and a red **TX** badge.

**Band scope.** A row of bars showing activity around your frequency. The middle bar is your channel.
- A long press on `0`, or a key set to **Band Scope** in Key Function Select, cycles Bars → Waterfall → Off.
- `0` is also the stock squelch key, so a long press on `0` may also open the Squelch window. Press **Exit** to close it.
- Set the width in Menu → Radio Setting → **15 Band Scope**: Off, ±90, ±112.5, ±180, ±225 or ±450 kHz. A tick marks the saved span, and the Step column shows the gap between bars (5 to 25 kHz).
- It is off after a fresh install. Your on/off choice and width are remembered.
- It only sweeps while your channel is quiet. It pauses while you receive, transmit, scan, use Monitor or listen to FM radio.

**Waterfall.** A full-screen spectrum history of the band scope, with the newest sweep on top.
- A red marker follows the strongest signal. It holds for about 5 seconds on strong signals that stand well above the noise, and ignores momentary spikes.
- With a VFO in frequency mode, the top knob moves the marker and **Menu** tunes the VFO to it. In the single-VFO view you can also type a frequency and press **Menu**.

**Themes.** Menu → Radio Setting → **16 Theme**: Stock (blue/white), Dark, or Tactical (dark olive/brown).
The whole screen follows the theme, including the menus. It is saved across power-off, and Stock is the default.

**Display.** Frequencies show 4 decimal places. In the dual and triple views the S-meter is at the top,
and the VFO cards grow to fill the screen while the scope is off. A Tempest logo replaces the boot picture.

**Three VFOs.** Band C is now available.
- `*` selects the next VFO (A → B → C).
- `#` switches the display between single, dual and triple VFO.
- Band C appears in Menu → Band Setting.
- In the dual and triple views, the receiving VFO's panel turns green and the transmitting VFO's panel turns red.

**Side Key PTT.** Turn it on in Menu → Radio Setting → Key Function → **4 Side Key PTT** (Off after install).
- Single view: nothing changes. PTT transmits on the selected VFO, and the side keys keep their functions.
- Dual view: PTT transmits on the top VFO and SK1 on the bottom one. SK2 keeps its functions.
- Triple view: PTT transmits on the top VFO, SK1 on the middle one and SK2 on the bottom one.
- A side key used as PTT transmits as soon as you press it, without changing the selected VFO.
- Releasing a side key always ends TX. With the keypad locked, side keys still transmit, like the main PTT.

## Fixes

- **Monitor** now opens the squelch on every channel, including tone and reverse channels.
- **Talk Around / Freq Reversal** now shows the correct frequency on screen. Stock showed them swapped.

## Keys

| Key | Function |
|---|---|
| Long press `0` | Band scope: Bars → Waterfall → Off |
| Key set to Band Scope | Band scope: Bars → Waterfall → Off |
| Top knob (waterfall, frequency mode) | Move the marker; **Menu** tunes to it |
| `*` | Next VFO (A → B → C) |
| `#` | Single → dual → triple display |
| SK2 long press | Monitor (single and dual views, or with Side Key PTT off) |
| SK1 (Side Key PTT on) | PTT for the 2nd VFO in dual and triple views |
| SK2 (Side Key PTT on) | PTT for the 3rd VFO in the triple view |

## Things to know

- **Boot picture:** uploading one with the CPS does nothing on this firmware (the CPS reports success). The radio shows the Tempest logo instead.
- **CHIRP and the Band Scope key:** CHIRP doesn't know this key function and may reset that key to OFF when you upload settings. Set the key again on the radio afterwards.
- With Power Save on, scope bars can read low or jumpy.

## Use at your own risk

This is an unofficial modification, not supported by Retevis or Ailunce, and it may void your
warranty. Flashing always carries some risk. Transmit only within your license and local rules.
