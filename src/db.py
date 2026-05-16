from db_conn import SQL, get_database_connection


def initialize_database():
    """Create the media table if it does not already exist."""
    conn = get_database_connection()
    conn.execute(SQL["create_media"])
    conn.commit()
    conn.close()


def get_all_media(offset=0, limit=20):
    """Return a paginated list of all media records ordered by most recent."""
    conn = get_database_connection()
    rows = conn.execute(SQL["get_all"], (limit, offset)).fetchall()
    conn.close()
    return rows


def search_media(query, offset=0, limit=20):
    """Search media records by matching the query against tags and transcript text."""
    conn = get_database_connection()
    rows = conn.execute(
        SQL["search"], (f"%{query}%", f"%{query}%", limit, offset)
    ).fetchall()
    conn.close()
    return rows


def update_media_tags(media_id, tags):
    """Overwrite the tags field for the given media record."""
    conn = get_database_connection()
    conn.execute(SQL["update_tags"], (tags, media_id))
    conn.commit()
    conn.close()


def get_media_by_id(media_id):
    """Fetch a single media record by its primary key. Returns None if not found."""
    conn = get_database_connection()
    row = conn.execute(SQL["get_by_id"], (media_id,)).fetchone()
    conn.close()
    return row


def delete_media_record(media_id):
    """Delete a media record from the database by its primary key."""
    conn = get_database_connection()
    conn.execute(SQL["delete"], (media_id,))
    conn.commit()
    conn.close()


def insert_media_record(url, tags, transcript, filename, media_type, created_at):
    """Insert a new media record and return its new row ID."""
    conn = get_database_connection()
    cursor = conn.execute(
        SQL["insert"], (url, tags, transcript, filename, media_type, created_at)
    )
    media_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return media_id


def update_media_transcript(media_id, transcript):
    """Update the transcript field for a media record once background transcription completes."""
    conn = get_database_connection()
    conn.execute(SQL["update_transcript"], (transcript, media_id))
    conn.commit()
    conn.close()
