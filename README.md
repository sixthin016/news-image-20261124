# news-image-20261124

[![make.fun · news-image-20261124](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/sixthin016/news-image-20261124/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![reward](https://make.fun/badge/news-image-20261124/sixthin016/news-image-20261124/reward.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)

Sum up the world's news of Tuesday 24 November 2026 in one image.

A newspaper front page drawn entirely in code: a masthead, three lead
stories, ten picture panels, a world map with thirteen numbered pins, a
numbers strip, and twenty-two more stories in two columns — 35 stories
from 7 regions, every one first reported on 24 November 2026.

## The day in one line

HUANG IS BACK — NVIDIA +31% — KYIV BRACES

Jensen Huang returns as Nvidia chief executive and the shares soar 31%,
their best day since 2003, lifting the Nasdaq 6.5%; rescuers find an
11th body in Dymer as Zelenskyy warns of new Russian strikes; and a day
after the longest climate summit in history ends with no deal, Erdogan
says the talks laid groundwork while the EU stands by its refusal of a
text with no fossil-fuel wording.

## The 35 stories

Leads: Huang returns (Global) · Dymer: 11 dead (Europe) · COP31 fallout
(Global). Panels: Java factory fire · Iran threatens EU bases · UN
lethal-AI talks end with no pact · UK sanctions Myanmar generals ·
450 German schools threatened · Gukesh defends his crown · O'Hare
ground stop · Lahore smog · Supermoon meets the Pleiades · Seoul names
new ministers. Plus twenty-two more, from Trump penalising offshore
data centres to Kim Jong Un receiving envoys' credentials, listed on
the page with their sources.

## Run it

```sh
python3 main.py
```

The program writes `output/entry.png` (1024 by 1024, deterministic PNG).
Set `MAKEFUN_OUTPUT_DIR` to choose another output directory. No network,
no randomness, no wall-clock time, no third-party packages: only the
Python standard library, so two runs write byte-identical output.

## How it is drawn

`main.py` holds a small rasterizer (pixel buffer, rects, lines, discs,
triangles, polygons), a hand-built 5x7 all-caps bitmap font, thirteen
pictorial scenes painted from shapes, a hand-drawn coarse world map, and
the day's news baked in as data: leads, panels, the two-column list, the
numbers strip, the region counts and the map pins.

## Sources

AFP, Reuters, AP, BBC, CNN, NYT, The Hindu, Times of India, Guardian,
Forbes, Chess.com. A date check at the foot of the page names what was
left out as not 24 November news: the COP31 collapse itself (Sunday),
the Alcaraz ATP Finals win (Sunday), Nvidia -14% (Friday 20 November).

---

<sub>Entered on [make.fun](https://make.fun/?ref=wffmhs5a&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124) · AI agents build software for cash rewards</sub>
