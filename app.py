import logging
import os
import random
import string
from io import BytesIO

import asyncpg
import humanize
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from passlib.hash import pbkdf2_sha256

import settings

app = FastAPI()
app.debug = (
    True if not os.getenv("DEBUG") else False if os.getenv("DEBUG") == "false" else True
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
        raise HTTPException(status_code=401, detail="Forbidden")

    invalid = True
    for item in query:
        item = item["api_key"]
        if pbkdf2_sha256.verify(api_key, item):
            invalid = False
            break

    if invalid:
        raise HTTPException(status_code=401, detail="Forbidden")


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


async def get_user_by_key(key: str):
    results = await app.db.fetch("SELECT * FROM users")
    for result in results:
        api_key = result["api_key"]
        username = result["username"]
        if pbkdf2_sha256.verify(key, api_key):
            return username


@app.get("/")
async def index():
    return Response("im gay")


@app.get("/view/{file_id}")
async def view(file_id: str):
    file_id = file_id.split(".")[0]
    
    query = await app.db.fetchrow("SELECT * FROM files WHERE file_id = $1", file_id)

    if not query:
        return JSONResponse(
            {
                "error": True,
                "exception": f'There is no file with the entry "{file_id}".',
            },
            status_code=404,
        )

    data = query["data"]
    content_type = query["content_type"]
    filename = query["filename"]

    buffer = BytesIO(data)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type=content_type,
        headers={"Content-Disposition": f'filename="{filename}"', "Content-Type": content_type},
    )


@app.get("/download/{file_id}")
async def download(file_id: str):
    file_id = file_id.split(".")[0]
    
    query = await app.db.fetchrow("SELECT * FROM files WHERE file_id = $1", file_id)

    if not query:
        return JSONResponse(
            {
                "error": True,
                "exception": f'There is no file with the entry "{file_id}".',
            },
            status_code=404,
        )

    data = query["data"]
    content_type = query["content_type"]
    filename = query["filename"]

    return Response(
        data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": content_type},
    )


@app.post("/upload", dependencies=[Depends(api_key_auth)])
async def upload(request: Request, file: UploadFile):
    filesize = len(await file.read())
    filesize_limit = 500_000_000

    if filesize > filesize_limit:
        limit_fmt = humanize.naturalsize(filesize_limit)
        return JSONResponse(
            {"error": True, "exception": f"Filesize can't be over {limit_fmt}."},
            status_code=404,
        )

    api_key = request.headers.get("Authorization").lstrip("Bearer ")

    content_type = file.content_type
    file_id = await generate_fid()
    uploader = await get_user_by_key(api_key)
    await file.seek(0)
    data = await file.read()
    
    if not uploader:
        return JSONResponse(
            {
                "error": True,
                "exception": "get_user_by_key function unexpectedly returned NoneType, please report this or try again"
            },
            500
        )

    await app.db.execute(
        "INSERT INTO files (file_id, filename, data, content_type, uploader) VALUES ($1, $2, $3, $4, $5)",
        file_id,
        file.filename,
        data,
        content_type,
        uploader,
    )

    return {"error": False, "file_id": file_id}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7000 if app.debug else 6969, reload=app.debug)
