import asyncio
import logging
import os
import time
from datetime import timedelta
from pyrogram import Client, filters, idle, enums
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from youtubesearchpython import VideosSearch
from pyrogram.types import Message
from pyrogram.errors import ChatAdminRequired, FloodWait, UserNotParticipant, UserAdminInvalid, UserAlreadyParticipant
import json
import subprocess
import requests
import random
import aiohttp
from PIL import Image, ImageDraw, ImageFont
from flask import Flask
import threading
from pytgcalls.exceptions import AlreadyJoinedError, GroupCallNotFound, NoActiveGroupCall



app = Flask(__name__)

@app.route('/health')
def health():
    return 'OK', 200

def run_server():
    app.run(host='0.0.0.0', port=8000)

if __name__ == "__main__":
    threading.Thread(target=run_server).start()


api_id = int(os.getenv("API_ID","27655384"))
api_hash = os.getenv("API_HASH","a6a418b023a146e99af9ae1afd571cf4")
session_string = os.getenv("ASSIS_SESSION_STRING","")
session_string1 = os.getenv("YOUR_SESSION_STRING","")
PREFIX = ["/", "#", "!", "."]
OWNER_ID = os.getenv("OWNER_ID","7045191057")
GROUPS_FILE = "groups.json"
COOL = f"<code>.</code> <code>/</code> <code>#</code> "
app = Client("Assis", api_id=api_id, api_hash=api_hash, session_string=session_string)
AMBOT = Client("AbhiModszYT", api_id=api_id, api_hash=api_hash, session_string=session_string1)

AbhiModszYT = PyTgCalls(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

stream_running = {}
queues = {}
looping = {}
_boot_ = time.time()

app.set_parse_mode(enums.ParseMode.MARKDOWN)
bot_start_time = time.time()

async def search_yt(query):
    try:
        search = VideosSearch(query, limit=1)
        result = search.result()
        if 'result' in result and result['result']:
            video = result['result'][0]
            title = video['title']
            duration = video['duration']
            video_id = video['id']
            link = f"https://www.youtube.com/watch?v={video_id}"
            return title, duration, link
        else:
            return None, None, None
    except Exception as e:
        logger.error(f"search_yt error: {e}")
        return None, None, None

async def ytdl(format, link):
    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--cookies", "cookies.txt",  
            "-g",
            "-f", f"{format}",
            f"{link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if stdout:
            audio_link = stdout.decode().split("\n")[0]
            logger.info(f"Audio link retrieved: {audio_link}")
            return 1, audio_link
        else:
            error_message = stderr.decode()
            logger.error(f"yt-dlp stderr: {error_message}")
            return 0, error_message
    except Exception as e:
        logger.error(f"Exception occurred in ytdl: {e}")
        return 0, str(e)


def convert_duration(duration_str):
    parts = duration_str.split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    else:
        return int(parts[0])

async def add_to_queue(chat_id, title, duration, link, media_type):
    if chat_id not in queues:
        queues[chat_id] = []
    queues[chat_id].append({"title": title, "duration": duration, "link": link, "type": media_type})
    logger.info(f"ᴀᴅᴅᴇᴅ ᴛᴏ Qᴜᴇᴜᴇ : {title} (ᴅᴜʀᴀᴛɪᴏɴ : {duration}) ɪɴ ᴄʜᴀᴛ {chat_id}")

async def poll_stream_status(chat_id, message):
    while chat_id in stream_running:
        await asyncio.sleep(5)
        current_time = time.time()
        stream_info = stream_running.get(chat_id)
        if not stream_info:
            break
        elapsed_time = current_time - stream_info["start_time"]
        if elapsed_time > stream_info["duration"]:
            if chat_id in looping and looping[chat_id] > 0:
                looping[chat_id] -= 1
                await play_media(chat_id, stream_info, message, from_loop=True)
            elif chat_id in queues and queues[chat_id]:
                next_track = queues[chat_id].pop(0)
                await play_media(chat_id, next_track, message)
            else:
                stream_running.pop(chat_id, None)
                await AbhiModszYT.leave_call(chat_id)
                await message.reply("ꜱᴛʀᴇᴀᴍ ʜᴀꜱ ᴇɴᴅᴇᴅ.")
                break

async def play_media(chat_id, track, message, from_loop=False, seek_time=0):
    try:
        title, duration_str, link, media_type = track["title"], track["duration"], track["link"], track["type"]
        duration = convert_duration(duration_str)
        resp, songlink = await ytdl("bestaudio" if media_type == 'audio' else "best", link)
        if resp != 1:
            await message.reply("ᴇʀʀᴏʀ ᴘʟᴀʏɪɴɢ ᴛʜᴇ ɴᴇxᴛ ᴛʀᴀᴄᴋ ɪɴ ᴛʜᴇ Qᴜᴇᴜᴇ.")
            return
        media_stream = MediaStream(songlink, video_flags=MediaStream.Flags.IGNORE if media_type == 'audio' else None)
        await AbhiModszYT.play(chat_id, media_stream)
        user = message.from_user.mention
        reply_message = (
            f"✰≽ 𝗦𝘁𝗮𝗿𝘁𝗲𝗱 𝗦𝘁𝗿𝗲𝗮𝗺𝗶𝗻𝗴 𝗢𝗻 𝗩𝗖 : [{title}]({link})\n"
            f"✰≽ 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻 : {duration_str}\n"
            f"✰≽ 𝐑𝐞𝐪𝐮𝐞𝐬𝐭𝐞𝐝 𝐁𝐲 : {user}"
        )
        if not from_loop:
            await message.reply(reply_message, disable_web_page_preview=True)
        stream_running[chat_id] = {
            "start_time": time.time() - seek_time,
            "duration": duration,
            "title": title,
            "duration_str": duration_str,
            "link": link,
            "type": media_type
        }
        logger.info(f"Started playing: {title} (Duration: {duration_str}) in chat {chat_id}")
    except Exception as e:
        logger.error(f"ᴇʀʀᴏʀ ᴘʟᴀʏɪɴɢ ᴍᴇᴅɪᴀ : {e}")
        await message.reply(f"ᴇʀʀᴏʀ ᴘʟᴀʏɪɴɢ ᴍᴇᴅɪᴀ : {e}")

@AMBOT.on_message(filters.command(["play"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("play", PREFIX))
async def play(client, message):
    global stream_running
    if len(message.command) < 2:
        await message.reply("ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ꜱᴏɴɢ ɴᴀᴍᴇ.")
        return
    try:
        user = await app.get_me()
        await client.get_chat_member(message.chat.id, user.id)
    except:
        try:
            invitelink = await client.export_chat_invite_link(message.chat.id)
        except Exception: 
            pass
        try:
            await app.join_chat(invitelink)
        except UserAlreadyParticipant:
            pass
        except Exception as e:
            pass
    chat_id = message.chat.id
    query = message.text.split(" ", 1)[1]
    indicator_message = await message.reply("🔍")
    try:
        await message.delete()
        await client.send_chat_action(chat_id, enums.ChatAction.TYPING)
        title, duration, link = await search_yt(query)
        if not link:
            await indicator_message.edit("ꜱᴏʀʀʏ, ɴᴏ ʀᴇꜱᴜʟᴛꜱ ꜰᴏᴜɴᴅ ꜰᴏʀ ᴛʜɪꜱ Qᴜᴇʀʏ.")
            return

        resp, songlink = await ytdl("bestaudio", link)
        if resp == 0:
            await indicator_message.edit("ꜱᴏʀʀʏ, ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴛʀɪᴇᴠᴇ ᴀᴜᴅɪᴏ ʟɪɴᴋ.")
            return

        if chat_id in stream_running:
            logger.info(f"Active stream found in chat {chat_id}, adding {title} to queue.")
            await add_to_queue(chat_id, title, duration, link, 'audio')
            await message.reply(f"ᴀᴅᴅᴇᴅ ᴛᴏ Qᴜᴇᴜᴇ :\n [{title}]({link})\nᴅᴜʀᴀᴛɪᴏɴ: {duration}", disable_web_page_preview=True)
        else:
            logger.info(f"No active stream in chat {chat_id}, playing {title} directly.")
            await AbhiModszYT.play(chat_id, MediaStream(songlink, video_flags=MediaStream.Flags.IGNORE))
            user = message.from_user.mention
            reply_message = (
                f"✰≽ 𝗦𝘁𝗮𝗿𝘁𝗲𝗱 𝗦𝘁𝗿𝗲𝗮𝗺𝗶𝗻𝗴 𝗢𝗻 𝗩𝗖 : [{title}]({link})\n"
                f"✰≽ 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻 : {duration}\n"
                f"✰≽ 𝐑𝐞𝐪𝐮𝐞𝐬𝐭𝐞𝐝 𝐁𝐲 : {user}"
            )
            await message.reply(reply_message, disable_web_page_preview=True)
            stream_running[chat_id] = {
                "start_time": time.time(),
                "duration": convert_duration(duration),
                "title": title,
                "duration_str": duration,
                "link": link,
                "type": 'audio'
            }
            asyncio.create_task(poll_stream_status(chat_id, message))
        await indicator_message.delete()
    except Exception as e:
        logger.error(f"Error in play command: {e}")
        await indicator_message.edit(f"ꜱᴏʀʀʏ, ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴛʀɪᴇᴠᴇ. ᴇʀʀᴏʀ : {e}")

@AMBOT.on_message(filters.command(["vplay"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("vplay", PREFIX))
async def vplay(client, message):
    global stream_running
    if len(message.command) < 2:
        await message.reply("ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ꜱᴏɴɢ ɴᴀᴍᴇ.")
        return
    try:
        user = await app.get_me()
        await client.get_chat_member(message.chat.id, user.id)
    except:
        try:
            invitelink = await client.export_chat_invite_link(message.chat.id)
        except Exception: 
            pass
        try:
            await app.join_chat(invitelink)
        except UserAlreadyParticipant:
            pass
        except Exception as e:
            pass
    chat_id = message.chat.id
    query = message.text.split(" ", 1)[1]
    indicator_message = await message.reply("🔍")

    try:
        await message.delete()
        await client.send_chat_action(chat_id, enums.ChatAction.TYPING)
        title, duration, link = await search_yt(query)
        if not link:
            await indicator_message.edit("ꜱᴏʀʀʏ, ɴᴏ ʀᴇꜱᴜʟᴛꜱ ꜰᴏᴜɴᴅ ꜰᴏʀ ᴛʜɪꜱ Qᴜᴇʀʏ.")
            return

        resp, songlink = await ytdl("bestvideo", link)
        if resp == 0:
            await indicator_message.edit("ꜱᴏʀʀʏ, ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴛʀɪᴇᴠᴇ ᴠɪᴅᴇᴏ ʟɪɴᴋ.")
            return

        if chat_id in stream_running:
            logger.info(f"Active stream found in chat {chat_id}, adding {title} to queue.")
            await add_to_queue(chat_id, title, duration, link, 'video')
            await message.reply(f"ᴀᴅᴅᴇᴅ ᴛᴏ Qᴜᴇᴜᴇ :\n Title: [{title}]({link})\nᴅᴜʀᴀᴛɪᴏɴ : {duration}", disable_web_page_preview=True)
        else:
            logger.info(f"No active stream in chat {chat_id}, playing {title} directly.")
            await AbhiModszYT.play(chat_id, MediaStream(songlink))
            user = message.from_user.mention
            reply_message = (
                f"✰≽ 𝗦𝘁𝗮𝗿𝘁𝗲𝗱 𝗦𝘁𝗿𝗲𝗮𝗺𝗶𝗻𝗴 𝗢𝗻 𝗩𝗖 : [{title}]({link})\n"
                f"✰≽ 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻 : {duration}\n"
                f"✰≽ 𝐑𝐞𝐪𝐮𝐞𝐬𝐭𝐞𝐝 𝐁𝐲 : {user}"
            )
            await message.reply(reply_message, disable_web_page_preview=True)
            stream_running[chat_id] = {
                "start_time": time.time(),
                "duration": convert_duration(duration),
                "title": title,
                "duration_str": duration,
                "link": link,
                "type": 'video'
            }
            asyncio.create_task(poll_stream_status(chat_id, message))
        await indicator_message.delete()
    except Exception as e:
        logger.error(f"Error in vplay command: {e}")
        await indicator_message.edit(f"ꜱᴏʀʀʏ, ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴛʀɪᴇᴠᴇ. ᴇʀʀᴏʀ : {e}")

@AMBOT.on_message(filters.command(["skip"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("skip", PREFIX))
async def skip(client, message):
    chat_id = message.chat.id
    await message.delete()
    if len(message.command) == 2 and message.command[1].isdigit():
        index = int(message.command[1])
        if chat_id in queues and len(queues[chat_id]) >= index:
            logger.info(f"Skipping to track {index} in chat {chat_id}.")
            for _ in range(index - 1):
                queues[chat_id].pop(0)
            next_track = queues[chat_id].pop(0)
            await play_media(chat_id, next_track, message)
        else:
            await message.reply("ɪɴᴠᴀʟɪᴅ ᴛʀᴀᴄᴋ ɴᴜᴍʙᴇʀ.")
    elif chat_id in stream_running:
        logger.info(f"Skipping current track in chat {chat_id}.")
        await AbhiModszYT.leave_call(chat_id)
        if chat_id in queues and queues[chat_id]:
            next_track = queues[chat_id].pop(0)
            await play_media(chat_id, next_track, message)
        else:
            stream_running.pop(chat_id, None)
            await message.reply("ɴᴏ ᴍᴏʀᴇ ᴛʀᴀᴄᴋꜱ ɪɴ ᴛʜᴇ Qᴜᴇᴜᴇ.")
    else:
        await message.reply("ɴᴏ ᴀᴄᴛɪᴠᴇ ꜱᴛʀᴇᴀᴍ ᴛᴏ ꜱᴋɪᴘ.")

@AMBOT.on_message(filters.command(["queue"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("queue", PREFIX))
async def queue(client, message):
    chat_id = message.chat.id
    await message.delete()
    if chat_id in queues and queues[chat_id]:
        queue_message = "ᴄᴜʀʀᴇɴᴛ Qᴜᴇᴜᴇ :\n"
        for idx, track in enumerate(queues[chat_id]):
            queue_message += f"{idx + 1}. {track['title']} - {track['duration_str']}\n"
        await message.reply(queue_message)
    else:
        await message.reply("ᴛʜᴇ Qᴜᴇᴜᴇ ɪꜱ ᴇᴍᴘᴛʏ.")

@AMBOT.on_message(filters.command(["clearqueue"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("clearqueue", PREFIX))
async def clearqueue(client, message):
    chat_id = message.chat.id
    await message.delete()
    if chat_id in queues:
        queues[chat_id] = []
        await message.reply("Qᴜᴇᴜᴇ ᴄʟᴇᴀʀᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ.")
    else:
        await message.reply("ɴᴏ ᴀᴄᴛɪᴠᴇ Qᴜᴇᴜᴇ ᴛᴏ ᴄʟᴇᴀʀ.")

@AMBOT.on_message(filters.command(["pause"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("pause", PREFIX))
async def pause(client, message):
    await message.delete()
    chat_id = message.chat.id
    if chat_id in stream_running:
        logger.info(f"Pausing stream in chat {chat_id}.")
        await AbhiModszYT.pause_stream(chat_id)
        await message.reply("ꜱᴛʀᴇᴀᴍ ᴘᴀᴜꜱᴇᴅ.")
    else:
        await message.reply("ɴᴏ ᴀᴄᴛɪᴠᴇ ꜱᴛʀᴇᴀᴍ ᴛᴏ ᴘᴀᴜꜱᴇ.")

@AMBOT.on_message(filters.command(["resume"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("resume", PREFIX))
async def resume(client, message):
    chat_id = message.chat.id
    await message.delete()
    if chat_id in stream_running:
        logger.info(f"Resuming stream in chat {chat_id}.")
        await AbhiModszYT.resume_stream(chat_id)
        await message.reply("ꜱᴛʀᴇᴀᴍ ʀᴇꜱᴜᴍᴇᴅ.")
    else:
        await message.reply("ɴᴏ ᴀᴄᴛɪᴠᴇ ꜱᴛʀᴇᴀᴍ ᴛᴏ ʀᴇꜱᴜᴍᴇ.")

@AMBOT.on_message(filters.command(["stop","end"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("stop", PREFIX))
async def stop(client, message):
    global stream_running
    await message.delete()
    chat_id = message.chat.id
    if chat_id in stream_running:
        logger.info(f"Stopping stream in chat {chat_id}.")
        await AbhiModszYT.leave_call(chat_id)
        del stream_running[chat_id]
        await message.reply("ꜱᴛʀᴇᴀᴍ ꜱᴛᴏᴘᴘᴇᴅ.")
    if chat_id in queues:
        queues[chat_id] = []
    else:
        await message.reply("ɴᴏ ᴀᴄᴛɪᴠᴇ ꜱᴛʀᴇᴀᴍ ᴛᴏ ꜱᴛᴏᴘ.")

@AMBOT.on_message(filters.command(["loop"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("loop", PREFIX))
async def loop(client, message):
    chat_id = message.chat.id
    await message.delete()
    if len(message.command) == 2 and message.command[1].isdigit():
        loop_count = int(message.command[1])
        if chat_id in stream_running:
            looping[chat_id] = loop_count
            await message.reply(f"ʟᴏᴏᴘɪɴɢ ᴄᴜʀʀᴇɴᴛ ꜱᴏɴɢ {loop_count} ᴛɪᴍᴇꜱ.")
        else:
            await message.reply("ɴᴏ ᴀᴄᴛɪᴠᴇ ꜱᴛʀᴇᴀᴍ ᴛᴏ ʟᴏᴏᴘ.")
    else:
        await message.reply("ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ɴᴜᴍʙᴇʀ ᴏꜰ ᴛɪᴍᴇꜱ ᴛᴏ ʟᴏᴏᴘ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ ꜱᴏɴɢ.")

@AMBOT.on_message(filters.command(["seek"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("seek", PREFIX))
async def seek(client, message):
    chat_id = message.chat.id
    await message.delete()
    if len(message.command) == 2:
        time_str = message.command[1]
        try:
            seek_time = int(time_str.replace('sec', '').replace('min', '').strip())
            if 'min' in time_str:
                seek_time *= 60
            
            if chat_id in stream_running:
                stream_info = stream_running[chat_id]
                current_time = time.time()
                elapsed_time = current_time - stream_info["start_time"]
                new_elapsed_time = elapsed_time + seek_time
                
                if new_elapsed_time < stream_info["duration"]:
                    stream_info["start_time"] = current_time - new_elapsed_time
                    logger.info(f"Seeked forward by {seek_time} seconds. New start time: {stream_info['start_time']}")
                else:
                    await message.reply("ꜱᴇᴇᴋ ᴛɪᴍᴇ ᴇxᴄᴇᴇᴅꜱ ꜱᴏɴɢ ᴅᴜʀᴀᴛɪᴏɴ.")
            else:
                await message.reply("ɴᴏ ᴀᴄᴛɪᴠᴇ ꜱᴛʀᴇᴀᴍ ᴛᴏ ꜱᴇᴇᴋ.")
        except ValueError:
            await message.reply("ɪɴᴠᴀʟɪᴅ ꜱᴇᴇᴋ ᴛɪᴍᴇ ꜰᴏʀᴍᴀᴛ. ᴜꜱᴇ '10ꜱᴇᴄ' ᴏʀ '1ᴍɪɴ'.")
    else:
        await message.reply("ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴛɪᴍᴇ ᴛᴏ ꜱᴇᴇᴋ, ᴇ.ɢ., .ꜱᴇᴇᴋ 30ꜱᴇᴄ ᴏʀ .ꜱᴇᴇᴋ 1ᴍɪɴ.")

@AMBOT.on_message(filters.command(["leave"], prefixes=[""]) & filters.me)
async def leave(client, message):
    await message.delete()
    if len(message.command) > 1:
        chat_id = message.command[1] 
        chat = await client.get_chat(chat_id)  
    else:
        chat_id = message.chat.id
        chat = message.chat  
    chat_title = chat.title if hasattr(chat, 'title') else "Unknown Chat"
    aux = await message.reply(f"{app.me.mention} ᴛʀʏɪɴɢ ᴛᴏ ʟᴇᴀᴠᴇ ᴛʜᴇ ᴄʜᴀᴛ <code>{chat_title}</code>...")
    try:
        await app.leave_chat(chat_id)
        await aux.edit(f"{app.me.mention} ᴅᴏɴᴇ! ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ʟᴇғᴛ ᴛʜᴇ ᴄʜᴀᴛ <code>{chat_title}</code>.")
    except Exception as e:
        await aux.edit(f"{app.me.mention} ᴇʀʀᴏʀ: <code>{str(e)}</code>")


        
@AMBOT.on_message(filters.command(["join"], prefixes=[""]) & filters.me)
async def join(client, message):
    await message.delete()
    chat_id = message.chat.id
    url = message.command[1]
    aux = await message.reply(f"{app.me.mention} ᴛʀʏɪɴɢ ᴛᴏ ᴊᴏɪɴ ᴛʜᴇ ᴀꜱꜱɪꜱᴛᴀɴᴛ ᴛᴏ ᴛʜᴇ ᴄʜᴀᴛ...")
    if url.startswith("https://t.me/+"):
        url = url.replace("https://t.me/+", "https://t.me/joinchat/")
    try:
        await app.join_chat(url)
        chat = await app.get_chat(chat_id)
        chat_title = chat.title if hasattr(chat, 'title') else "Unknown Chat"
        await aux.edit(f"{app.me.mention} ᴅᴏɴᴇ! ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ᴄʜᴀᴛ <code>{chat_title}</code>.")
    except UserAlreadyParticipant:
        await aux.edit(f"{app.me.mention} ɪ ᴀᴍ ᴀʟʀᴇᴀᴅʏ ɪɴ ᴛʜɪꜱ ᴄʜᴀᴛ <code>{chat_title}</code>.")
    except Exception as e:
        await aux.edit(f"{app.me.mention} ᴇʀʀᴏʀ: <code>{str(e)}</code>")


@AMBOT.on_message(filters.command(["start"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("start", PREFIX))
async def start(client, message):
    await message.delete()
    chat_id = message.chat.id
    start_message = f"""
ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴜʙᴍᴜꜱɪᴄ! 🎶

ʜᴇʀᴇ ᴀʀᴇ ꜱᴏᴍᴇ ʙᴀꜱɪᴄ ᴄᴏᴍᴍᴀɴᴅꜱ ʏᴏᴜ ᴄᴀɴ ᴜꜱᴇ ᴛᴏ ᴄᴏɴᴛʀᴏʟ ᴛʜᴇ ᴍᴜꜱɪᴄ ʙᴏᴛ :
ᴜꜱᴇ ᴄᴏᴍᴍᴀɴᴅꜱ ᴘʀᴇꜰɪx : {COOL}
ꜰᴏʀ ᴜʙ : ᴊᴜꜱᴛ ᴛʏᴘᴇ ᴄᴍᴅꜱ

help - ɢᴇᴛ ᴛʜᴇ ʟɪꜱᴛ ᴏꜰ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅꜱ.
"""
    await message.reply(start_message)
    
@AMBOT.on_message(filters.command(["help"], prefixes=[""]) & filters.me)
@app.on_message(filters.command("help", PREFIX))
async def help(client, message):
    await message.delete()
    chat_id = message.chat.id
    HELPSALL = f"""
ᴜʙᴍᴜꜱɪᴄ ᴄᴏᴍᴍᴀɴᴅꜱ :
ᴜꜱᴇ ᴄᴏᴍᴍᴀɴᴅꜱ ᴘʀᴇꜰɪx : {COOL}
ꜰᴏʀ ᴜʙ : ᴊᴜꜱᴛ ᴛʏᴘᴇ ᴄᴍᴅꜱ

play : ꜰᴏʀ ᴀᴜᴅɪᴏ ꜱᴏɴɢ ᴘʟᴀʏ ɪɴ ɢʀᴏᴜᴘ.
vplay : ꜰᴏʀ ᴠɪᴅᴇᴏ ꜱᴏɴɢ ᴘʟᴀʏ ɪɴ ɢʀᴏᴜᴘ.
skip : ꜱᴋɪᴘ ꜱᴏɴɢ / ᴘʟᴀʏ ɴᴇxᴛ ꜱᴏɴɢ.
queue : ꜱʜᴏᴡ ᴘʟᴀʏʟɪꜱᴛꜱ / ꜱʜᴏᴡ ɴᴇxᴛ ᴘʟᴀʏ ꜱᴏɴɢꜱ.
pause : ᴍᴜᴛᴇ ꜱᴏɴɢ / ᴘᴀᴜꜱᴇ ᴍᴜꜱɪᴄ ɪɴ ɢʀᴏᴜᴘ.
resume : ʀᴇꜱᴜᴍᴇ ꜱᴏɴɢ.
stop : ꜱᴛᴏᴘ ᴘʟᴀʏ ꜱᴏɴɢ / ᴇɴᴅ ᴍᴜꜱɪᴄ.
loop : ʟᴏᴏᴘ ꜱᴏɴɢꜱ.
seek : ꜱᴇᴇᴋ ᴍᴜꜱɪᴄ / .ꜱᴇᴇᴋ 30ꜱᴇᴄ ᴏʀ .ꜱᴇᴇᴋ 1ᴍɪɴ.
clearqueue : ᴄʟᴇᴀʀ Qᴜᴇᴜᴇ / ᴄʟᴇᴀʀ ᴘʟᴀʏʟɪꜱᴛꜱ.
join : ᴊᴏɪɴ ᴀꜱꜱɪꜱ ᴠɪᴇ ɢʀᴏᴜᴘ ᴜʀʟ / ᴊᴏɪɴ @UserName / PriviteLink.
leave : ᴄʜᴀᴛ_ɪᴅ / ꜰᴏʀ ʟᴇᴀᴠᴇ ᴀꜱꜱɪꜱ ɢʀᴏᴜᴘ.
"""
    await message.reply(HELPSALL)



async def fetch_and_save_groups():
    try:
        async for dialog in app.get_dialogs():
            if dialog.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
                save_group_id(dialog.chat.id)

        print("Groups fetched and saved successfully.")  
    except Exception as e:
        print(f"Error fetching groups: {e}")  

def save_group_id(chat_id):
    try:
        with open(GROUPS_FILE, "r") as f:
            groups = json.load(f)
    except FileNotFoundError:
        groups = []

    if chat_id not in groups:
        groups.append(chat_id)
        with open(GROUPS_FILE, "w") as f:
            json.dump(groups, f)
        print(f"Saved new group ID: {chat_id}")  

async def fetch_trivia():
    try:
        url = "https://opentdb.com/api.php?amount=1&type=multiple"
        response = requests.get(url)
        data = response.json()

        if data['response_code'] == 0:
            question = data['results'][0]['question']
            correct_answer = data['results'][0]['correct_answer']
            incorrect_answers = data['results'][0]['incorrect_answers']
            options = incorrect_answers + [correct_answer]
            random.shuffle(options)

            trivia_message = f"🎉 Trivia Challenge! 🎉\n\nQuestion: {question}\n"
            trivia_message += "\n".join([f"{i + 1}. {option}" for i, option in enumerate(options)])
            trivia_message += f"\n\n🕵️‍♂️ Find the correct answer in the poll below!"
            
            return trivia_message, options, correct_answer
        else:
            print("Failed to fetch trivia. Response code:", data['response_code'])  
            return "Couldn't fetch trivia at the moment.", [], ""
    except Exception as e:
        print(f"Error fetching trivia: {e}")
        return "Couldn't fetch trivia due to an error.", [], ""

async def fetch_fun_fact():
    try:
        number = random.randint(1, 100)
        url = f"http://numbersapi.com/{number}/trivia"
        response = requests.get(url)

        if response.status_code == 200:
            return f"📚 Fun Fact: {response.text}"
        else:
            print("Failed to fetch fun fact. Status code:", response.status_code)  
            return "Couldn't fetch a fun fact at the moment."
    except Exception as e:
        print(f"Error fetching fun fact: {e}")
        return "Couldn't fetch a fun fact due to an error."

async def send_auto_messages():
    await fetch_and_save_groups()
    try:
        with open(GROUPS_FILE, "r") as f:
            group_ids = json.load(f)
    except FileNotFoundError:
        group_ids = []
        print("No groups found, please fetch groups first.")  

    while True:
        print("Sending auto messages...")  

        if random.choice([True, False]):
            message, options, correct_answer = await fetch_trivia()
            for group_id in group_ids:
                try:
                    await app.send_poll(
                        group_id,
                        question=message,
                        options=options,
                        is_anonymous=False,
                        correct_option_id=options.index(correct_answer) if correct_answer in options else 0,
                        explanation="Select the correct answer!"
                    )
                    print(f"Poll sent to group ID: {group_id}") 
                except Exception as e:
                    print(f"Error sending poll to group {group_id}: {e}")
        else:
            message = await fetch_fun_fact()
            for group_id in group_ids:
                try:
                    await app.send_message(group_id, message)
                    print(f"Fun fact sent to group ID: {group_id}")  
                except Exception as e:
                    print(f"Error sending fun fact to group {group_id}: {e}")

        await asyncio.sleep(18000) 

async def main():
    await app.start()
    print("Assis started")
    await AMBOT.start()
    print("Main Userbot started")
    await AbhiModszYT.start()
    print("PyTgCalls started For Assis")
    await idle()
    await app.stop()
    await AMBOT.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
