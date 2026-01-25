#!/usr/bin/env python3
"""
Midwinter Database Search MCP Server

This MCP server provides tools for searching the Midwinter game manual database.
Uses Python sqlite3 directly - no external binaries required.
"""

import asyncio
import sqlite3
from pathlib import Path
from typing import Any
import sys

# Add mcp package to path
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: mcp package not found. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Database path
PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "midwinter_unified.db"

# Create MCP server instance
app = Server("midwinter-search")


def get_db_connection():
    """Get a database connection."""
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DATABASE_PATH}")
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def quick_search_query(query: str) -> str:
    """Fast entity lookup for characters, buildings, etc."""
    try:
        conn = get_db_connection()
        results = []

        # Search characters
        cursor = conn.execute("""
            SELECT full_name, title, age, occupation, biography
            FROM characters
            WHERE full_name LIKE ? OR search_text LIKE ?
            LIMIT 10
        """, (f"%{query}%", f"%{query}%"))

        chars = cursor.fetchall()
        if chars:
            results.append("=== CHARACTERS ===")
            for c in chars:
                results.append(f"\n**{c['full_name']}**")
                if c['title']:
                    results.append(f"  Title: {c['title']}")
                if c['age']:
                    results.append(f"  Age: {c['age']}")
                if c['occupation']:
                    results.append(f"  Occupation: {c['occupation']}")
                if c['biography']:
                    bio = c['biography'][:300] + "..." if len(c['biography']) > 300 else c['biography']
                    results.append(f"  Bio: {bio}")

        # Search buildings
        cursor = conn.execute("""
            SELECT building_type, description, gameplay_function
            FROM buildings
            WHERE building_type LIKE ? OR description LIKE ?
            LIMIT 10
        """, (f"%{query}%", f"%{query}%"))

        buildings = cursor.fetchall()
        if buildings:
            results.append("\n=== BUILDINGS ===")
            for b in buildings:
                results.append(f"\n**{b['building_type']}**")
                if b['description']:
                    results.append(f"  {b['description']}")
                if b['gameplay_function']:
                    results.append(f"  Function: {b['gameplay_function']}")

        # Search enemy vehicles
        cursor = conn.execute("""
            SELECT vehicle_type, role, description
            FROM enemy_vehicles
            WHERE vehicle_type LIKE ? OR description LIKE ?
            LIMIT 10
        """, (f"%{query}%", f"%{query}%"))

        vehicles = cursor.fetchall()
        if vehicles:
            results.append("\n=== ENEMY VEHICLES ===")
            for v in vehicles:
                results.append(f"\n**{v['vehicle_type']}**")
                if v['role']:
                    results.append(f"  Role: {v['role']}")
                if v['description']:
                    results.append(f"  {v['description']}")

        conn.close()

        if not results:
            return f"No entities found matching '{query}'"

        return "\n".join(results)

    except Exception as e:
        return f"Error: {str(e)}"


def search_manual_query(query: str) -> str:
    """Full-text search across the manual using FTS5."""
    try:
        conn = get_db_connection()

        # Use FTS5 for full-text search with BM25 ranking
        cursor = conn.execute("""
            SELECT page_number, section_type,
                   snippet(manual_fts, 2, '>>>', '<<<', '...', 64) as snippet,
                   bm25(manual_fts) as rank
            FROM manual_fts
            WHERE manual_fts MATCH ?
            ORDER BY rank
            LIMIT 15
        """, (query,))

        results = cursor.fetchall()
        conn.close()

        if not results:
            return f"No results found for '{query}'"

        output = [f"Found {len(results)} results for '{query}':\n"]
        for r in results:
            output.append(f"**Page {r['page_number']}** [{r['section_type']}]")
            output.append(f"  {r['snippet']}\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error: {str(e)}"


def filter_by_section_query(section: str, query: str) -> str:
    """Search within a specific section."""
    try:
        conn = get_db_connection()

        # Map section names to section_type values
        section_map = {
            "characters": "character",
            "equipment": "equipment",
            "locations": "location",
            "story_sections": "story",
            "general_content": "general"
        }

        section_type = section_map.get(section, section)

        cursor = conn.execute("""
            SELECT page_number, section_type,
                   snippet(manual_fts, 2, '>>>', '<<<', '...', 64) as snippet
            FROM manual_fts
            WHERE manual_fts MATCH ? AND section_type LIKE ?
            LIMIT 15
        """, (query, f"%{section_type}%"))

        results = cursor.fetchall()
        conn.close()

        if not results:
            return f"No results found for '{query}' in section '{section}'"

        output = [f"Found {len(results)} results in '{section}':\n"]
        for r in results:
            output.append(f"**Page {r['page_number']}** [{r['section_type']}]")
            output.append(f"  {r['snippet']}\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error: {str(e)}"


def show_page_query(page_number: int) -> str:
    """Display full content of a specific page."""
    try:
        conn = get_db_connection()

        cursor = conn.execute("""
            SELECT page_number, section_type, content
            FROM manual_pages
            WHERE page_number = ?
        """, (page_number,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return f"Page {page_number} not found"

        return f"=== Page {row['page_number']} [{row['section_type']}] ===\n\n{row['content']}"

    except Exception as e:
        return f"Error: {str(e)}"


def list_sections_query() -> str:
    """List all sections with page counts."""
    try:
        conn = get_db_connection()

        cursor = conn.execute("""
            SELECT section_type, COUNT(*) as count,
                   MIN(page_number) as first_page, MAX(page_number) as last_page
            FROM manual_pages
            GROUP BY section_type
            ORDER BY first_page
        """)

        results = cursor.fetchall()
        conn.close()

        output = ["=== MANUAL SECTIONS ===\n"]
        total = 0
        for r in results:
            output.append(f"**{r['section_type']}**: {r['count']} pages (pp. {r['first_page']}-{r['last_page']})")
            total += r['count']

        output.append(f"\n**Total: {total} pages**")
        return "\n".join(output)

    except Exception as e:
        return f"Error: {str(e)}"


def list_entities_query() -> str:
    """List all pre-extracted entities."""
    try:
        conn = get_db_connection()
        output = []

        # Characters
        cursor = conn.execute("SELECT full_name FROM characters ORDER BY full_name")
        chars = [r['full_name'] for r in cursor.fetchall()]
        output.append(f"=== CHARACTERS ({len(chars)}) ===")
        output.append(", ".join(chars))

        # Buildings
        cursor = conn.execute("SELECT building_type FROM buildings ORDER BY building_type")
        buildings = [r['building_type'] for r in cursor.fetchall()]
        output.append(f"\n=== BUILDINGS ({len(buildings)}) ===")
        output.append(", ".join(buildings))

        # Enemy vehicles
        cursor = conn.execute("SELECT vehicle_type FROM enemy_vehicles ORDER BY vehicle_type")
        vehicles = [r['vehicle_type'] for r in cursor.fetchall()]
        output.append(f"\n=== ENEMY VEHICLES ({len(vehicles)}) ===")
        output.append(", ".join(vehicles))

        # Skills
        cursor = conn.execute("SELECT skill_name FROM skills ORDER BY skill_name")
        skills = [r['skill_name'] for r in cursor.fetchall()]
        if skills:
            output.append(f"\n=== SKILLS ({len(skills)}) ===")
            output.append(", ".join(skills))

        conn.close()
        return "\n".join(output)

    except Exception as e:
        return f"Error: {str(e)}"


def can_recruit_query(recruiter: str, target: str) -> str:
    """Check if one character can recruit another."""
    try:
        conn = get_db_connection()

        # Normalize names by searching for matches
        recruiter_match = None
        target_match = None

        cursor = conn.execute("SELECT full_name FROM characters WHERE full_name LIKE ?", (f"%{recruiter}%",))
        result = cursor.fetchone()
        if result:
            recruiter_match = result['full_name']

        cursor = conn.execute("SELECT full_name FROM characters WHERE full_name LIKE ?", (f"%{target}%",))
        result = cursor.fetchone()
        if result:
            target_match = result['full_name']

        if not recruiter_match:
            return f"Character '{recruiter}' not found"
        if not target_match:
            return f"Character '{target}' not found"

        # Check for positive relationship (recruiter likes target)
        cursor = conn.execute("""
            SELECT relationship_type FROM character_relationships
            WHERE from_character = ? AND to_character = ? AND sentiment = 'positive'
        """, (recruiter_match, target_match))
        positive = cursor.fetchall()

        # Check for negative relationship (target dislikes recruiter)
        cursor = conn.execute("""
            SELECT relationship_type FROM character_relationships
            WHERE from_character = ? AND to_character = ? AND sentiment = 'negative'
        """, (target_match, recruiter_match))
        blocked = cursor.fetchall()

        conn.close()

        output = [f"=== Can {recruiter_match} recruit {target_match}? ===\n"]

        if blocked:
            reasons = [r['relationship_type'] for r in blocked]
            output.append(f"NO - {target_match} {', '.join(reasons)} {recruiter_match}")
            return "\n".join(output)

        if positive:
            reasons = [r['relationship_type'] for r in positive]
            output.append(f"YES - {recruiter_match} is {', '.join(reasons)} with {target_match}")
            return "\n".join(output)

        output.append(f"UNKNOWN - No direct relationship found")
        output.append(f"(They are not friends, but also not enemies)")
        return "\n".join(output)

    except Exception as e:
        return f"Error: {str(e)}"


def who_can_recruit_query(target: str) -> str:
    """Find all characters who can recruit a specific target."""
    try:
        conn = get_db_connection()

        # Find target character
        cursor = conn.execute("SELECT full_name FROM characters WHERE full_name LIKE ?", (f"%{target}%",))
        result = cursor.fetchone()
        if not result:
            return f"Character '{target}' not found"
        target_match = result['full_name']

        # Find who the target likes (they can be recruited by people they like)
        cursor = conn.execute("""
            SELECT to_character, relationship_type FROM character_relationships
            WHERE from_character = ? AND sentiment = 'positive'
        """, (target_match,))
        can_recruit = cursor.fetchall()

        # Find who the target dislikes (they cannot recruit)
        cursor = conn.execute("""
            SELECT to_character, relationship_type FROM character_relationships
            WHERE from_character = ? AND sentiment = 'negative'
        """, (target_match,))
        cannot_recruit = cursor.fetchall()

        conn.close()

        output = [f"=== Who can recruit {target_match}? ===\n"]

        if can_recruit:
            output.append("CAN RECRUIT:")
            for r in can_recruit:
                output.append(f"  - {r['to_character']} ({r['relationship_type']})")
        else:
            output.append("CAN RECRUIT: No specific friends listed")

        if cannot_recruit:
            output.append("\nCANNOT RECRUIT:")
            for r in cannot_recruit:
                output.append(f"  - {r['to_character']} ({r['relationship_type']})")
        else:
            output.append("\nCANNOT RECRUIT: No enemies listed")

        return "\n".join(output)

    except Exception as e:
        return f"Error: {str(e)}"


def get_enemies_query(character: str) -> str:
    """Get all enemies of a character (people who dislike them or they dislike)."""
    try:
        conn = get_db_connection()

        cursor = conn.execute("SELECT full_name FROM characters WHERE full_name LIKE ?", (f"%{character}%",))
        result = cursor.fetchone()
        if not result:
            return f"Character '{character}' not found"
        char_match = result['full_name']

        # People this character dislikes
        cursor = conn.execute("""
            SELECT to_character, relationship_type FROM character_relationships
            WHERE from_character = ? AND sentiment = 'negative'
        """, (char_match,))
        dislikes = cursor.fetchall()

        # People who dislike this character
        cursor = conn.execute("""
            SELECT from_character, relationship_type FROM character_relationships
            WHERE to_character = ? AND sentiment = 'negative'
        """, (char_match,))
        disliked_by = cursor.fetchall()

        conn.close()

        output = [f"=== Enemies of {char_match} ===\n"]

        if dislikes:
            output.append(f"{char_match} DISLIKES:")
            for r in dislikes:
                output.append(f"  - {r['to_character']} ({r['relationship_type']})")

        if disliked_by:
            output.append(f"\nDISLIKED BY:")
            for r in disliked_by:
                output.append(f"  - {r['from_character']} ({r['relationship_type']})")

        if not dislikes and not disliked_by:
            output.append("No enemies found!")

        return "\n".join(output)

    except Exception as e:
        return f"Error: {str(e)}"


def get_friends_query(character: str) -> str:
    """Get all friends/allies of a character."""
    try:
        conn = get_db_connection()

        cursor = conn.execute("SELECT full_name FROM characters WHERE full_name LIKE ?", (f"%{character}%",))
        result = cursor.fetchone()
        if not result:
            return f"Character '{character}' not found"
        char_match = result['full_name']

        # People this character likes
        cursor = conn.execute("""
            SELECT to_character, relationship_type FROM character_relationships
            WHERE from_character = ? AND sentiment = 'positive'
        """, (char_match,))
        friends = cursor.fetchall()

        # People who like this character
        cursor = conn.execute("""
            SELECT from_character, relationship_type FROM character_relationships
            WHERE to_character = ? AND sentiment = 'positive'
        """, (char_match,))
        liked_by = cursor.fetchall()

        conn.close()

        output = [f"=== Friends of {char_match} ===\n"]

        if friends:
            output.append(f"{char_match} LIKES:")
            for r in friends:
                output.append(f"  - {r['to_character']} ({r['relationship_type']})")

        if liked_by:
            output.append(f"\nLIKED BY:")
            for r in liked_by:
                output.append(f"  - {r['from_character']} ({r['relationship_type']})")

        if not friends and not liked_by:
            output.append("No friends found!")

        return "\n".join(output)

    except Exception as e:
        return f"Error: {str(e)}"


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="quick_search",
            description="Ultra-fast entity lookup for characters, equipment, and locations. Best for finding specific items, people, or places by name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Entity name to find (e.g., 'Stark', 'rifle', 'snow-cat')"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_manual",
            description="Full-text search across the Midwinter game manual. Returns relevant pages with highlighted snippets and BM25 relevance ranking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'vehicle combat', 'how to use hang glider', 'weapons')"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="filter_by_section",
            description="Search within a specific section of the manual (characters, equipment, locations, story_sections, general_content).",
            inputSchema={
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "description": "Section to search in",
                        "enum": ["characters", "equipment", "locations", "story_sections", "general_content"]
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["section", "query"]
            }
        ),
        Tool(
            name="show_page",
            description="Display the full content of a specific manual page by its page number.",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_number": {
                        "type": "integer",
                        "description": "Page number to display"
                    }
                },
                "required": ["page_number"]
            }
        ),
        Tool(
            name="list_sections",
            description="List all available sections in the manual with page counts.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="list_entities",
            description="List all pre-extracted entities (characters, equipment, locations) available for quick search.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="can_recruit",
            description="Check if one character can recruit another. Returns YES, NO, or UNKNOWN based on their relationship.",
            inputSchema={
                "type": "object",
                "properties": {
                    "recruiter": {
                        "type": "string",
                        "description": "Name of the character doing the recruiting (e.g., 'Stark', 'Llewellyn')"
                    },
                    "target": {
                        "type": "string",
                        "description": "Name of the character to be recruited (e.g., 'Adams', 'Wright')"
                    }
                },
                "required": ["recruiter", "target"]
            }
        ),
        Tool(
            name="who_can_recruit",
            description="Find all characters who can (or cannot) recruit a specific target character.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Name of the character to find recruiters for"
                    }
                },
                "required": ["target"]
            }
        ),
        Tool(
            name="get_enemies",
            description="Get all enemies of a character - people they dislike or who dislike them.",
            inputSchema={
                "type": "object",
                "properties": {
                    "character": {
                        "type": "string",
                        "description": "Name of the character"
                    }
                },
                "required": ["character"]
            }
        ),
        Tool(
            name="get_friends",
            description="Get all friends/allies of a character - people they like or who like them.",
            inputSchema={
                "type": "object",
                "properties": {
                    "character": {
                        "type": "string",
                        "description": "Name of the character"
                    }
                },
                "required": ["character"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""

    if name == "quick_search":
        query = arguments.get("query", "")
        output = quick_search_query(query)
        return [TextContent(type="text", text=output)]

    elif name == "search_manual":
        query = arguments.get("query", "")
        output = search_manual_query(query)
        return [TextContent(type="text", text=output)]

    elif name == "filter_by_section":
        section = arguments.get("section", "")
        query = arguments.get("query", "")
        output = filter_by_section_query(section, query)
        return [TextContent(type="text", text=output)]

    elif name == "show_page":
        page_number = arguments.get("page_number", 0)
        output = show_page_query(page_number)
        return [TextContent(type="text", text=output)]

    elif name == "list_sections":
        output = list_sections_query()
        return [TextContent(type="text", text=output)]

    elif name == "list_entities":
        output = list_entities_query()
        return [TextContent(type="text", text=output)]

    elif name == "can_recruit":
        recruiter = arguments.get("recruiter", "")
        target = arguments.get("target", "")
        output = can_recruit_query(recruiter, target)
        return [TextContent(type="text", text=output)]

    elif name == "who_can_recruit":
        target = arguments.get("target", "")
        output = who_can_recruit_query(target)
        return [TextContent(type="text", text=output)]

    elif name == "get_enemies":
        character = arguments.get("character", "")
        output = get_enemies_query(character)
        return [TextContent(type="text", text=output)]

    elif name == "get_friends":
        character = arguments.get("character", "")
        output = get_friends_query(character)
        return [TextContent(type="text", text=output)]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
