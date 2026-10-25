# Image policy — The Tone at the Top

Every story shows an image, and every image must be one we are allowed to show, with credit given.
`scripts/images.py` enforces these rules automatically, and the AI editor never writes image URLs or credits.

## Where images may come from

| Order | Source | When it's allowed | Credit shown |
|---|---|---|---|
| 1 | The story's own preview image | Only for publishers whose terms allow reuse: **U.S. federal agencies** (works of the U.S. government are public domain, 17 U.S.C. §105), the **Government of Canada** (non-commercial reproduction with attribution), **EU institutions** (reuse with the source acknowledged, Commission Decision 2011/833/EU) | "Image: U.S. Department of Labor (U.S. government work, public domain)", "© European Union", etc. |
| 2 | **Wikimedia Commons** | Only files under **CC0, public domain, CC BY or CC BY-SA** | "Photo: *Author* / Wikimedia Commons, *licence*", linking to the file page and the licence |
| 3 | The site's own topic illustration | When nothing above passes | None needed (made for this site) |

Preview images from news outlets, law-firm sites and blogs are **never** reused, even when the article itself is linked.

## What is never used

- Logos, seals, emblems, badges, coats of arms or flags-of (trademark and endorsement risk)
- Portraits, headshots or photos centred on people, and any image of children (personality and privacy rights)
- Graphic, violent or sensitive imagery; protests or riots; weapons
- Maps, charts, diagrams, screenshots, cartoons
- Files that Commons flags with extra restrictions (for example trademark or personality-rights notices)
- Small or non-landscape images (under 900px wide, or outside a 1.2–2.4 aspect ratio)

## How a picture is chosen

1. The editor writes an `image_query` per story: a named building, place, vehicle or object (no people, logos or seals).
2. The script searches Commons, keeps only licensed files that pass the filters above, and requires the file's title
   or description to match most words of the query.
3. If that fails, it tries the source's headquarters (for example the SEC building), then a vetted generic query
   for the topic, and never uses the same image twice in one edition.
4. The licence, author, file page and licence link are stored with the story and shown under the image.

Licences such as CC BY and CC BY-SA require attribution; we display images unmodified (only resized by
Wikimedia's own thumbnailer), so share-alike obligations on adaptations do not arise.
