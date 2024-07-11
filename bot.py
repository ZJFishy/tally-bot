import json
import datetime
import discord
import humanfriendly
from google.cloud import secretmanager
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix="!", intents=intents)

DNE_MESSAGE = "Tally does not exist, please start it first using `!start_tally name count`"
DT_FORMAT = "%H:%M:%S %Y-%m-%d"
DATA_FILEPATH = "./data.json"


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")

@client.command()
async def start_tally(ctx, name: str, start_count: int = 0):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db:
        await ctx.send(
            f'{name} tally already exists, with a count of {db[name][0]}')
    else:
        db[name] = (start_count, [])
        with open(DATA_FILEPATH, "w", encoding="utf-8") as file_out:
            json.dump(db, file_out)
        await ctx.send(f'{name} tally created with a count of {start_count}')


@client.command()
async def update_count(ctx, name: str, count: int):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db:
        dates = db[name][1]
        dates.append(datetime.datetime.now().strftime(DT_FORMAT))
        db[name] = (count, dates)
        with open(DATA_FILEPATH, "w", encoding="utf-8") as file_out:
            json.dump(db, file_out)
        await ctx.send(f"{name} tally updated to a count of {count}")
    else:
        await ctx.send(DNE_MESSAGE)


@client.command()
async def inc(ctx, add: int, name: str):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db:
        count, dates = db[name]
        dates.append(datetime.datetime.now().strftime(DT_FORMAT))
        db[name] = (count + add, dates)
        with open(DATA_FILEPATH, "w", encoding="utf-8") as file_out:
            json.dump(db, file_out)
        await ctx.send(f"{name} tally increased to a count of {count + add}")
    else:
        await ctx.send(DNE_MESSAGE)


@client.command()
async def dec(ctx, remove: int, name: str):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db:
        count, dates = db[name]
        for _ in range(remove):
            dates.pop(-1)
        db[name] = (count - remove, dates)
        with open(DATA_FILEPATH, "w", encoding="utf-8") as file_out:
            json.dump(db, file_out)
        await ctx.send(f"{name} tally decreased to a count of {count - remove}"
                       )
    else:
        await ctx.send(DNE_MESSAGE)


@client.command()
async def check_tally(ctx, name: str):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db:
        count, dates = db[name]
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
    if name in db:
        del db[name]
        with open(DATA_FILEPATH, "w", encoding="utf-8") as file_out:
            json.dump(db, file_out)
        await ctx.send(f"{name} tally deleted")
    else:
        await ctx.send(f"{name} tally does not exist")


@client.command()
async def last_inc(ctx, name: str):
    with open(DATA_FILEPATH, "r", encoding="utf-8") as file_in:
        db = json.load(file_in)
    if name in db:
        count, dates = db[name]
        if count == 0:
            await ctx.send(f"{name} tally has no count")
        elif len(dates) == 0:
            await ctx.send(
                f"{name} tally has a count of {count}, but no associated dates"
            )
        else:
            await ctx.send(
                f"{name} tally was last updated {humanfriendly.format_timespan(datetime.datetime.now() - datetime.datetime.strptime(dates[-1], DT_FORMAT))} ago"
            )
    else:
        await ctx.send(DNE_MESSAGE)

sm_client = secretmanager.SecretManagerServiceClient()
client.run(token=sm_client.access_secret_version(request={"name":"projects/59510040058/secrets/bot-token/versions/1"}).payload.data.decode("UTF-8"))
