-- 006: people-first discovery (specs/16-people-first-discovery.md).
-- A person is anyone who publishes knowledge about financial markets or economics: trader, portfolio manager, executive,
-- economist, professor, researcher, analyst, author, journalist, regulator... `trading_style` / `primary_markets` stay as they are
-- (they describe traders); the new columns describe everybody.
ALTER TABLE persons ADD COLUMN profession TEXT CHECK (profession IS NULL OR profession IN
  ('trader','portfolio_manager','investor','executive','founder','economist','academic','researcher','analyst','strategist',
   'author','journalist','educator','regulator','central_banker','other'));
ALTER TABLE persons ADD COLUMN affiliation TEXT;       -- employer, fund, university, institution
ALTER TABLE persons ADD COLUMN domains TEXT;           -- comma-separated fields: "equities, macro, asset pricing"
ALTER TABLE persons ADD COLUMN homepage TEXT;
ALTER TABLE persons ADD COLUMN relevance TEXT;         -- one sentence: why this person is in scope (the evidence of finance/economics knowledge)
ALTER TABLE persons ADD COLUMN external_ids TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(external_ids));  -- {"orcid": "...", "openalex": "A123", "google_scholar": "...", "wikipedia": "...", "ssrn": "..."}
CREATE INDEX idx_persons_profession ON persons(profession);
