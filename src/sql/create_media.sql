CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    transcript TEXT,
    filename TEXT NOT NULL,
    media_type TEXT NOT NULL DEFAULT 'video',
    created_at TEXT NOT NULL
);
