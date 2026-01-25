"""
Midwinter Manual Search - Web Interface
A simple Streamlit app for intelligent searching of the Midwinter game manual.

Deploy to Streamlit Cloud (free) - API key stored in Secrets, not visible to users.
"""

import streamlit as st
import sqlite3
import os
from pathlib import Path

# Try to import anthropic
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def get_api_key():
    """Get API key from Streamlit secrets or environment."""
    # Try Streamlit secrets first (for Streamlit Cloud deployment)
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except:
        pass

    # Try environment variable (for local/NAS deployment)
    return os.environ.get("ANTHROPIC_API_KEY", "")


def get_database_path():
    """Find the database file."""
    possible_paths = [
        Path(__file__).parent / "database" / "midwinter_unified.db",
        Path(__file__).parent.parent / "database" / "midwinter_unified.db",
        Path(__file__).parent / "midwinter_unified.db",
        Path("database/midwinter_unified.db"),
        Path("midwinter_unified.db"),
    ]

    for path in possible_paths:
        if path.exists():
            return str(path)

    return None


class DatabaseTools:
    """Database search tools matching the MCP server functionality."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def search_manual(self, query: str) -> str:
        """Full-text search across the manual."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT page_number, section, snippet(pages_fts, 2, '>>>', '<<<', '...', 64) as snippet,
                       bm25(pages_fts) as rank
                FROM pages_fts
                WHERE pages_fts MATCH ?
                ORDER BY rank
                LIMIT 5
            """, (query,))

            results = cursor.fetchall()

            if not results:
                words = query.split()
                if words:
                    like_pattern = f"%{words[0]}%"
                    cursor.execute("""
                        SELECT page_number, section, substr(content, 1, 200) as snippet
                        FROM pages
                        WHERE content LIKE ?
                        LIMIT 5
                    """, (like_pattern,))
                    results = cursor.fetchall()

            if not results:
                return "No matching pages found."

            output = []
            for row in results:
                page_num = row[0]
                section = row[1] or "General"
                snippet = row[2]
                output.append(f"**Page {page_num}** ({section}):\n{snippet}\n")

            return "\n".join(output)

        finally:
            conn.close()

    def quick_search(self, query: str) -> str:
        """Search for specific entities."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            results = []

            cursor.execute("""
                SELECT name, description FROM characters
                WHERE name LIKE ? OR description LIKE ?
                LIMIT 3
            """, (f"%{query}%", f"%{query}%"))
            for row in cursor.fetchall():
                results.append(f"**Character: {row[0]}**\n{row[1][:200]}...")

            cursor.execute("""
                SELECT name, description FROM equipment
                WHERE name LIKE ? OR description LIKE ?
                LIMIT 3
            """, (f"%{query}%", f"%{query}%"))
            for row in cursor.fetchall():
                results.append(f"**Equipment: {row[0]}**\n{row[1][:200]}...")

            cursor.execute("""
                SELECT name, description FROM locations
                WHERE name LIKE ? OR description LIKE ?
                LIMIT 3
            """, (f"%{query}%", f"%{query}%"))
            for row in cursor.fetchall():
                results.append(f"**Location: {row[0]}**\n{row[1][:200]}...")

            if not results:
                return f"No entities found matching '{query}'."

            return "\n\n".join(results)

        finally:
            conn.close()

    def show_page(self, page_number: int) -> str:
        """Get the full content of a specific page."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT page_number, section, content
                FROM pages WHERE page_number = ?
            """, (page_number,))

            row = cursor.fetchone()
            if not row:
                return f"Page {page_number} not found."

            return f"**Page {row[0]}** ({row[1] or 'General'}):\n\n{row[2]}"

        finally:
            conn.close()


def ai_search(query: str, api_key: str, db_tools: DatabaseTools) -> str:
    """Use Claude to intelligently answer the question."""

    client = anthropic.Anthropic(api_key=api_key)

    tools = [
        {
            "name": "search_manual",
            "description": "Full-text search across the Midwinter game manual. Returns relevant pages with snippets.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "quick_search",
            "description": "Search for characters, equipment, or locations by name.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Entity name"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "show_page",
            "description": "Display full content of a manual page by number.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "page_number": {"type": "integer", "description": "Page number"}
                },
                "required": ["page_number"]
            }
        }
    ]

    system_prompt = """You are a helpful assistant for the Midwinter video game (1989).
You have access to the game manual database. Use the search tools to find information
and provide accurate, helpful answers. Always search the manual before answering."""

    messages = [{"role": "user", "content": query}]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        tools=tools,
        messages=messages
    )

    max_iterations = 5
    iteration = 0

    while response.stop_reason == "tool_use" and iteration < max_iterations:
        iteration += 1
        tool_results = []
        assistant_content = response.content

        for block in assistant_content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id

                if tool_name == "search_manual":
                    result = db_tools.search_manual(tool_input["query"])
                elif tool_name == "quick_search":
                    result = db_tools.quick_search(tool_input["query"])
                elif tool_name == "show_page":
                    result = db_tools.show_page(tool_input["page_number"])
                else:
                    result = f"Unknown tool: {tool_name}"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result
                })

        messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

    final_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            final_text += block.text

    return final_text


# ============== STREAMLIT APP ==============

st.set_page_config(
    page_title="Midwinter Manual Search",
    page_icon="❄️",
    layout="centered"
)

st.title("❄️ Midwinter Manual Search")
st.markdown("*Ask questions about the Midwinter game (1989)*")

# Check database
db_path = get_database_path()
if not db_path:
    st.error("Database not found. Contact the administrator.")
    st.stop()

db_tools = DatabaseTools(db_path)

# Get API key (from secrets/environment - user never sees this)
api_key = get_api_key()

# Search interface
query = st.text_input(
    "What would you like to know?",
    placeholder="e.g., What body parts can be injured?"
)

col1, col2 = st.columns([1, 4])
with col1:
    search_clicked = st.button("Search", type="primary")

if search_clicked and query:
    with st.spinner("Searching the manual..."):
        if api_key and HAS_ANTHROPIC:
            try:
                result = ai_search(query, api_key, db_tools)
                st.markdown("---")
                st.markdown(result)
            except Exception as e:
                st.error(f"Search error: {e}")
        else:
            st.warning("AI search unavailable. Showing basic results:")
            st.markdown(db_tools.search_manual(query))

# Example questions
st.markdown("---")
st.markdown("**Try asking:**")
examples = [
    "What body parts can be injured?",
    "How does recruitment work?",
    "Who is Professor Kristiansen?",
    "What vehicles are available?",
    "How do I use the radio station?",
    "What happens when I destroy buildings?"
]

cols = st.columns(2)
for i, example in enumerate(examples):
    with cols[i % 2]:
        if st.button(example, key=f"ex_{i}"):
            st.session_state["query"] = example
            st.rerun()

# Footer
st.markdown("---")
st.caption("Powered by Claude AI • Database from the original Midwinter manual")
