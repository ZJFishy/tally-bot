import json
import datetime
import discord
import humanfriendly
from google.cloud import secretmanager
from discord.ext import commands
import signal
import sys
from types import FrameType

from flask import Flask

from utils.logging import logger

app = Flask(__name__)

@app.route("/")
def hello() -> str:
    # Use basic logging with custom fields
    logger.info(logField="custom-entry", arbitraryField="custom-entry")

    # https://cloud.google.com/run/docs/logging#correlate-logs
    logger.info("Child logger with trace Id.")

    return "Hello, World!"


def shutdown_handler(signal_int: int, frame: FrameType) -> None:
    logger.info(f"Caught Signal {signal.strsignal(signal_int)}")

    from utils.logging import flush

    flush()

    # Safely exit program
    sys.exit(0)

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix="!", intents=intents)

DNE_MESSAGE = "Tally does not exist, please start it first using `!start_tally name count`"
DT_FORMAT = "%H:%M:%S %Y-%m-%d"
DATA_FILEPATH = "./data.json"


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")

@client.event
async def on_guild_join(guild):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if not str(guild.id) in db:
        db[str(guild.id)] = {}
        with open(DATA_FILEPATH, "w", encoding="utf-8") as file_out:
            json.dump(db, file_out)

@client.command()
async def start_tally(ctx, name: str, start_count: int = 0):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db[str(ctx.guild.id)]:
        await ctx.send(
            f'{name} tally already exists, with a count of {db[str(ctx.guild.id)][name][0]}')
    else:
        db[str(ctx.guild.id)][name] = (start_count, ["UNKNOWN" for _ in range(start_count)])
        with open(DATA_FILEPATH, "w", encoding="utf-8") as file_out:
            json.dump(db, file_out)
        await ctx.send(f'{name} tally created with a count of {start_count}')


@client.command()
async def update_count(ctx, name: str, count: int):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db[str(ctx.guild.id)]:
        dates = db[str(ctx.guild.id)][name][1]
        while count > db[str(ctx.guild.id)][name][0] + 1:
            dates.append("UNKNOWN")
        dates.append(datetime.datetime.now().strftime(DT_FORMAT))
        db[str(ctx.guild.id)][name] = (count, dates)
        with open(DATA_FILEPATH, "w", encoding="utf-8") as file_out:
            json.dump(db, file_out)
        await ctx.send(f"{name} tally updated to a count of {count}")
    else:
        await ctx.send(DNE_MESSAGE)


@client.command()
async def inc(ctx, add: int, name: str):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db[str(ctx.guild.id)]:
        count, dates = db[str(ctx.guild.id)][name]
        dates.append(datetime.datetime.now().strftime(DT_FORMAT))
        db[str(ctx.guild.id)][name] = (count + add, dates)
        with open(DATA_FILEPATH, "w", encoding="utf-8") as file_out:
            json.dump(db, file_out)
        await ctx.send(f"{name} tally increased to a count of {count + add}")
    else:
        await ctx.send(DNE_MESSAGE)


@client.command()
async def dec(ctx, remove: int, name: str):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db[str(ctx.guild.id)]:
        count, dates = db[str(ctx.guild.id)][name]
        for _ in range(remove):
            dates.pop(-1)
        db[str(ctx.guild.id)][name] = (count - remove, dates)
        with open(DATA_FILEPATH, "w", encoding="utf-8") as file_out:
            json.dump(db, file_out)
        await ctx.send(f"{name} tally decreased to a count of {count - remove}")
    else:
        await ctx.send(DNE_MESSAGE)


@client.command()
async def check_tally(ctx, name: str):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db[str(ctx.guild.id)]:
        count, dates = db[str(ctx.guild.id)][name]
        if len(dates) == 0:
            await ctx.send(f"{name} tally has a count of {count}")
        else:
            await ctx.send(
                f"{name} tally has a count of {count} and was last updated at {dates[-1]} GMT"
            )
    else:
        await ctx.send(DNE_MESSAGE)


@client.command()
async def delete_tally(ctx, name: str):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db[str(ctx.guild.id)]:
        del db[str(ctx.guild.id)][name]
        with open(DATA_FILEPATH, "w", encoding="utf-8") as file_out:
            json.dump(db, file_out)
        await ctx.send(f"{name} tally deleted")
    else:
        await ctx.send(f"{name} tally does not exist")


@client.command()
async def last_inc(ctx, name: str):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db[str(ctx.guild.id)]:
        count, dates = db[str(ctx.guild.id)][name]
        if count == 0:
            await ctx.send(f"{name} tally has no count")
        elif len(dates) == 0:
            await ctx.send(
                f"{name} tally has a count of {count}, but no associated dates"
            )
        else:
            try:
                await ctx.send(
                    f"{name} tally was last updated {humanfriendly.format_timespan(datetime.datetime.now() - datetime.datetime.strptime(dates[-1], DT_FORMAT))} ago"
                )
            except:
                await ctx.send(
                    f"{name} tally was last updated an unknown amount of time ago"
                )
    else:
        await ctx.send(DNE_MESSAGE)

if __name__ == "__main__":
    # Running application locally, outside of a Google Cloud Environment

    # handles Ctrl-C termination
    signal.signal(signal.SIGINT, shutdown_handler)

    app.run(host="localhost", port=8080, debug=True)
    sm_client = secretmanager.SecretManagerServiceClient()
    client.run(token=sm_client.access_secret_version(request={"name":"projects/59510040058/secrets/bot-token/versions/1"}).payload.data.decode())
else:
    # handles Cloud Run container termination
    signal.signal(signal.SIGTERM, shutdown_handler)
