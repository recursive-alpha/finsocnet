-- Migration 002: Add Skill Classification (System Skills vs Improved Skills)

-- Safely add columns if not already present
ALTER TABLE skills ADD COLUMN skill_type TEXT DEFAULT 'improved'; -- 'system' vs 'improved'
ALTER TABLE skills ADD COLUMN version TEXT DEFAULT '1.0.0';
ALTER TABLE skills ADD COLUMN author TEXT DEFAULT 'finsocnet';

CREATE INDEX IF NOT EXISTS idx_skills_type ON skills(skill_type);
