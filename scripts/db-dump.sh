#!/usr/bin/env bash
# Dump the local EvoGraph database for seeding a remote deployment.
#
# Usage: ./scripts/db-dump.sh [output_file]
#
# Creates a compressed pg_dump that can be restored with:
#   pg_restore --no-owner --no-acl -d <DATABASE_URL> evograph_dump.sql.gz

set -euo pipefail

OUTPUT="${1:-data/evograph_dump.sql.gz}"
mkdir -p "$(dirname "$OUTPUT")"

echo "Dumping evograph database..."
docker compose exec -T db pg_dump -U postgres -Fc evograph > "$OUTPUT"

SIZE=$(du -h "$OUTPUT" | cut -f1)
echo "Done. Dump saved to $OUTPUT ($SIZE)"
echo ""
echo "To restore to a remote database:"
echo "  pg_restore --no-owner --no-acl -d \$DATABASE_URL $OUTPUT"
