# Midwinter Database Search MCP Server

An MCP server that provides search capabilities for the Midwinter game manual database.

## Requirements

- Python 3.10+
- `mcp` package: `pip install mcp`
- Database file at `database/midwinter_unified.db` (included in repo)

**No external binaries required** - uses Python sqlite3 directly.

## Installation

```bash
pip install mcp
```

That's it! The server uses Python's built-in sqlite3 module.

## Configuration

Add to your `.mcp.json` in the project root:

```json
{
  "mcpServers": {
    "midwinter": {
      "command": "python",
      "args": ["mcp-midwinter-search/server.py"]
    }
  }
}
```

## Troubleshooting

**"Database not found" error:**
- Ensure `database/midwinter_unified.db` exists in the project root
- The server looks for it at `../database/midwinter_unified.db` relative to `server.py`

**"mcp package not found" error:**
```bash
pip install mcp
```

**MCP tools not appearing in Claude Code:**
- Restart Claude Code after adding the configuration
- Check that `.mcp.json` is in the project root (same folder as `Cargo.toml`)

## Available Tools

### quick_search
Fast entity lookup for characters, buildings, and vehicles.

```
Search for "Stark" - finds Captain John Doone Doyle Doyne Doyle Stark
Search for "snow" - finds snow-related buildings and vehicles
```

### search_manual
Full-text search across all 196 manual pages using FTS5 with BM25 ranking.

```
Search for "vehicle combat"
Search for "hang glider"
```

### filter_by_section
Search within a specific section:
- `characters` - Character descriptions and bios
- `equipment` - Weapons, vehicles, items
- `locations` - Places and buildings
- `story_sections` - Story/narrative content
- `general_content` - General gameplay info

### show_page
Display the full content of a specific page by number (1-196).

### list_sections
Show all sections with page counts.

### list_entities
List all indexed entities (32 characters, 18 buildings, vehicles, skills).

## Database Contents

- **196 manual pages** with full-text search index (FTS5)
- **32 characters** with names, ages, occupations, biographies
- **18 building types** with descriptions and gameplay functions
- **Enemy vehicles** with roles and descriptions
- **Skills** and character skill ratings
- **Relationships** between characters

## Technical Details

- Uses SQLite FTS5 for full-text search with Porter stemming
- BM25 ranking for relevance scoring
- Snippet highlighting with `>>>` and `<<<` markers
- All queries are parameterized (SQL injection safe)
