import logging
import os
import random
import string
from io import BytesIO

import asyncpg
import humanize
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, UploadFile, status, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from passlib.hash import pbkdf2_sha256
import settings

app = FastAPI()
app.debug = (
    True
    if not os.getenv("DEBUG")
    else False
    if os.getenv("DEBUG") == "false"
    else "true"
)

app.logger = logging.getLogger(__name__)
app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.on_event("startup")
async def initialize():
    app.db = await asyncpg.create_pool(
        database=settings.db.NAME,
        host="127.0.0.1" if app.debug else "gayms_db",
        port="5432",
        user=settings.db.USER,
        password=settings.db.PASSWORD,
    )

    with open("schema.sql") as fb:
        await app.db.execute(fb.read())

    app.logger.info("Database has started.")


async def api_key_auth(api_key: str = Depends(oauth2_scheme)):
    query = await app.db.fetch("SELECT api_key FROM users")

    if not query:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Forbidden"
        )

    invalid = True
    for item in query:
        item = item["api_key"]
        if pbkdf2_sha256.verify(api_key, item):
            invalid = False
            break

    if invalid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Forbidden"
        )


async def generate_fid(check_existing: bool = True):
    file_id = random.choices(string.ascii_letters + string.digits, k=24)

    if check_existing:
        entries = await app.db.fetch("SELECT file_id FROM files")
        while True:
            if file_id in entries:
                file_id = random.choices(string.ascii_letters + string.digits, k=24)
            else:
                break

    return "".join(file_id)

@app.get("/")
async def index():
    return Response("im gay")

@app.get("/view/{file_id}")
async def view(file_id: str):
    query = await app.db.fetchrow("SELECT * FROM files WHERE file_id = $1", file_id)

    if not query:
        return {
            "error": True,
            "exception": f'There is no file with the entry "{file_id}".',
        }

    data = query["data"]
    content_type = query["content_type"]
    filename = query["filename"]

    buffer = BytesIO(data)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type=content_type,
        headers={"Content-Disposition": f'filename="{filename}"'},
    )


@app.get("/download/{file_id}")
async def download(file_id: str):
    query = await app.db.fetchrow("SELECT * FROM files WHERE file_id = $1", file_id)

    if not query:
        return {
            "error": True,
            "exception": f'There is no file with the entry "{file_id}".',
        }

    data = query["data"]
    content_type = query["content_type"]
    filename = query["filename"]

    return Response(
        data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
    
@app.get("/hi-im-discord-crawler")
async def discord_check(request: Request):
    agent = request.headers.get("user-agent")
    return Response(
    f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>hi im discord crawler</title>
        <meta property="og:title" content="hi im discord crawler" />
        <meta property="og:type" content="website" />
        <meta property="og:description" content="{agent}" />
    </head>
    <body>
        <p>this site is only for getting discord's crawler agent, there's totally definitely not any secret definitely not no way</p>
    </body>
    </html>
    """.lstrip()
    )


@app.post("/upload", dependencies=[Depends(api_key_auth)])
async def upload(file: UploadFile):
    filesize = len(await file.read())
    filesize_limit = 500_000_000

    if filesize > filesize_limit:
        limit_fmt = humanize.naturalsize(filesize_limit)
        return {"error": True, "exception": f"Filesize can't be over {limit_fmt}."}

    content_type = file.content_type
    file_id = await generate_fid()
    await file.seek(0)
    data = await file.read()

    await app.db.execute(
        "INSERT INTO files (file_id, filename, data, content_type) VALUES ($1, $2, $3, $4)",
        file_id,
        file.filename,
        data,
        content_type,
    )

    return {"error": False, "file_id": file_id}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=6969, reload=app.debug)
