# Wrapped

A Discord bot that turns a channel's last 30 days into a shareable stats card
(total messages, top chatter, favorite emoji). The card has a QR code that opens it on a web page,
where you can copy the link or download the picture.

## Commands

| Command | What it does |
|---|---|
| `/wrapped [channel] [days]` | Reads the channel (default: the current one, 30 days, max 90) and posts the card as a PNG with an **Open card** button |

- Counts messages from people only (bots, webhooks, joins and pins are skipped).
- Favorite emoji = the most-used **reaction** in the channel.
- You can only make a card for a channel you can read yourself.
- It reads at most 20,000 messages per card; in a busier channel the card covers a shorter window and says so.
- The same channel and days are served from memory for 15 minutes.

**Nothing is stored.** The bot counts while it reads and throws the messages away; it never looks at message text.

## Discord permissions

- **Privileged intents:** none needed (leave all three off).
- **Install scopes:** `bot`, `applications.commands`
- **Bot permissions:** View Channels, Read Message History (the bot needs these in the channel it reads)
- The bot must be **Public** so anyone can use the invite link.

## Run your own copy

```bash
git clone <this repo> && cd wrapped-bot
python -m venv .venv && source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium                              # on Linux also: playwright install-deps chromium

cp .env.example .env                                     # then paste your bot token into .env
python -m bot
```

1. Create an app at the [Developer Portal](https://discord.com/developers/applications), add a bot, copy its token into `.env`.
2. Set `DEV_GUILD_ID` in `.env` to your test server's ID while developing (commands appear instantly).
3. Deploy the card page (below) and set `SHARE_BASE` in `docs/config.js`, otherwise the QR code and the button have no working link.
4. Keep `python -m bot` running somewhere that stays on (a Hack Club Nest server works, or any VPS).

Tests: `python -m pytest tests`

## How it fits together

```
/wrapped ──► scan.py reads the channel  ──► stats.py counts  ──► cardlink.encode_card()  ──► payload string
                                                                                                │
                    ┌───────────────────────────────────────────────────────────────────────────┤
                    ▼                                                                           ▼
   render.py opens docs/index.html?render#payload                    QR code on the card points to
   in headless Chromium and screenshots the card ──► PNG in Discord  https://<you>.github.io/wrapped-bot/#payload
                                                                     (same page, with Copy link / Download)
```

There is **one** card template (`docs/index.html` + `card.css` + `card.js`). The bot and the website both use it.

### No database, no card IDs

Everything the card shows is packed into the URL after the `#`:

```
[1, server, channel, days, endDate, total, name, userId, avatarHash, emoji]  →  JSON  →  base64url
```

So every link is its own card, GitHub Pages only has to serve static files, nothing is stored, and the part
after `#` is never sent to any server. Anyone could edit a link to fake a card; that's fine for a fun stats toy.
The page treats the link as untrusted: text is only inserted as text, IDs are validated before they go into image URLs.

## Files

```
docs/                  ← this folder is what GitHub Pages serves
  index.html           viewer page + the card markup
  card.css             the card (fixed 667×711, positioned in px like in Figma) + Inter fonts
  page.css             page around the card (not in the PNG)
  card.js              decodes the link, fits text, draws QR, copy/download buttons
  config.js            SHARE_BASE, INVITE_URL
  vendor/              qrcode-generator, html-to-image (copied from npm, no CDN needed)
  fonts/               Inter 300/400/700, latin + latin-ext (Czech etc.)
bot/
  main.py              the bot and the /wrapped command
  scan.py              reads channel history newest-first, stops at the cutoff / message cap
  stats.py             Tally: total, top chatter, favorite emoji (counters only)
  cardlink.py          encode_card(), share_url()
  render.py            CardRenderer + CLI: payload → PNG
  config.py            .env + SHARE_BASE from docs/config.js
tests/test_scan.py
```

Try the card without Discord:

```bash
python -m bot.render --demo card.png          # sample card
python -m bot.render --demo-long card.png     # long names → text scales down, then "…"
python -m http.server -d docs 8000            # then open http://localhost:8000/?demo  (or ?demo=long)
```

## Deploy the card page (GitHub Pages)

1. Push the repo, then **Settings → Pages → Deploy from a branch → `main` / `/docs`**.
2. Put the resulting URL in `docs/config.js` as `SHARE_BASE` (this is what the QR code points to).
3. Optional: set `INVITE_URL` to show an "Add Wrapped to your server" link under the card.

## Notes

- Text limits (px) before it scales down: channel 440, total 418, top chatter 562 (`LIMITS` in `card.js`). Below 40% size it is cut with "…".
- Unicode emoji are Twemoji images from jsDelivr (same look everywhere); if that fails the plain emoji character is shown instead.
- Avatars come from Discord's CDN. Without an avatar the card shows the grey silhouette.
- Fonts: Inter, SIL Open Font License (see `docs/fonts/LICENSE`).
