---
name: my-maps-spots
description: Build a Google My Maps import (CSV) of spots for a place, sourced from first-hand travel blogs and articles by locals and travellers. Use when the user wants map pins, a travel map, or a My Maps CSV with verified coordinates, descriptions, local names, Google Maps links, official websites, and the source posts. Also shows the spots in the chat grouped by area, each with a photo. The place name may come later; if it is not given, ask for it in the chat.
---

# My Maps spots from first-hand travel writing

Turn a place name into CSV files that import cleanly into Google My Maps. Every pin
comes from real blog posts or articles written by residents or people who actually
travelled there, carries an accurate location, and lists the posts it came from. The
same spots are also shown in the chat, grouped by area, each with a photo.

The user will follow these pins on the ground. **A missing pin is better than a
wrong pin. A missing link is better than a guessed link.**

These instructions are agent-neutral. "Search the web", "open the page" and "run the
command" mean whatever tools your environment provides. If you cannot run scripts,
follow the manual path described in each step.

## Step 1: Ask for the place in the chat and wait

The place name normally does **not** come with the request. It is not an error or
missing input; getting it is this step's job.

- If the user's message already names a place, use it and go to Step 1b.
- Otherwise, your whole reply is a short, friendly question in the chat, in the
  user's language. Ask only for the place; interests come in Step 1b, once you know
  the place. For example:

  > Which place would you like me to map? It can be a city, town, island or region.
  > Add the country if the name could mean more than one place.

- Ask as ordinary chat text. Do not use pop-up forms, question widgets or other
  tools, and do not say that the input or a parameter is missing.
- Then stop and wait for the answer. Do not search, guess a place, or create files
  before the user replies.
- If the name is ambiguous (Portland, Victoria, San José), ask which one.
- Do not ask how many spots; the sources decide (see Step 4).
- Note the **user's language** (the language they write in) and work out the **local
  language(s)** of the place. Descriptions are written in the user's language; local
  names and terms come from the local language.

## Step 1b: Suggest interests that fit the place

Generic options like "food, nature, architecture" don't help the user choose. Once
you know the place, tell them what it is actually known for, so they can pick.

- Do a quick search first (for example `<place> what is it known for`,
  `<place> travel highlights`, and the same in the local language) to confirm what
  the place is famous for. Don't rely on memory alone, especially for small places.
- Reply in the chat with 4 to 6 themes typical of **this** place. Give each theme
  one line with one or two concrete, real examples, including the local term when it
  is part of the experience. Keep the whole reply short.
- End by asking which themes they want. Mention that "everything" is fine, and that
  they can add their own (travelling with kids, budget, rainy day, ...).
- Then stop and wait. If the user's earlier message already stated interests, skip
  this step.

Example for Helsinki, written in English (write yours in the user's language):

> Helsinki is especially known for:
> - **Design and architecture**: the Design District, Alvar Aalto's buildings, Oodi library
> - **Sauna culture** (*sauna*): public saunas by the sea such as Löyly and Allas Sea Pool
> - **Sea and islands**: the Suomenlinna sea fortress and summer island-hopping by ferry
> - **Markets and Nordic food**: Market Square (*Kauppatori*) and the Old Market Hall
> - **Nature in the city**: Central Park, seaside paths, and Nuuksio National Park as a day trip
>
> Which of these interest you? "Everything" is fine too, and you can add your own wishes.

Use the chosen themes to steer the searches in Step 2 and the categories in Step 3.
Spots outside the chosen themes can still be included when several first-hand sources
strongly recommend them.

## Step 2: Find first-hand sources

Search in **both** the user's language and the local language. When neither of them is
English, also search in **English**, since English usually has more first-hand posts
and detail than the user's language (for example, a Japanese reader searching for
Helsinki finds more in English than in Japanese). Use several phrasings, for example (the
phrasings below are in English; translate them for the other languages, and adapt the
local-language ones, these are Finnish examples for Helsinki):

- `"<place>" travel blog`, `"<place>" trip report`, `"<place>" itinerary blog`
- `"<place>" local's guide`, `"<place>" hidden gems blog`, `living in <place> favourite places`
- local language: `<place> vinkit`, `<place> blogi`, `asun <place>`, `suosikkipaikat <place>`
- forum and community trip reports (Reddit, local forums) when they contain detail

Open and read the posts, not just the search snippets. Aim for at least 5 distinct
first-hand sources; for small places accept however many genuinely exist.

**Keep** a source when it is first-person ("we walked", "I have lived here for ten
years"), shows the author was there (own photos, specific details, dates), and has an
identifiable author or publication.

**Reject** booking and review aggregators, AI-generated or SEO listicles, pages with
no author, and content that only rewrites other sites. Log every source you opened,
kept or rejected, with a one-line reason. The user wants to see them.

## Step 3: Extract candidate spots

For each spot a source recommends, record:

- `local_name`: the name as written locally (for example `Temppeliaukion kirkko`).
- `name`: the pin title. Use the local name, followed by the user's-language name in
  brackets when it differs: `Temppeliaukion kirkko (Rock Church)`.
- `category`: a short layer name in the user's language (Sights, Food & Drink, Nature,
  Museums, Shopping, Nightlife, ...). Keep the total to 10 or fewer, since My Maps
  allows 10 layers per map.
- `area`: the neighbourhood, district or zone of the place where the spot lies (for
  example Kallio, Töölö, "Islands in the harbour"). Use the names the sources and
  Wikipedia use. Step 6 turns these into the list of areas.
- what the author said or recommended (a tip, a favourite dish, best time to go).
- `sources`: the URL of every kept post that mentions this spot.
- `search_query`: the text you would type into Google Maps to find it, including the
  city, for example `Temppeliaukion kirkko, Helsinki`.
- `address`: if a source or official site gives a street address, record it.

Merge duplicates across sources (same place under different names) and keep all their
source URLs.

## Step 4: Decide how many spots

There is no fixed number. Include the spots that first-hand sources actually
recommend. That naturally scales with the place: a village may yield 3 to 5, a big
city 15 to 30.

- Every spot needs at least one kept first-hand source.
- Rank by how many independent sources mention a spot.
- If more than about 30 candidates remain, keep the most-mentioned ones and ask the
  user before adding the rest.

## Step 5: Enrich each spot

Research background beyond the blog: history, who built it, what it is known for,
practical details. Prefer Wikipedia (in both languages), Wikidata, the official site,
and official tourism boards. Write the `description` in the user's language, 2 to 4
sentences: what it is, background or history, and the first-hand tip.

Add `local_terms` that help the user learn and use local words, for example the parts
of the name (`saari` = island, `tori` = market square, `kirkko` = church), with a simple
pronunciation hint when useful.

Never invent facts, opening hours, prices, or URLs. If you could not confirm
something, leave it out.

Note the spot's Wikidata ID (`Q...`) if you find one: it lets the verifier cross-check
the location, and it adds the spot's Wikimedia Commons photo as a last-resort image.

### Photos

Every spot should have a photo in the chat list; the output never shows a link instead
of one. List image URLs in `images`, best first. Give each spot a few candidates from
different sites, because some will not embed in chat apps.

1. The spot's official website or tourism board page.
2. Wikimedia Commons (often found through the Wikipedia or Wikidata page). Use the
   direct `https://upload.wikimedia.org/...` thumbnail URL (about 480 px wide), or
   `https://commons.wikimedia.org/wiki/Special:FilePath/<File_name>?width=480`, not the
   `commons.wikimedia.org/wiki/File:` page.
3. A photo from one of the source posts, only if the post's licence or the author
   clearly allows showing it.

Do not use Google Maps or Google Places photos. Each URL must:

- start with `https://`;
- point directly at a JPEG, PNG, WebP or GIF file, not a web page, SVG or AVIF;
- be a thumbnail-sized file, under about 1.5 MB.

The scripts check this later. A spot with no working image is still listed, without a
photo, and the script warns about it.

Only set `website` if you confirmed it is the spot's own official site (linked from
Wikipedia/Wikidata, the tourism board, or clearly operated by the venue). Set
`website_confirmed_official: true` when you do.

## Step 6: Write `spots.json`

Create a working folder `output/<place-slug>/` and write `spots.json`:

```json
{
  "place": {
    "query": "Helsinki, Finland",
    "slug": "helsinki",
    "user_language": "en",
    "local_language": "fi",
    "areas": [
      {"id": "centre", "name": "City centre", "local_name": "Keskusta",
       "summary": "The compact heart of Helsinki around the railway station and the harbour front."},
      {"id": "toolo", "name": "Töölö", "local_name": "Töölö",
       "summary": "A leafy residential district just north-west of the centre."}
    ]
  },
  "labels": {},
  "spots": [
    {
      "id": "temppeliaukio",
      "name": "Temppeliaukion kirkko (Rock Church)",
      "local_name": "Temppeliaukion kirkko",
      "category": "Sights",
      "area": "toolo",
      "description": "A Lutheran church carved directly into solid granite, completed in 1969 by architects Timo and Tuomo Suomalainen. A copper dome and a ring of skylights let daylight in along the rock walls. Bloggers recommend going early to avoid tour groups and checking for concerts, as the acoustics are excellent.",
      "local_terms": [
        {"term": "kirkko", "meaning": "church", "pronunciation": "KEERK-ko"},
        {"term": "temppeliaukio", "meaning": "temple square"}
      ],
      "search_query": "Temppeliaukion kirkko, Helsinki",
      "address": "Lutherinkatu 3, 00100 Helsinki",
      "wikidata": "Q1132809",
      "website": "https://www.temppeliaukionkirkko.fi/",
      "website_confirmed_official": true,
      "images": ["https://upload.wikimedia.org/wikipedia/commons/thumb/..."],
      "sources": ["https://example-blog.com/helsinki-weekend"]
    }
  ],
  "sources": [
    {
      "url": "https://example-blog.com/helsinki-weekend",
      "title": "A slow weekend in Helsinki",
      "author": "Jane Doe",
      "date": "2025-06-14",
      "language": "en",
      "kind": "traveller blog",
      "status": "used",
      "reason": "First-person trip report with own photos",
      "spots": ["temppeliaukio"]
    },
    {
      "url": "https://example-aggregator.com/top-50-helsinki",
      "title": "Top 50 things to do in Helsinki",
      "status": "rejected",
      "reason": "SEO listicle, no author, no first-hand detail"
    }
  ]
}
```

Optional field: `place.bbox` as `[south, west, north, east]` if the automatic bounding
box would be wrong (for example a region rather than a city).

**Areas.** `place.areas` is the list of areas that the spots lie in, in the order the
user should see them (for example from the centre outward, or in the order of a sensible
walking route). Each area has an `id`, a `name` in the user's language, the
`local_name`, and a one-line `summary` in the user's language of what the area is like,
taken from the sources or Wikipedia. Use 2 to 8 areas; a village may need only one.
Every spot's `area` is the `id` of one of them. A spot without a valid `area` is shown
under "Other areas", so assign them all.

**Labels.** When the user's language is not English, translate the output headings in
`labels`. Keys and English defaults: `other_areas` Other areas, `address` Address,
`local_terms` Local terms, `item_sources` Sources, `google_maps` Google Maps, `website`
Website, `sources_used` Sources used, `rejected_sources` Rejected sources.

## Step 7: Verify locations, links and websites

### With scripts (preferred)

The scripts use only the Python 3 standard library. Paths are relative to this skill's
folder.

**Do not check for the key yourself.** The key is a secret: `.env` is git-ignored, so
your file-reading and search tools often cannot see it, and a missing result from them
says nothing. Run this first:

```bash
python3 scripts/verify_places.py --check-key
```

It looks in the environment variable, then in the `.env` in this skill folder, and
prints each place it looked. It does not call Google, does not need `spots.json`, and
does not print the key.

- Exit 0 and `Google Maps API key: found in ...`: a key is configured. Run the verify
  command below. Before any spot, the script sends one Places request to confirm Google
  accepts the key. `Places API accepted the key.` means it did. If the request is
  rejected, stop and tell the user what the error says. Do not switch to open data mode
  unless they ask.
- Exit 1 and `Google Maps API key: not found.` plus `Checked:` lines: no key is
  configured. Show the user those lines. Tell them once that a key gives verified
  Google Maps links (setup is in the README next to this file) and offer to continue
  without one. Run the verify command only after they agree. It will use open data mode.

Never decide from your own checks that there is no key, and never skip `--check-key`
because you could not see `.env`. If the user said they set up a key but it exits 1,
show them the "Checked" lines and rerun with `--env-file <path to the .env>` if they
give a different location. `--mode google` makes a full run stop with an error instead
of falling back. **Never ask the user to paste a key into the chat, and never print
the key or the contents of `.env`.**

```bash
python3 scripts/verify_places.py output/<slug>/spots.json -o output/<slug>/verified.json
```

The script picks its mode automatically:

- **Google mode**, when `GOOGLE_MAPS_API_KEY` is set (environment variable, or a `.env`
  file in this skill folder). It looks each spot up with Google Places API Text Search
  and takes coordinates, the Google Maps link and the website from Google's result.
- **Open data mode**, without a key. It geocodes with OpenStreetMap Nominatim and
  cross-checks against Wikidata coordinates or the street address. The Google Maps
  link stays empty, because nothing confirmed the place exists on Google Maps.

Then read `verified.json`. Each spot has `verification.status`:

- `verified`: safe to pin.
- `unconfirmed` or `not_found`: read `verification.notes`. You may fix
  `search_query`, `local_name`, `address` or `wikidata` in `spots.json` and rerun.
  Do not force a pin. Spots that remain unverified are excluded and reported.

For each verified spot that has a `wikidata` ID, the script also appends that item's
Wikimedia Commons image to the spot's `images`, as the last candidate.

### Without scripts (manual path)

For each spot:

1. Find coordinates from **two independent** sources: for example the Wikipedia or
   Wikidata coordinates, plus OpenStreetMap (openstreetmap.org search) or the official
   site's address geocoded on OpenStreetMap.
2. Accept only if the two agree within 150 m (or one lies inside the other's outline
   for large places like parks and islands), and the point is inside the place.
3. Add a Google Maps link only if you actually opened a Google Maps result for that
   exact place. Use the URL of that result. Otherwise leave it empty.
4. Use 6 decimal places for coordinates.

## Step 8: Build the CSVs and the area list

### The CSVs

```bash
python3 scripts/build_mymaps_csv.py output/<slug>/verified.json --out-dir output/<slug>
```

This writes:

- `<slug>-all.csv`: every verified spot in one layer.
- `<slug>-<category>.csv`: one file per category, one My Maps layer each.
- `sources.md` and `sources.csv`: every source opened, used or rejected, and which
  spots came from it.
- `excluded.csv`: spots left out and why.

Manual path: write the same files by hand. The CSV is UTF-8 with a header row and these
columns, in this order, with standard CSV quoting:

```
Name,Local name,Category,Area,Description,Latitude,Longitude,Google Maps URL,Website,Sources
```

- `Area`: the area's name (from `place.areas`), so it shows in the pin's details.
- `Description`: the description text, then a blank line, then
  `Local terms: kirkko = church (KEERK-ko); temppeliaukio = temple square`.
- `Sources`: source URLs separated by single spaces.
- Empty cells for unknown links. Never fill them with guesses.

### The list for the chat

```bash
python3 scripts/render_spots.py output/<slug>/verified.json -o output/<slug>/spots.md
```

It prints (or writes) Markdown for the chat, for the same spots as in the CSVs:

- one section per area, in the order of `place.areas`, with the area's summary. Inside
  an area, the spots with the most sources come first;
- a card per spot: photo, category, Google Maps and website links (only when
  confirmed), description, address, local terms, and numbered source links;
- the numbered list of used sources and the rejected sources, so the numbers in the
  cards match the list.

For each spot it tries the `images` in order, the way a chat app would embed them (from
another site, following redirects), keeps the first that passes the rules in Step 5,
and rewrites it to a `https://camo.githubusercontent.com/...` URL through GitHub's
Markdown API. Some chat apps, often on mobile and web, only show images from a short
list of trusted hosts, and GitHub's image proxy is commonly on it; everywhere else the
photo shows as usual. Set `GITHUB_TOKEN` or `GH_TOKEN` to raise GitHub's rate limit;
without one it allows 60 requests an hour.

Read the warnings:

- "no working image": add candidates from other sites to the spot's `images` in
  `verified.json` or `spots.json` (rerun Step 7 if you edited `spots.json`), then rerun.
- "no area set" or "unknown area": fix the spot's `area` or `place.areas`.
- "no image could be reached": the environment probably has no internet access. Check
  the image URLs with your browsing tool, remove the ones that do not show the spot, and
  rerun with `--no-check-images`.

Without scripts (manual path): for each spot, open each image URL and keep the first
that shows the right place and follows the rules in Step 5. Use the final URL after any
redirect. Then send `{"text": "![](<url>)", "mode": "gfm"}` as a POST to
`https://api.github.com/markdown` and use the `camo.githubusercontent.com` URL from the
`<img src="...">` it returns. Write the Markdown in the layout shown in Step 9. Escape
`(`, `)` and spaces in URLs as `%28`, `%29` and `%20` so links and images render.

## Step 9: Report to the user

In the user's language, give:

1. The paths of the CSV files, and which to import (combined file, or one per layer).
2. The spots grouped by area, with photos: post the Markdown from
   `render_spots.py` as it is, in the chat, not only as a file. No table. The layout is
   made for a phone screen:

   ```markdown
   ## Töölö (Töölö)

   *A leafy residential district just north-west of the centre.*

   ### Temppeliaukion kirkko (Rock Church)

   ![Temppeliaukion kirkko (Rock Church)](https://...)

   *Sights* · [Google Maps](https://...) · [Website](https://...)

   A Lutheran church carved directly into solid granite, ...

   - **Address:** Lutherinkatu 3, 00100 Helsinki
   - **Local terms:** *kirkko* = church (KEERK-ko)
   - **Sources:** [2](https://...)
   ```

3. The source list: title, author, date and link for each used source, then the
   rejected ones with reasons. It comes right after the spots, under the heading
   "Sources used", and is part of the same Markdown. Show it in the chat, not only in
   the file.
4. Excluded spots and why they were left out.
5. How the locations were verified: Google mode or open data mode, exactly as the
   verifier reported (`verification.mode` in `verified.json`). Say the key is missing
   only if the verifier said so.
6. How to import:
   1. Open [Google My Maps](https://www.google.com/maps/d/) and create a map.
   2. In a layer, click **Import** and upload a CSV.
   3. For "Choose columns to position your placemarks", tick **Latitude** and
      **Longitude**.
   4. For "Choose a column to title your markers", choose **Name**.
   5. Repeat with a new layer for each category file, if using per-category files.
