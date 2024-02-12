-- Enable membership on dev mode
WANT_MEMBERSHIP = false

-- Production settings:
PRODUCTION_ENABLED = false

API_TOKEN = ""
PLAY_TOKEN_KEY = ""
WANT_TOKEN_EXPIRATIONS = false

-- Doesn't seem dcFile.getHash() matches the client.
-- We'll just hardcode the stock WOC client hashVal.
-- This shouldn't change as we won't be adding new content anyways.
CLIENT_HASH = 46329213
