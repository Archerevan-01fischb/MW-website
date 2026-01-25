# Database Migrations

## Current Migrations

### 001: Fix Gondola Naming Convention

**Problem:** Gondola system IDs used ambiguous format (G1, G2, G3) that conflicts with tile IDs (A1-P16).

**Solution:** Use explicit `GONDOLA_NN` format for all gondola identifiers.

**Status:** Ready to run

## Running the Migration

### Option 1: Windows (Recommended)
```bash
cd database/migrations
run_migration.bat
```

### Option 2: Git Bash / WSL
```bash
cd database/migrations
bash run_migration.sh
```

### Option 3: Manual
```bash
cd database
# Create backup
copy settlements.db backups/settlements_backup_manual.db
# Run migration
sqlite3 settlements.db < migrations/001_fix_gondola_naming.sql
```

## What Changes

### Before Migration:
```
gondola_system_id: 1
system_name: "G1-ORIGIN"
system_name: "G1-PYLON-01"
system_name: "G1-TERMINUS"
```

### After Migration:
```
gondola_system_id: 1 (kept for compatibility)
gondola_system_text: "GONDOLA_01" (NEW)
system_name: "GONDOLA_01-ORIGIN"
system_name: "GONDOLA_01-PYLON-01"
system_name: "GONDOLA_01-TERMINUS"
```

## Verification

After running migration, check results:

```sql
-- Should show GONDOLA_01, GONDOLA_02, etc.
SELECT DISTINCT gondola_system_text, COUNT(*)
FROM settlements
WHERE gondola_system_text IS NOT NULL
GROUP BY gondola_system_text
ORDER BY gondola_system_text;

-- Sample GONDOLA_01 settlements
SELECT system_name, tile_id, gondola_role
FROM settlements
WHERE gondola_system_text = 'GONDOLA_01'
ORDER BY gondola_sequence;
```

## Rollback

If something goes wrong:
```bash
# Windows
copy backups\settlements_backup_YYYYMMDD_HHMMSS.db settlements.db

# Bash
cp backups/settlements_backup_YYYYMMDD_HHMMSS.db settlements.db
```

## Impact on Code

After migration, update code to use new field:

### Old Code (DEPRECATED):
```rust
// DON'T USE THIS
let gondola_id = row.get::<_, i32>("gondola_system_id")?;
let name = format!("G{}-ORIGIN", gondola_id); // ❌ Ambiguous!
```

### New Code (CORRECT):
```rust
// USE THIS
let gondola_id = row.get::<_, String>("gondola_system_text")?;
let name = format!("{}-ORIGIN", gondola_id); // ✅ "GONDOLA_01-ORIGIN"
```

## Benefits

1. **No ambiguity** - "GONDOLA_01" cannot be confused with tile "G1"
2. **Professional** - Clear, explicit naming convention
3. **Sortable** - Zero-padded numbers sort correctly (GONDOLA_01, GONDOLA_02, ...)
4. **Searchable** - Easy to grep/search for "GONDOLA_" prefix
5. **Extensible** - Can add other transport types (TRAM_01, CABLE_01) without confusion

---

**Created:** 2025-10-16
**Author:** Claude Code
**Status:** Ready for production
