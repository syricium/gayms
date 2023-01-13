CREATE TABLE IF NOT EXISTS files (
    file_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    data BYTEA NOT NULL,
    content_type TEXT NOT NULL,
    uploader TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    api_key TEXT NOT NULL
);