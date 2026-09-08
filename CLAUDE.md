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
