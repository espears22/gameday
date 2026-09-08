# Gameday — glanceable live scores for the Tesla center screen

## What this is

A single static HTML page that a Tesla owner bookmarks in the car's browser. It shows
one game — their team's — at a size readable at arm's length while the car is moving.
No app, no install, no account.

The competitor is not ESPN's data. It's ESPN's *website*, which loads fine in the Tesla
browser but is a dense desktop page with ads and 14px type that takes three taps to
reach one game. This product is: open bookmark, correct game already on screen, zero taps.

**Hard deadline: NFL Week 1. Colts host Baltimore Sunday Sept 13, 1:00pm ET.**
Everything below is scoped to that date.

## Decisions already made — do not relitigate

- **No backend, no database, no accounts.** Static file on a CDN. Marginal cost per
  user must stay at zero. This is the entire business model: we can offer an unlimited
  free tier because serving one more user costs nothing.
- **No LLM anywhere in the product.** A wrong score confidently displayed on a screen
  someone glances at while driving is the worst possible failure. Deterministic code only.
- **No localStorage or sessionStorage.** Config comes from URL query params:
  `?team=IND&league=football/nfl`. This is deliberate — Tesla syncs bookmarks across
  vehicles and profiles, so the URL *is* the user's saved settings, and it survives
  into loaners and rentals.
- **No Tesla Fleet API in v1.** Fleet API is pay-per-use and `media_info` sits on the
  expensive `vehicle_data` endpoint. Registering also requires legal business details,
  a hosted public key, and a payment method on file. That's a week of friction we don't
  have. Auto-detect is a later premium feature, not v1.
- **Data source is ESPN's undocumented endpoint** — prototype only:
  `https://site.api.espn.com/apis/site/v2/sports/{league}/scoreboard`
  No auth. Unlicensed. Fine for validating demand, must be replaced with a licensed
  feed before charging anyone.

## Task order — do these strictly in sequence

1. **Deploy `index.html` to Vercel.** Nothing else until it's live at a real URL.
2. **Test CORS from the deployed domain.** This is the only thing that can kill the
   architecture. If ESPN's endpoint refuses cross-origin requests from the browser,
   write a minimal Vercel edge function to proxy it and cache responses for 10s.
   Report back what happened before building anything else.
3. **Fix sizing against a real screenshot from the car.** Everything is `vh`/`clamp()`
   but the usable viewport in Tesla's browser is unknown. Do not guess — wait for the
   screenshot.
4. Stop. Ship. Week 1 is the test.

## Design constraints

The reader is glancing for well under a second while driving. Design accordingly.

- Score numerals are the hero, roughly a quarter of the viewport height, tabular figures.
- Possession is shown as a lit rail under the team with the ball. This is the primary
  glanceable signal — it must be readable in peripheral vision without reading any text.
- Dark background always. The screen is bright and often used at night.
- No hover states, no small tap targets, no scrolling, no modals, no onboarding.
- Team colors come live from the API (`competitor.team.color`, bare hex, needs `#`)
  and tint each half of the screen. The app takes on the team's identity automatically.
- Red zone turns the situation band red.
- Poll every 20s when a game is live, every 5 minutes otherwise. Never faster.

## Failure states matter more than usual

Someone is looking at this in a moving car. Every state must be legible and calm.

- No game today → say so, plus when the next one is.
- Network failure → say what happened and that it's retrying. Never a spinner forever,
  never a stack trace, never a blank screen.
- Parse failure → fall back to whatever fields did resolve. Use optional chaining
  everywhere; ESPN's shape varies by sport and game state.

## Explicitly out of scope for v1

Do not build these even if they seem easy:

- Fantasy overlay (Week 3, and use Sleeper's public API — not ESPN's, which needs
  scraped auth cookies and breaks constantly)
- Multi-game RedZone view
- Tesla Fleet API auto-detect
- Any betting odds or wager display — regulatory problem, and it undermines being
  trustworthy at a glance
- Anything that bypasses Tesla's driving lockouts. That's a safety restriction, not
  an obstacle. Non-negotiable.

## Stack

Plain HTML, CSS, vanilla JS in one file. No framework, no build step, no dependencies.
It has to load fast over a car's cellular connection. Keep it that way.

## Fantasy play alerts — spec

Ships after Week 1 validates. Do not start before the score screen has rendered
against a live NFL game and been tuned to a real Tesla screenshot.

Superseded the earlier team-totals-only "Fantasy overlay" spec — this version
adds the play-level alert, which is the actual point of the feature.

### The feature

Not a fantasy scoreboard. A **play-level alert**.

ESPN's `situation.lastPlay.text` names the players involved in the play that just
happened. The user's Sleeper roster is a list of player IDs. Intersect them:

    JONATHAN TAYLOR  14 YD TD          +7.2

When a play involves someone on the user's roster, surface it. Otherwise show
nothing extra. This is the one feature in this product that a bookmark to ESPN
cannot replace, and it's the reason someone opens this instead of anything else.

Team totals ("Me 87.4 — Kyle 62.1") are secondary. Show them small in the band.
The alert is the product.

### Scope: Sleeper only

ESPN fantasy needs `SWID` / `espn_s2` session cookies lifted from the user's own
browser — a trust problem and permanently fragile. Yahoo needs OAuth, which means
secrets, token storage, and a backend, which introduces per-user cost and kills
the unlimited free tier. Sleeper's reads need no auth, so the app stays static.

Revisit only if real users ask.

**Survivor / Pick'em is out.** Sleeper runs those products but exposes no
documented endpoints for them. If an undocumented one turns up in the network tab,
treat it as a bonus, never a dependency.

**Sports betting is out.** Not buildable (books don't expose user positions to
third parties), regulated per-state, and wrong for a screen whose whole value is
being trustworthy at a glance.

### Data flow

Base: `https://api.sleeper.app/v1` — read-only, no key. Stay well under 1000
calls/min; they IP-block.

Session setup, cached in memory after first load:

1. `GET /state/nfl` → current `week`. Never hardcode it.
2. `GET /user/{username}` → `user_id`
3. `GET /user/{user_id}/leagues/nfl/{season}` → league list
4. `GET /league/{league_id}/rosters` → match `owner_id` to `user_id` to get
   `roster_id` and the user's `players` array
5. `GET /league/{league_id}/matchups/{week}` → entries carry `roster_id`,
   `matchup_id`, and `points` already computed against that league's scoring
   settings. The two entries sharing a `matchup_id` are the head-to-head pair.

Only step 5 re-polls.

### Player name mapping — build step, not runtime

The full `/players/nfl` dump is ~5MB and Sleeper says not to fetch it more than
once a day. Never call it from the browser.

Instead, generate a trimmed static `players.json` at build time using the filters
(`?position=QB&active=true`, and so on for RB/WR/TE/K/DEF). Keep only `player_id`,
full name, and team. Commit it. Refresh weekly.

### Name matching is the hard part — treat it as such

ESPN writes plays as prose; Sleeper stores structured names. They will not match
cleanly. Normalize aggressively: casefold, strip punctuation and suffixes
(Jr., III), and match on last name plus first initial plus NFL team.

**A false positive is worse than a miss.** Telling someone their player scored
when he didn't destroys the only thing this product sells, which is being right at
a glance. When the match is ambiguous, show nothing.

Log unmatched plays during Weeks 1 and 2 and tune against real data rather than
guessing at the rules up front.

### Config

Extends the existing URL-param pattern. No storage, no accounts:

```
?team=IND&sleeper=evanspears&league_id=123456789
```

`league_id` optional — default to the first NFL league of the current season.
Include it so people in several leagues can bookmark each separately.

### Display

- **Alert:** replaces the last-play line when a rostered player is involved.
  Larger than the normal last-play text, held for ~20s, then decays back.
  One line. Never a list.
- **Totals:** small, in the band, alongside the game situation. Highlight
  whichever side leads.
- Do **not** render a per-player roster breakdown. Nine players with individual
  scores is not glanceable, and glanceable is the entire product.

### Failure behaviour

Strictly additive. If the `sleeper` param is missing, the username doesn't
resolve, or Sleeper is down: render the score screen exactly as it is today, with
no band, no alert, and no error message. **A fantasy failure must never degrade
the score screen.** That screen is the product; this attaches to it.

### Polling

30s while a game is live, 5 minutes otherwise.
