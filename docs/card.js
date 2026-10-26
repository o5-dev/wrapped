var CARD_WIDTH = 667;
var CARD_HEIGHT = 711;
var EMOJI_URL = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@15.1.0/assets/svg/";
var EMPTY_IMAGE = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==";

var SILHOUETTE = '<svg viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg">' +
    '<rect width="240" height="240" fill="#d9d9d5"/>' +
    '<g fill="none" stroke="#262624" stroke-width="11">' +
    '<circle cx="120" cy="92" r="31"/>' +
    '<path d="M36 214 A84 62 0 0 1 204 214"/>' +
    '</g></svg>';

var demos = {
    normal: {
        server: "Hack Club",
        channel: "general",
        days: 30,
        date: "2026-10-26",
        total: 54045,
        name: "username",
        userId: "",
        avatar: "",
        emoji: "😂"
    },
    long: {
        server: "The Extremely Long Server Name That Keeps Going",
        channel: "super-duper-long-channel-name-here",
        days: 30,
        date: "2026-10-26",
        total: 1234567890,
        name: "Řehoř Žlutoučký-Kůň the Magnificent",
        userId: "",
        avatar: "",
        emoji: "👨‍👩‍👧‍👦"
    }
};

function cut(text, max) {
    var letters = Array.from(String(text));
    if (letters.length <= max) {
        return letters.join("");
    }
    return letters.slice(0, max - 1).join("") + "…";
}

function cleanEmoji(value) {
    var emoji = cut(value, 24);
    if (/^:\d{1,20}$/.test(emoji)) {
        return emoji;
    }
    if (emoji.charAt(0) === ":") {
        return "";
    }
    return emoji;
}

function decodePayload(payload) {
    var base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    while (base64.length % 4 !== 0) {
        base64 += "=";
    }
    var binary = atob(base64);
    var bytes = Uint8Array.from(binary, function (letter) {
        return letter.charCodeAt(0);
    });
    var list = JSON.parse(new TextDecoder().decode(bytes));
    if (!Array.isArray(list) || list[0] !== 1) {
        throw new Error("bad link");
    }
    return {
        server: cut(list[1], 40),
        channel: cut(list[2], 32),
        days: Number(list[3]) || 30,
        date: /^\d{4}-\d{2}-\d{2}$/.test(list[4]) ? list[4] : "",
        total: Math.max(0, Math.floor(Number(list[5]) || 0)),
        name: cut(list[6], 32),
        userId: /^\d{1,20}$/.test(list[7]) ? list[7] : "",
        avatar: /^(a_)?[a-f0-9]{32}$/i.test(list[8]) ? list[8] : "",
        emoji: cleanEmoji(list[9])
    };
}

function encodePayload(card) {
    var list = [1, card.server, card.channel, card.days, card.date, card.total, card.name, card.userId, card.avatar, card.emoji];
    var bytes = new TextEncoder().encode(JSON.stringify(list));
    var binary = "";
    for (var i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function getShareLink(payload) {
    var base = SHARE_BASE;
    var notSet = base.indexOf("YOUR-USERNAME") !== -1;
    var onWeb = window.location.protocol.indexOf("http") === 0;
    if (notSet && onWeb) {
        base = window.location.origin + window.location.pathname;
    }
    return base + "#" + payload;
}

function formatDate(milliseconds) {
    return new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        timeZone: "UTC"
    }).format(new Date(milliseconds));
}

function periodText(card) {
    var text = "Last " + card.days + " days";
    if (card.days === 1) {
        text = "Last day";
    }
    if (card.date === "") {
        return text;
    }
    var end = Date.parse(card.date + "T00:00:00Z");
    var start = end - card.days * 86400000;
    return text + " · " + formatDate(start) + " – " + formatDate(end);
}

function makeSlug(text) {
    var slug = text.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    if (slug === "") {
        return "card";
    }
    return slug;
}

function say(text) {
    document.getElementById("message").textContent = text;
}

function loadImage(url) {
    return new Promise(function (resolve, reject) {
        var image = new Image();
        image.crossOrigin = "anonymous";
        image.onload = function () {
            resolve(image);
        };
        image.onerror = reject;
        setTimeout(reject, 8000);
        image.src = url;
    });
}

function loadFonts(card) {
    return Promise.all([
        document.fonts.load("300 65px Inter", "#" + card.channel),
        document.fonts.load("400 22px Inter", "Total Messages Top Chatter Favorite Emoji Share it!"),
        document.fonts.load("700 68px Inter", card.name + "@0123456789,"),
        document.fonts.load("700 32px Inter", "Scan the QR")
    ]).then(function () {
        return document.fonts.ready;
    }, function () {});
}

function shrinkToFit(element, maxWidth) {
    element.classList.remove("cut");
    element.style.fontSize = "";
    element.style.maxWidth = "";
    var startSize = parseFloat(getComputedStyle(element).fontSize);
    var smallest = startSize * 0.4;
    var size = startSize;
    var tries = 0;
    while (element.offsetWidth > maxWidth + 0.5 && tries < 4 && size > smallest) {
        size = Math.max(smallest, size * maxWidth / element.offsetWidth * 0.995);
        element.style.fontSize = size + "px";
        tries++;
    }
    if (element.offsetWidth > maxWidth + 0.5) {
        element.classList.add("cut");
        element.style.maxWidth = maxWidth + "px";
    }
}

function drawQr(box, text) {
    var qr = qrcode(0, "L");
    qr.addData(text, "Byte");
    qr.make();
    var count = qr.getModuleCount();
    var margin = 1;
    var size = count + margin * 2;
    var path = "";
    for (var row = 0; row < count; row++) {
        var col = 0;
        while (col < count) {
            if (!qr.isDark(row, col)) {
                col++;
                continue;
            }
            var length = 1;
            while (col + length < count && qr.isDark(row, col + length)) {
                length++;
            }
            path += "M" + (col + margin) + " " + (row + margin) + "h" + length + "v1h-" + length + "z";
            col += length;
        }
    }
    box.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + size + " " + size + '" shape-rendering="crispEdges">' +
        '<path d="' + path + '" fill="#262624"/></svg>';
}

function showAvatar(card) {
    var box = document.getElementById("avatar");
    box.innerHTML = SILHOUETTE;
    if (card.userId === "" || card.avatar === "") {
        return Promise.resolve();
    }
    var url = "https://cdn.discordapp.com/avatars/" + card.userId + "/" + card.avatar + ".png?size=512";
    return loadImage(url).then(function (image) {
        box.innerHTML = "";
        box.appendChild(image);
    }, function () {});
}

function emojiImageUrl(emoji) {
    var codes = Array.from(emoji).map(function (letter) {
        return letter.codePointAt(0).toString(16);
    });
    if (codes.indexOf("200d") === -1) {
        codes = codes.filter(function (code) {
            return code !== "fe0f";
        });
    }
    return EMOJI_URL + codes.join("-") + ".svg";
}

function showEmoji(emoji) {
    var box = document.getElementById("emoji");
    box.className = "emoji";
    box.textContent = "";
    if (emoji === "") {
        box.textContent = "—";
        return Promise.resolve();
    }
    var isCustom = emoji.charAt(0) === ":";
    var url = emojiImageUrl(emoji);
    if (isCustom) {
        url = "https://cdn.discordapp.com/emojis/" + emoji.slice(1) + ".png?size=128";
    }
    return loadImage(url).then(function (image) {
        box.appendChild(image);
    }, function () {
        if (isCustom) {
            box.textContent = "—";
        } else {
            box.textContent = emoji;
            box.className = "emoji native";
        }
    });
}

function fitToScreen() {
    var scale = Math.min(1, (window.innerWidth - 54) / CARD_WIDTH);
    document.getElementById("card-box").style.width = (CARD_WIDTH * scale) + "px";
    document.getElementById("card-box").style.height = (CARD_HEIGHT * scale) + "px";
    document.getElementById("card").style.transform = "scale(" + scale + ")";
}

function copyLink(link) {
    if (!navigator.clipboard) {
        say("Could not copy, please copy the link from the address bar");
        return;
    }
    navigator.clipboard.writeText(link).then(function () {
        say("Link copied");
    }, function () {
        say("Could not copy, please copy the link from the address bar");
    });
}

function downloadImage(card) {
    say("Making the image...");
    htmlToImage.toPng(document.getElementById("card"), {
        pixelRatio: 3,
        width: CARD_WIDTH,
        height: CARD_HEIGHT,
        imagePlaceholder: EMPTY_IMAGE,
        style: { transform: "none" }
    }).then(function (dataUrl) {
        var link = document.createElement("a");
        link.href = dataUrl;
        link.download = "wrapped-" + makeSlug(card.channel) + ".png";
        link.click();
        say("Image saved");
    }).catch(function () {
        say("Could not make the image, a screenshot works too");
    });
}

function showPage() {
    var params = new URLSearchParams(window.location.search);
    var isRender = params.has("render");
    if (isRender) {
        document.body.className = "render";
    }

    var payload = window.location.hash.slice(1);
    if (payload === "" && params.has("demo")) {
        if (params.get("demo") === "long") {
            payload = encodePayload(demos.long);
        } else {
            payload = encodePayload(demos.normal);
        }
    }

    var card = null;
    try {
        if (payload !== "") {
            card = decodePayload(payload);
        }
    } catch (error) {
        card = null;
    }

    if (card === null) {
        document.getElementById("broken").style.display = "block";
        window.cardReady = true;
        return;
    }

    document.getElementById("content").style.display = "block";
    document.title = card.server + " · Wrapped";
    document.getElementById("server-name").textContent = card.server;
    document.getElementById("period").textContent = periodText(card);

    var total = new Intl.NumberFormat("en-US").format(card.total);
    var link = getShareLink(payload);
    document.getElementById("channel").textContent = card.channel;
    document.getElementById("total").textContent = total;
    document.getElementById("chatter").textContent = "@" + card.name;
    document.getElementById("card").setAttribute("aria-label", "Wrapped for #" + card.channel + ": " + total + " messages, top chatter @" + card.name);
    drawQr(document.getElementById("qr"), link);

    if (!isRender) {
        fitToScreen();
        window.addEventListener("resize", fitToScreen);
    }

    document.getElementById("copy-button").onclick = function () {
        copyLink(link);
    };
    document.getElementById("download-button").onclick = function () {
        downloadImage(card);
    };

    loadFonts(card).then(function () {
        shrinkToFit(document.getElementById("channel"), 440);
        shrinkToFit(document.getElementById("total"), 418);
        shrinkToFit(document.getElementById("chatter"), 562);
        return Promise.all([showAvatar(card), showEmoji(card.emoji)]);
    }).then(function () {
        window.cardReady = true;
    });
}

showPage();
