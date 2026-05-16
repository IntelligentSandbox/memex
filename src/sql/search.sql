SELECT * FROM media
WHERE tags LIKE ? OR transcript LIKE ?
ORDER BY created_at DESC
LIMIT ? OFFSET ?;
