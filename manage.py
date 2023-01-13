import asyncio
import inspect
import os
import random
import string

import asyncpg
from passlib.hash import pbkdf2_sha256

import settings

debug = (
    True
    if not os.getenv("DEBUG")
    else False
    if os.getenv("DEBUG") == "false"
    else "true"
)


async def add_user(username):
    db = await asyncpg.create_pool(
        database=settings.db.NAME,
        host="127.0.0.1" if debug else "gayms_db",
        port="5432",
        user=settings.db.USER,
        password=settings.db.PASSWORD,
    )

    raw_api_key = "".join(random.choices(string.ascii_letters, k=64))
    api_key = pbkdf2_sha256.hash(raw_api_key)

    await db.execute(
        "INSERT INTO users (username, api_key) VALUES ($1, $2)", username, api_key
    )

    print(f"api key: {raw_api_key}")


async def remove_user(username):
    db = await asyncpg.create_pool(
        database=settings.db.NAME,
        host="127.0.0.1" if debug else "gayms_db",
        port="5432",
        user=settings.db.USER,
        password=settings.db.PASSWORD,
    )

    await db.execute("DELETE FROM users WHERE username = $1", username)

    results = await db.fetchrow("SELECT * FROM users WHERE username = $1", username)

    if not results:
        print("deleted successfully")
    else:
        print("failed deletion")


async def update_key(username):
    db = await asyncpg.create_pool(
        database=settings.db.NAME,
        host="127.0.0.1" if debug else "gayms_db",
        port="5432",
        user=settings.db.USER,
        password=settings.db.PASSWORD,
    )

    raw_api_key = "".join(random.choices(string.ascii_letters, k=64))
    api_key = pbkdf2_sha256.hash(raw_api_key)

    results = await db.execute(
        "UPDATE users SET api_key = $2 WHERE username = $1", username, api_key
    )

    if results == "UPDATE 1":
        print(f"new api key: {raw_api_key}")
    else:
        print("insertion failed")


async def list_users():
    db = await asyncpg.create_pool(
        database=settings.db.NAME,
        host="127.0.0.1" if debug else "gayms_db",
        port="5432",
        user=settings.db.USER,
        password=settings.db.PASSWORD,
    )

    results = await db.fetch("SELECT username FROM users")

    for result in results:
        print("- " + result["username"])


async def check_key(username, key):
    db = await asyncpg.create_pool(
        database=settings.db.NAME,
        host="127.0.0.1" if debug else "gayms_db",
        port="5432",
        user=settings.db.USER,
        password=settings.db.PASSWORD,
    )

    result = await db.fetchval(
        "SELECT api_key FROM users WHERE username = $1", username
    )

    if pbkdf2_sha256.verify(key, result):
        print("key valid")
    else:
        print("key invalid")


async def custom():
    last_func_type = "fetch"
    func_types = ["execute", "fetch", "fetchrow", "fetchval"]

    db = await asyncpg.create_pool(
        database=settings.db.NAME,
        host="127.0.0.1" if debug else "gayms_db",
        port="5432",
        user=settings.db.USER,
        password=settings.db.PASSWORD,
    )

    while True:
        query = input("> ")

        if query in ["quit", "exit", "\q"]:
            break

        lower_query = query.lower()

        for func_type in func_types:
            if query.startswith(func_type + " "):
                last_func_type = func_type
                query = query.lstrip(func_type)

        func = getattr(db, last_func_type)

        result = await func(query)

        print(result)
        print("")


options = {
    "add_user": add_user,
    "remove_user": remove_user,
    "update_key": update_key,
    "list_users": list_users,
    "check_key": check_key,
    "custom": custom,
}

options_fmt = "\n".join(f"{k+1}. {v}" for k, v in enumerate(options.keys()))
selection = input(f"Which option do you want?\n{options_fmt}\n\nSelection: ").lower()

if selection not in options:
    try:
        selection = list(options.keys())[int(selection) - 1]
    except ValueError:
        print("Selection not valid")
        exit()

func = options[selection]

variables = {}

for arg in list(inspect.getfullargspec(func).args):
    var = input(f"{arg}: ")
    variables[arg] = var

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(func(**variables))
