# Tempest features by radio

One row per feature, one column per radio. Each radio is its own port with its own source folder
and release line; this table only tracks which features each one has.

The maintainer of each radio updates that radio's column when they ship a release.

| Value | Meaning |
|---|---|
| `v1.0.0` | First release of that radio's line with the feature |
| planned | Not released yet, intended |
| - | Not planned, or not possible on this radio |

## Display and receive

| Feature | HA1G | HA1UV | HA2 |
|---|---|---|---|
| S-meter, S1 to S9+40 with numeric reading and RX badge | v1.0.0 | planned | planned |
| TX power bar with battery voltage and TX badge | v1.0.0 | planned | planned |
| Band scope around the current frequency, selectable width | v1.0.0 | planned | planned |
| Waterfall with marker on the strongest signal | v1.0.0 | planned | planned |
| Waterfall marker tunes the VFO (knob moves it, Menu tunes) | v1.0.0 | planned | planned |
| Waterfall colours follow the noise floor | v1.0.1 | planned | planned |
| 4-decimal frequency display | v1.0.0 | planned | planned |
| Themes: Stock, Dark, Tactical | v1.0.0 | planned | planned |
| Tempest boot logo | v1.0.0 | planned | planned |

## VFOs and keys

| Feature | HA1G | HA1UV | HA2 |
|---|---|---|---|
| Third VFO (Band C) | v1.0.0 | planned | planned |
| Single, dual and triple VFO views | v1.0.0 | planned | planned |
| Receiving panel green, transmitting panel red | v1.0.0 | planned | planned |
| Side Key PTT on the other VFOs | v1.0.0 | planned | planned |
| Band Scope key function | v1.0.0 | planned | planned |

## Fixes to stock behaviour

These depend on the stock firmware of each radio. Mark - if that radio's stock does not have the bug.

| Fix | HA1G | HA1UV | HA2 |
|---|---|---|---|
| Monitor opens the squelch on every channel | v1.0.0 | planned | planned |
| Talk Around / Freq Reversal show the right frequency | v1.0.0 | planned | planned |

## Flasher and source

| Feature | HA1G | HA1UV | HA2 |
|---|---|---|---|
| Browser flasher that patches your own stock file | v1.0.0 | planned | planned |
| Return to stock from the flasher | v1.0.0 | planned | planned |
| Source with a script that rebuilds the release | v1.0.0 | planned | planned |
