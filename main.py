import logging
from os.path import isfile
from os import system, getenv
from time import time

from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument, DocumentAttributeSticker, DocumentAttributeAnimated, MessageMediaPhoto, Message
from telethon import events
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Credentials
API_ID = getenv("API_ID")
if API_ID is None or not API_ID:
    raise ValueError("API_ID must be set")

API_HASH = getenv("API_HASH")
if API_HASH is None or not API_HASH:
    raise ValueError("API_HASH must be set")

BOT_TOKEN = getenv("BOT_TOKEN")
if BOT_TOKEN is None or not BOT_TOKEN:
    raise ValueError("BOT_TOKEN must be set")

PIN_CODE = getenv("PIN_CODE")
if PIN_CODE is None or not PIN_CODE:
    raise ValueError("PIN_CODE must be set")

OWNER_USERNAME = getenv("OWNER_USERNAME")

# Media logging
LOGGING = getenv("LOGGING")
LOG_CHANNEL_ID = int(getenv("LOG_CHANNEL_ID"))

if LOGGING and LOG_CHANNEL_ID is None:
    raise ValueError("LOG_CHANNEL_ID must be set if LOGGING is enabled")

client = TelegramClient("bot", API_ID, API_HASH)
client.start(bot_token=BOT_TOKEN)

# Put user ids of people that you want to force cooldowns (respectively, no limits and banned account)
# e.g. 123456789: [0, 0], 23456789: [time(), 999999999]}
cooldown: dict[int, list[float, float]] = {}

@client.on(events.NewMessage(pattern="^/start"))
async def welcome(ev):
    await ev.respond(f"Hello!\nWelcome to **{OWNER_USERNAME}'s label printer**!")

    if PIN_CODE:
        await ev.respond("To unlock this bot, please enter the pin code written on the printer!")
        return

    cooldown[ev.message.peer_id.user_id] = [0, 5] # Set cooldown as 5 secs

# This one triggers on a single message with the pin code written
@client.on(events.NewMessage(pattern=PIN_CODE))
async def pin(ev):
    cooldown[ev.message.peer_id.user_id] = [0, 5] # Set cooldown as 5 secs
    await ev.respond("**Printer has been unlocked. Please only print NSFW pictures if you are there to pick them up RIGHT AWAY. You may now print Stickers and Pictures! Have fun!**")

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private and e.message.media))
async def handler(ev: events.NewMessage.Event):
    msg: Message = ev.message

    if msg.peer_id.user_id not in cooldown:
        await ev.respond("You need to unlock the printer first by writing the pin code!")
        return

    if time()-cooldown[msg.peer_id.user_id][0] < cooldown[msg.peer_id.user_id][1]:
        time_left = int(cooldown[msg.peer_id.user_id][1]-(time() - cooldown[msg.peer_id.user_id][0]))

        await ev.respond(f"Woo calm down fam!\n\nSend the sticker again in {time_left//60} minutes {time_left%60} seconds")
        return

    # Cache the media locally
    fn = None
    if isinstance(msg.media, MessageMediaPhoto):
        fn = f"photo/{msg.media.photo.id}.jpg"

    elif isinstance(msg.media, MessageMediaDocument):
        for att in msg.media.document.attributes:
            if isinstance(att, DocumentAttributeSticker):
                fn = f"doc/{msg.media.document.id}.webp"
            if isinstance(att, DocumentAttributeAnimated):
                fn = None
                break

    if not fn:
        await ev.respond("Cannot print this. Try with a sticker or a picture.")
        return

    if not isfile(fn):
        await client.download_media(msg, file=fn)

    img = Image.open(fn)

    # Limit stickers ratio to 1:10 (so people don"t print incredibly long stickers)
    if img.size[1]/img.size[0] > 10:
        await ev.respond("That image is too tall. It would waste a lot of paper. Please give me a shorter image.")
        return

    # Make transparent backgrounds white
    if img.mode == "RGBA":
        white = Image.new(img.mode, img.size, "white")
        img = Image.alpha_composite(white, img)

    # Resize the image (only width is important here)
    img.thumbnail([696, 9999], resample=Image.Resampling.LANCZOS, reducing_gap=None)

    # Convert to grayscale and apply a gamma of 1.8 (try also 2.2)
    img = img.convert("L")
    img = Image.eval(img, lambda x: int(255*pow((x/255),(1/1.8))))
    img.save("tmp.png", "PNG")

    # Before running, give access to /dev/usb/lp0 to the user you run the bot as
    status_code = system(f"brother_ql -m QL-650TD -b pyusb -p usb://0x04f9:0x20c0/000D9Z773892 print -l 62 tmp.png -d")
    if status_code == 0:
        cooldown[msg.peer_id.user_id][0] = time()
        cooldown[msg.peer_id.user_id][1] = min(cooldown[msg.peer_id.user_id][1]*1.2, 30)

        await ev.respond("Your sticker has finished printing now! Enjoy it :3")

        if LOGGING and LOG_CHANNEL_ID:
            log_channel = await client.get_entity(LOG_CHANNEL_ID)
            await client.forward_messages(log_channel, msg)
            await client.send_message(log_channel, str(msg.peer_id.user_id))
    else:
        await ev.respond(f"Whoops, there was a problem printing your sticker. Please call {OWNER_USERNAME}")
        await client.send_message(OWNER_USERNAME, "Printer is not working")

client.flood_sleep_threshold = 24*60*60
client.run_until_disconnected()
