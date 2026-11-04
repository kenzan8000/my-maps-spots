# My Maps spots skill

An agent skill that turns a place name into a [Google My Maps](https://www.google.com/maps/d/)
import file. You give it a place such as `Helsinki`. The agent reads blog posts and
articles by residents and people who actually travelled there, picks the spots they
recommend, researches each spot's background, verifies every location, and writes
CSV files you can import as map layers. It also lists the source posts it used, and
the ones it rejected.

Each pin has:

| Column | Content |
| --- | --- |
| Name | Local name, with your language's name in brackets, e.g. `Temppeliaukion kirkko (Rock Church)` |
| Local name | Local name only, to show to locals |
| Category | Layer name (Sights, Food & Drink, Nature, ...) |
| Description | Background, history and the bloggers' tips in your language, followed by useful local terms |
| Latitude, Longitude | Verified coordinates, 6 decimal places |
| Google Maps URL | Only when Google confirmed the place exists, never guessed |
| Website | Only a confirmed official website |
| Sources | The blog posts and articles that recommended the spot |

## What's in here

```
my-maps-spots/
  SKILL.md                     the skill: workflow and rules for the agent
  scripts/verify_places.py     checks coordinates, Google Maps links, websites
  scripts/build_mymaps_csv.py  writes the My Maps CSVs and the sources list
  examples/helsinki-spots.json sample input with three Helsinki spots
  .env.example                 where to put the optional API key
```

Both scripts need only Python 3.9 or newer, with no extra packages. Agents that cannot
run scripts can follow the manual steps written into `SKILL.md`.

## Install

`SKILL.md` uses the open Agent Skills format (a folder with a `SKILL.md` file and
`name`/`description` frontmatter). Copy the whole `my-maps-spots` folder:

| Agent | Where |
| --- | --- |
| Claude Code | `~/.claude/skills/my-maps-spots/` (or `.claude/skills/` in a project) |
| Claude apps | Zip the folder and upload it in the Skills section of Settings |
| Cursor | `~/.cursor/skills/my-maps-spots/` (or `.cursor/skills/` in a project) |
| Codex CLI | `~/.codex/skills/my-maps-spots/` |
| Anything else | Paste `SKILL.md` into the chat or the agent's custom instructions |

Then ask the agent something like "Make a My Maps file for Helsinki". It needs web
search and page reading to find the blog posts.

## Google Maps API key (optional, recommended)

Without a key, coordinates are checked against OpenStreetMap and Wikidata, which is
accurate, but the **Google Maps URL** column stays empty. Without a key nothing has
confirmed the place exists on Google Maps, and the skill never guesses links. With a
key, each spot is matched with Google Places, so pins and links line up exactly with
Google Maps.

### Getting a key

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project and
   set up billing. Google's monthly free usage typically covers personal use, since one
   city run makes only a few dozen requests. Check the current
   [pricing](https://developers.google.com/maps/billing-and-pricing/pricing).
2. Enable **Places API (New)** under APIs & Services > Library.
3. Under APIs & Services > Credentials, create an API key. Edit it and, under
   **API restrictions**, allow only **Places API (New)**.
4. Under APIs & Services > Places API (New) > Quotas, set a low daily request limit,
   and add a budget alert under Billing. Then a runaway agent can't run up costs.

### Giving the key to the skill

The key is never written into `SKILL.md`. The verifier looks for it in this order:

1. **The environment variable `GOOGLE_MAPS_API_KEY`.** Every agent can use this.

   ```bash
   # ~/.zshrc or ~/.bashrc
   export GOOGLE_MAPS_API_KEY="your-key"
   ```

   Cloud or hosted agents usually have a secrets setting. Add a secret named
   `GOOGLE_MAPS_API_KEY` there.

2. **A `.env` file in the skill folder.** Copy `.env.example` to `.env` and fill it
   in. `.env` is git-ignored.

Don't paste the key into the chat; the skill is written to never ask for it there.

## Running the scripts yourself

The agent normally runs these. To try them on the bundled example:

```bash
cd my-maps-spots
mkdir -p output/helsinki
cp examples/helsinki-spots.json output/helsinki/spots.json
python3 scripts/verify_places.py output/helsinki/spots.json
python3 scripts/build_mymaps_csv.py output/helsinki/verified.json
```

Output in `output/helsinki/`:

- `helsinki-all.csv`: all spots, for a single layer
- `helsinki-<category>.csv`: one file per category, for one layer each
- `sources.md`, `sources.csv`: every source read, used or rejected, and the spots from it
- `excluded.csv`: spots that could not be verified, and why

Useful options for `verify_places.py`:

- `--mode google|osm`: force a mode (default `auto`)
- `--margin-km 15`: how far outside the place a spot may be, for day trips
- `--tolerance-m 150`: how close two independent sources must agree in open data mode

The sample's blog URLs are `example.com` placeholders; real runs list the actual posts.

## Importing into Google My Maps

1. Open [Google My Maps](https://www.google.com/maps/d/) and click **Create a new map**.
2. In the first layer, click **Import** and upload a CSV.
3. Under "Choose columns to position your placemarks", tick **Latitude** and **Longitude**.
4. Under "Choose a column to title your markers", choose **Name**.
5. For one layer per category, click **Add layer** and repeat with each category file.
   A map can have up to 10 layers.

Every other column appears in the pin's details, and the URLs are clickable.

## Data sources

- [OpenStreetMap Nominatim](https://nominatim.org/) (data under ODbL), used at most one
  request per second as its usage policy requires
- [Wikidata](https://www.wikidata.org/) (CC0)
- [Google Places API (New)](https://developers.google.com/maps/documentation/places/web-service/text-search),
  when a key is configured
