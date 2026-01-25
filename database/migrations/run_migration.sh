#!/bin/bash
# ============================================================================
# Run Database Migration with Backup
# ============================================================================

set -e  # Exit on error

DB_PATH="../settlements.db"
BACKUP_PATH="../backups/settlements_backup_$(date +%Y%m%d_%H%M%S).db"
MIGRATION_FILE="001_fix_gondola_naming.sql"

echo "================================"
echo "Database Migration: Fix Gondola Naming"
echo "================================"
echo ""

# Create backup directory
mkdir -p ../backups

# Step 1: Backup
echo "Step 1: Creating backup..."
cp "$DB_PATH" "$BACKUP_PATH"
echo "✓ Backup created: $BACKUP_PATH"
echo ""

# Step 2: Show current state
echo "Step 2: Current gondola system IDs:"
sqlite3 "$DB_PATH" "SELECT DISTINCT gondola_system_id, COUNT(*) as count FROM settlements WHERE gondola_system_id IS NOT NULL GROUP BY gondola_system_id ORDER BY gondola_system_id LIMIT 5;"
echo ""

# Step 3: Run migration
echo "Step 3: Running migration..."
sqlite3 "$DB_PATH" < "$MIGRATION_FILE"
echo "✓ Migration complete"
echo ""

# Step 4: Verify
echo "Step 4: Verification - New gondola system IDs:"
sqlite3 "$DB_PATH" "SELECT DISTINCT gondola_system_text, COUNT(*) as count FROM settlements WHERE gondola_system_text IS NOT NULL GROUP BY gondola_system_text ORDER BY gondola_system_text LIMIT 5;"
echo ""

# Step 5: Sample new naming
echo "Step 5: Sample new naming (GONDOLA_01):"
sqlite3 "$DB_PATH" "SELECT system_name, tile_id, gondola_role FROM settlements WHERE gondola_system_text = 'GONDOLA_01' ORDER BY gondola_sequence;"
echo ""

echo "================================"
echo "✓ Migration complete!"
echo "================================"
echo ""
echo "Backup saved to: $BACKUP_PATH"
echo ""
echo "To rollback:"
echo "  cp \"$BACKUP_PATH\" \"$DB_PATH\""
