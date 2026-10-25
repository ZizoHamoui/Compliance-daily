# The Tone at the Top — Brand identity

**Concept: "Newsroom Blue."** A cool, credible palette built from colours people already associate with trusted
media and professional networks: The Guardian's deep blue for authority, LinkedIn's blue for the professional,
interactive layer, and accents from Twitch, Slack and Spotify for clear, modern signals.

## Hard rules

1. **No red anywhere.** No reds, pinks, oranges, terracottas, warm yellows, golds or creams (this also excludes
   the warm terracotta and cream tones associated with Claude). Every colour in the system sits between green (≈140°)
   and violet (≈270°) on the colour wheel, plus cool neutrals.
2. **60 · 30 · 10.** About 60% Paper (white and cool mist), 30% Ink (Guardian Blue), and 10% Accent (LinkedIn Blue)
   for links, selections, focus and the signature rule only.
3. **Signals are hue-reserved.** Violet means *Act now* and cyan means *Monitor*. The brand never uses these
   decoratively, so they always carry meaning.
4. **Never colour alone.** Each signal also has a label and icon ("Action required" with "!", "Monitor" with an eye).
5. **Contrast first.** Every text pairing below meets WCAG AA (4.5:1), and most meet AAA (7:1).

## Core palette

| Role | Name | Hex | Source inspiration | Contrast on white |
|---|---|---|---|---|
| Ink (30%) | Guardian Blue | `#052962` | The Guardian | 14.0:1 |
| Ink, light | Ink 2 | `#0F3D82` | derived | — |
| Accent (10%) | LinkedIn Blue | `#0A66C2` | LinkedIn "Science Blue" | 5.7:1 |
| Accent container | Blue tint / ink | `#DCEBFA` / `#003366` | derived | 10.4:1 |
| Paper (60%) | Paper | `#FFFFFF` | — | — |
| | Mist | `#EEF3F9` | LinkedIn "Botticelli" `#DCE6F1`, lightened | — |
| | Mist low / high | `#F5F8FC` / `#DCE6F1` | | |
| Text | Body | `#34435E` | derived | 9.9:1 |
| | Meta | `#56687A` | LinkedIn "Blue Bayoux" | 5.7:1 |

## Signal palette (semantic only)

| Signal | Strong | Container | On-container | Soft tint | Inspiration |
|---|---|---|---|---|---|
| Act now (Action required) | `#6E32D9` (white text 6.7:1) | `#E6DAFF` | `#2E1065` | `#F5F0FF` | Twitch purple `#9146FF`, deepened |
| Monitor | `#00708F` | `#D7F1FA` | `#00334A` | `#EEF9FC` | Slack cyan `#36C5F0` family |
| FYI | `#56687A` | `#E6EBF1` | `#1F2A36` | `#F4F6F9` | LinkedIn slate |

## Source palette

| Source | Colours | Inspiration |
|---|---|---|
| Official source | Outline chip, body text | — |
| Expert analysis | Mist chip `#EEF3F9`, body text | — |
| AI briefing | Green chip `#DCF5E5`, ink `#05391C`, links `#0B7A3B` | Spotify green `#1DB954` family |

## Signature elements

- **Brand mark:** a Guardian Blue rounded square with a serif "T" and a small LinkedIn Blue dot.
- **Accent rule:** a short 56px rounded LinkedIn Blue bar under the nameplate.
- **Illustrations:** topic tiles alternate Guardian Blue and LinkedIn Blue tints, told apart by icon.
- **Glass:** white translucent glass, used only for floating navigation.

## Where the tokens live

`static/style.css` `:root` holds every colour as a CSS variable, and `scripts/send_email.py` and
`scripts/build.py` (illustrations) use the same hex values. Change colours there only, and keep this document in sync.
