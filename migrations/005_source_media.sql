-- 005: pictures of sources (channel / subreddit / profile icons), next to the person images of 004.
ALTER TABLE sources ADD COLUMN avatar_url TEXT;
ALTER TABLE sources ADD COLUMN avatar_path TEXT;
ALTER TABLE sources ADD COLUMN avatar_sha256 TEXT;
