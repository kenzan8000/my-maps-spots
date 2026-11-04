---
name: my-maps-spots
description: Build a Google My Maps import (CSV) of spots for a place, sourced from first-hand travel blogs and articles by locals and travellers. Use when the user wants map pins, a travel map, or a My Maps CSV with verified coordinates, descriptions, local names, Google Maps links, official websites, and the source posts. The place name may come later; if it is not given, ask for it in the chat.
---

# My Maps spots from first-hand travel writing

Turn a place name into CSV files that import cleanly into Google My Maps. Every pin
comes from real blog posts or articles written by residents or people who actually
travelled there, carries an accurate location, and lists the posts it came from.

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
the location.

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
    "local_language": "fi"
  },
  "spots": [
    {
      "id": "temppeliaukio",
      "name": "Temppeliaukion kirkko (Rock Church)",
      "local_name": "Temppeliaukion kirkko",
      "category": "Sights",
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

## Step 7: Verify locations, links and websites

### With scripts (preferred)

The scripts use only the Python 3 standard library. Paths are relative to this skill's
folder.

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

If there is no key, tell the user once that a Google Maps API key gives verified
Google Maps links (setup is in the README next to this file). Offer to continue
without one. **Never ask the user to paste a key into the chat.**

Then read `verified.json`. Each spot has `verification.status`:

- `verified`: safe to pin.
- `unconfirmed` or `not_found`: read `verification.notes`. You may fix
  `search_query`, `local_name`, `address` or `wikidata` in `spots.json` and rerun.
  Do not force a pin. Spots that remain unverified are excluded and reported.

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

## Step 8: Build the CSVs

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
Name,Local name,Category,Description,Latitude,Longitude,Google Maps URL,Website,Sources
```

- `Description`: the description text, then a blank line, then
  `Local terms: kirkko = church (KEERK-ko); temppeliaukio = temple square`.
- `Sources`: source URLs separated by single spaces.
- Empty cells for unknown links. Never fill them with guesses.

## Step 9: Report to the user

In the user's language, give:

1. The paths of the CSV files, and which to import (combined file, or one per layer).
2. A table of the spots: name, category, and whether a Google Maps link and website
   were found.
3. The source list: title, author, date and link for each used source, then the
   rejected ones with reasons. Show this in the chat, not only in the file.
4. Excluded spots and why they were left out.
5. How to import:
   1. Open [Google My Maps](https://www.google.com/maps/d/) and create a map.
   2. In a layer, click **Import** and upload a CSV.
   3. For "Choose columns to position your placemarks", tick **Latitude** and
      **Longitude**.
   4. For "Choose a column to title your markers", choose **Name**.
   5. Repeat with a new layer for each category file, if using per-category files.
