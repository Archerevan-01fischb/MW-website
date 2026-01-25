-- ============================================================================
-- Migration 001: Fix Gondola Naming Convention
-- ============================================================================
-- Problem: gondola_system_id uses integers (1, 2, 3...) which creates
--          ambiguous system_name patterns like "G1-ORIGIN", "G2-TERMINUS"
--          that look identical to tile IDs (G1, G2, etc.)
--
-- Solution: Use explicit "GONDOLA_NN" format for all gondola identifiers
--
-- Date: 2025-10-16
-- ============================================================================

-- STEP 1: Backup check
-- Run this first to verify you have a backup:
-- .backup 'settlements_backup_20251016.db'

BEGIN TRANSACTION;

-- STEP 2: Add new text-based gondola system identifier column
ALTER TABLE settlements
ADD COLUMN gondola_system_text TEXT;

-- STEP 3: Populate new column with GONDOLA_NN format
-- Pad to 2 digits for consistent sorting
UPDATE settlements
SET gondola_system_text = 'GONDOLA_' || printf('%02d', gondola_system_id)
WHERE gondola_system_id IS NOT NULL;

-- STEP 4: Update system_name for all gondola-related settlements
-- Replace "G{N}-" prefix with "GONDOLA_{NN}-"

-- Update ORIGIN settlements
UPDATE settlements
SET system_name = gondola_system_text || '-ORIGIN'
WHERE gondola_role = 'ORIGIN';

-- Update PYLON settlements (extract sequence number from current name)
-- Current format: "G1-PYLON-01" -> New format: "GONDOLA_01-PYLON-01"
UPDATE settlements
SET system_name = gondola_system_text || '-PYLON-' ||
                  substr(system_name, instr(system_name, '-PYLON-') + 7)
WHERE gondola_role = 'PYLON';

-- Update TERMINUS settlements
UPDATE settlements
SET system_name = gondola_system_text || '-TERMINUS'
WHERE gondola_role = 'TERMINUS';

-- STEP 5: Create index on new column for performance
CREATE INDEX idx_settlements_gondola_text ON settlements(gondola_system_text);

-- STEP 6: Verify the changes
-- Uncomment to see before/after comparison:
-- SELECT
--     gondola_system_id as old_id,
--     gondola_system_text as new_id,
--     system_name,
--     tile_id
-- FROM settlements
-- WHERE gondola_system_id IS NOT NULL
-- ORDER BY gondola_system_text, gondola_sequence;

COMMIT;

-- ============================================================================
-- POST-MIGRATION VERIFICATION
-- ============================================================================
-- Run these queries to verify the migration succeeded:

-- 1. Check that all gondola settlements have new IDs
-- SELECT COUNT(*) as missing_new_ids
-- FROM settlements
-- WHERE gondola_system_id IS NOT NULL
--   AND gondola_system_text IS NULL;
-- Expected: 0

-- 2. Check that system_names are updated correctly
-- SELECT DISTINCT gondola_system_text, COUNT(*) as settlements
-- FROM settlements
-- WHERE gondola_system_text IS NOT NULL
-- GROUP BY gondola_system_text
-- ORDER BY gondola_system_text;

-- 3. Sample the new naming convention
-- SELECT system_name, tile_id, gondola_system_text, gondola_role
-- FROM settlements
-- WHERE gondola_system_text IN ('GONDOLA_01', 'GONDOLA_02')
-- ORDER BY gondola_system_text, gondola_sequence;

-- ============================================================================
-- ROLLBACK (if needed)
-- ============================================================================
-- If something goes wrong, restore from backup:
-- .restore 'settlements_backup_20251016.db'

-- ============================================================================
-- FUTURE: Optional cleanup (Phase 2)
-- ============================================================================
-- After verifying everything works, optionally remove old integer column:
--
-- BEGIN TRANSACTION;
--
-- -- Create new table without gondola_system_id
-- CREATE TABLE settlements_new (
--     ... (copy full schema but replace gondola_system_id with gondola_system_text)
-- );
--
-- -- Copy data
-- INSERT INTO settlements_new SELECT ... FROM settlements;
--
-- -- Swap tables
-- DROP TABLE settlements;
-- ALTER TABLE settlements_new RENAME TO settlements;
--
-- -- Recreate indexes and constraints
-- ...
--
-- COMMIT;
