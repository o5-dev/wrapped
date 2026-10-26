# Wrapped

A Discord bot that turns a channel's last 30 days into a stats card (total messages, top chatter, favorite emoji).
The card has a QR code that opens it on a web page, where you can copy the link or download the picture.

## Command

`/wrapped [channel] [days]` reads the channel (default: the current one, 30 days, up to 90) and posts the card as a picture with an **Open card** button.

- Only messages from people count. Bots, webhooks, joins and pins are skipped.
- Favorite emoji is the most used reaction in the channel.
- You can only make a card for a channel you can read yourself.
- It reads at most 20,000 messages per card. In a busier channel the card covers a shorter window and says so.
- Each person can use the command once a minute.
- Nothing is stored. The bot counts while it reads and never looks at message text.

## Discord settings

- Privileged intents: all off
- Install scopes: `bot` and `applications.commands`
- Bot permissions: View Channels, Read Message History, Attach Files (the invite link on the website already has these)
- Public Bot: on, so anyone can use the invite link

## Run your own copy

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python -m bot
```

On Mac or Linux activate with `source .venv/bin/activate`. On Linux also run `playwright install-deps chromium`.

1. Create an app in the Discord Developer Portal, add a bot and copy its token.
2. Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN`.
3. Put your test server's ID in `DEV_GUILD_ID` while developing so the command shows up instantly. Leave it empty when you deploy.
4. Put your site address in `docs/config.js` (see below), otherwise the QR code and the button have no working link.
5. Keep `python -m bot` running somewhere that stays on, like a Hack Club Nest server or any VPS.

Tests: `python -m pytest tests`

## The website (GitHub Pages)

The `docs` folder is the website.

1. Push the repo, then open Settings, Pages, choose the `main` branch and the `/docs` folder.
2. Put the address of the card page in `docs/config.js`, for example `https://you.github.io/wrapped-bot/card.html`.
3. Run `python -m bot.render --demo docs/example-card.png --scale 2` so the example on the homepage has a QR code that points to your site.

The homepage (`index.html`) has the **Add to Discord** button. If you change the invite link, change it in `index.html` and `card.html`.

## How it works

```
/wrapped -> scan.py reads the channel -> stats.py counts -> cardlink.py packs the numbers into a link
         -> render.py opens card.html in a headless browser and takes a picture of the card
```

Everything on a card is packed into the web address after the `#`, so there is no database. Every link is its own card.
The page only ever shows that data as plain text, so an edited link can't run anything.

Try the card without Discord:

```
python -m bot.render --demo card.png
python -m bot.render --demo-long card.png
python -m http.server -d docs 8000
```

Then open `http://localhost:8000/card.html?demo` (or `?demo=long`).

## Files

```
docs/
  index.html    homepage
  card.html     the card page (what the QR code opens)
  style.css     page style and fonts
  card.css      the card
  card.js       fills in the card, QR code, copy and download buttons
  config.js     the address of card.html
  vendor/       qrcode-generator and html-to-image
  fonts/        Inter
bot/
  main.py       the bot and the /wrapped command
  scan.py       reads the channel history
  stats.py      counts messages and emoji
  cardlink.py   packs the numbers into a link
  render.py     turns a link into a picture
  config.py     reads .env and docs/config.js
tests/
```
