#!/usr/bin/env python3
"""
Midwinter Manual Search - AI-Powered GUI Application

A standalone search tool for the Midwinter game manual with Claude AI intelligence.
Ask questions in natural language just like talking to Claude!

Requires: Claude API key (get one at console.anthropic.com)

Can be packaged as standalone .exe with:
    pip install pyinstaller
    pyinstaller --onefile --windowed --add-data "database;database" midwinter_search_gui.py
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from pathlib import Path
import sys
import json
import threading

# Try to import anthropic
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def get_database_path():
    """Find the database file in various locations."""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
        db_path = base_path / "database" / "midwinter_unified.db"
        if db_path.exists():
            return db_path

    script_dir = Path(__file__).parent
    possible_paths = [
        script_dir / "database" / "midwinter_unified.db",
        script_dir.parent / "database" / "midwinter_unified.db",
        Path("database") / "midwinter_unified.db",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def get_config_path():
    """Get path for config file."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / "midwinter_search_config.json"
    return Path(__file__).parent / "midwinter_search_config.json"


class DatabaseTools:
    """Database search tools that Claude can use."""

    def __init__(self, db_path):
        self.db_path = db_path

    def get_connection(self):
        if not self.db_path:
            return None
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def quick_search(self, query: str) -> str:
        """Search for characters, buildings, vehicles by name."""
        conn = self.get_connection()
        if not conn:
            return "Database not available"

        results = []

        # Characters
        cursor = conn.execute("""
            SELECT full_name, title, age, occupation, biography
            FROM characters WHERE full_name LIKE ? OR biography LIKE ?
            LIMIT 10
        """, (f"%{query}%", f"%{query}%"))

        chars = cursor.fetchall()
        if chars:
            results.append("=== CHARACTERS ===")
            for c in chars:
                results.append(f"\n**{c['full_name']}**")
                if c['age']: results.append(f"  Age: {c['age']}")
                if c['occupation']: results.append(f"  Occupation: {c['occupation']}")
                if c['biography']: results.append(f"  Bio: {c['biography']}")

        # Buildings
        cursor = conn.execute("""
            SELECT building_type, description, gameplay_function
            FROM buildings WHERE building_type LIKE ? OR description LIKE ?
            LIMIT 10
        """, (f"%{query}%", f"%{query}%"))

        buildings = cursor.fetchall()
        if buildings:
            results.append("\n=== BUILDINGS ===")
            for b in buildings:
                results.append(f"\n**{b['building_type']}**")
                if b['description']: results.append(f"  {b['description']}")

        # Vehicles
        cursor = conn.execute("""
            SELECT vehicle_type, role, description
            FROM enemy_vehicles WHERE vehicle_type LIKE ? OR description LIKE ?
            LIMIT 10
        """, (f"%{query}%", f"%{query}%"))

        vehicles = cursor.fetchall()
        if vehicles:
            results.append("\n=== VEHICLES ===")
            for v in vehicles:
                results.append(f"\n**{v['vehicle_type']}**")
                if v['role']: results.append(f"  Role: {v['role']}")

        conn.close()
        return "\n".join(results) if results else f"No entities found for '{query}'"

    def search_manual(self, query: str) -> str:
        """Full-text search of manual pages."""
        conn = self.get_connection()
        if not conn:
            return "Database not available"

        try:
            cursor = conn.execute("""
                SELECT page_number, section_type,
                       snippet(manual_fts, 2, '>>>', '<<<', '...', 64) as snippet
                FROM manual_fts WHERE manual_fts MATCH ?
                ORDER BY bm25(manual_fts) LIMIT 10
            """, (query,))

            results = cursor.fetchall()
            conn.close()

            if not results:
                return f"No manual pages found for '{query}'"

            output = [f"Found {len(results)} pages:"]
            for r in results:
                output.append(f"\nPage {r['page_number']} [{r['section_type']}]: {r['snippet']}")

            return "\n".join(output)
        except:
            conn.close()
            # Fallback to LIKE search
            return self.search_manual_like(query)

    def search_manual_like(self, query: str) -> str:
        """Fallback LIKE search."""
        conn = self.get_connection()
        if not conn:
            return "Database not available"

        cursor = conn.execute("""
            SELECT page_number, section_type, content
            FROM manual_pages WHERE content LIKE ? LIMIT 10
        """, (f"%{query}%",))

        results = []
        for row in cursor.fetchall():
            content = row['content']
            pos = content.lower().find(query.lower())
            if pos >= 0:
                start = max(0, pos - 60)
                end = min(len(content), pos + len(query) + 60)
                snippet = "..." + content[start:end] + "..."
                results.append(f"\nPage {row['page_number']} [{row['section_type']}]: {snippet}")

        conn.close()
        return "\n".join(results) if results else f"No pages found for '{query}'"

    def show_page(self, page_number: int) -> str:
        """Show full content of a manual page."""
        conn = self.get_connection()
        if not conn:
            return "Database not available"

        cursor = conn.execute("""
            SELECT page_number, section_type, content
            FROM manual_pages WHERE page_number = ?
        """, (page_number,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return f"Page {page_number} not found"

        return f"=== PAGE {row['page_number']} [{row['section_type']}] ===\n\n{row['content']}"

    def list_characters(self) -> str:
        """List all characters."""
        conn = self.get_connection()
        if not conn:
            return "Database not available"

        cursor = conn.execute("SELECT full_name, age, occupation FROM characters ORDER BY full_name")
        chars = cursor.fetchall()
        conn.close()

        output = [f"=== ALL {len(chars)} CHARACTERS ===\n"]
        for c in chars:
            output.append(f"{c['full_name']} - Age {c['age']}, {c['occupation']}")

        return "\n".join(output)

    def list_buildings(self) -> str:
        """List all building types."""
        conn = self.get_connection()
        if not conn:
            return "Database not available"

        cursor = conn.execute("SELECT building_type, description FROM buildings ORDER BY building_type")
        buildings = cursor.fetchall()
        conn.close()

        output = [f"=== ALL {len(buildings)} BUILDINGS ===\n"]
        for b in buildings:
            output.append(f"{b['building_type']}: {b['description'] or 'No description'}")

        return "\n".join(output)


class MidwinterSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Midwinter Manual Search (AI-Powered)")
        self.root.geometry("950x750")
        self.root.minsize(700, 500)

        self.db_path = get_database_path()
        self.db_tools = DatabaseTools(self.db_path)
        self.api_key = None
        self.client = None

        self.load_config()
        self.create_widgets()
        self.show_welcome()

    def load_config(self):
        """Load API key from config file."""
        config_path = get_config_path()
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    self.api_key = config.get("api_key")
                    if self.api_key and HAS_ANTHROPIC:
                        self.client = anthropic.Anthropic(api_key=self.api_key)
            except:
                pass

    def save_config(self):
        """Save API key to config file."""
        config_path = get_config_path()
        try:
            with open(config_path, 'w') as f:
                json.dump({"api_key": self.api_key}, f)
        except:
            pass

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title and API status
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(title_frame, text="Midwinter Manual Search",
                  font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)

        self.api_status = ttk.Label(title_frame, text="", font=("Segoe UI", 9))
        self.api_status.pack(side=tk.RIGHT)

        api_btn = ttk.Button(title_frame, text="Set API Key", command=self.set_api_key)
        api_btn.pack(side=tk.RIGHT, padx=5)

        self.update_api_status()

        # Search frame
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="Ask anything:").pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=60)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self.do_search())

        self.search_btn = ttk.Button(search_frame, text="Search", command=self.do_search)
        self.search_btn.pack(side=tk.LEFT)

        # Results
        results_frame = ttk.LabelFrame(main_frame, text="Answer", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.results_text = scrolledtext.ScrolledText(
            results_frame, wrap=tk.WORD, font=("Consolas", 10), padx=10, pady=10
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)

        # Quick buttons
        quick_frame = ttk.Frame(main_frame)
        quick_frame.pack(fill=tk.X)

        ttk.Label(quick_frame, text="Quick:").pack(side=tk.LEFT, padx=(0, 5))

        for text, cmd in [
            ("All Characters", lambda: self.show_result(self.db_tools.list_characters())),
            ("All Buildings", lambda: self.show_result(self.db_tools.list_buildings())),
        ]:
            ttk.Button(quick_frame, text=text, command=cmd).pack(side=tk.LEFT, padx=2)

        # Status
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var).pack(fill=tk.X)

        self.search_entry.focus()

    def update_api_status(self):
        if not HAS_ANTHROPIC:
            self.api_status.config(text="anthropic package not installed", foreground="red")
        elif self.client:
            self.api_status.config(text="AI Ready", foreground="green")
        else:
            self.api_status.config(text="No API Key - basic search only", foreground="orange")

    def set_api_key(self):
        key = simpledialog.askstring(
            "Claude API Key",
            "Enter your Claude API key:\n(Get one at console.anthropic.com)",
            show='*'
        )
        if key:
            self.api_key = key.strip()
            if HAS_ANTHROPIC:
                self.client = anthropic.Anthropic(api_key=self.api_key)
            self.save_config()
            self.update_api_status()
            messagebox.showinfo("Success", "API key saved! You now have AI-powered search.")

    def show_welcome(self):
        if not self.db_path:
            self.results_text.insert(tk.END, "ERROR: Database not found!\n")
            return

        welcome = """Welcome to Midwinter Manual Search!

Ask questions in natural language, just like talking to Claude:

  "What body parts can be injured?"
  "How does Professor Kristiansen recruit people?"
  "What vehicles are in the game?"
  "Tell me about Captain Stark"
  "How do radio stations work?"

"""
        if self.client:
            welcome += "AI Mode: ENABLED - Full intelligent search active!\n"
        else:
            welcome += "Basic Mode: Set your Claude API key for intelligent answers.\n"
            welcome += "(Click 'Set API Key' button above)\n"

        self.results_text.insert(tk.END, welcome)

    def show_result(self, text):
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, text)

    def do_search(self):
        query = self.search_var.get().strip()
        if not query:
            return

        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Searching...\n")
        self.search_btn.config(state="disabled")
        self.root.update()

        # Run search in thread to keep UI responsive
        thread = threading.Thread(target=self._do_search_thread, args=(query,))
        thread.start()

    def _do_search_thread(self, query):
        try:
            if self.client:
                result = self.ai_search(query)
            else:
                result = self.basic_search(query)
        except Exception as e:
            result = f"Error: {str(e)}"

        # Update UI from main thread
        self.root.after(0, lambda: self._show_search_result(result))

    def _show_search_result(self, result):
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, result)
        self.search_btn.config(state="normal")
        self.status_var.set("Search complete")

    def ai_search(self, query):
        """Use Claude to intelligently answer the question."""

        # Define tools for Claude
        tools = [
            {
                "name": "search_manual",
                "description": "Search the Midwinter game manual for information. Use keywords relevant to the topic.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search keywords"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "quick_search",
                "description": "Look up specific characters, buildings, or vehicles by name.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Name to search for"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "show_page",
                "description": "Display a specific page from the manual.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "page_number": {"type": "integer", "description": "Page number (1-196)"}
                    },
                    "required": ["page_number"]
                }
            }
        ]

        system_prompt = """You are a helpful assistant for the Midwinter video game (1989).
You have access to the complete game manual database. Use the tools to search for information
and provide helpful, accurate answers about the game mechanics, characters, locations, and strategies.

When answering questions:
1. Use the search tools to find relevant information
2. Synthesize the information into a clear, helpful answer
3. If the manual doesn't cover something, say so

Keep answers concise but complete."""

        messages = [{"role": "user", "content": query}]

        # Initial request
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        # Handle tool calls
        while response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    # Execute the tool
                    if tool_name == "search_manual":
                        result = self.db_tools.search_manual(tool_input["query"])
                    elif tool_name == "quick_search":
                        result = self.db_tools.quick_search(tool_input["query"])
                    elif tool_name == "show_page":
                        result = self.db_tools.show_page(tool_input["page_number"])
                    else:
                        result = f"Unknown tool: {tool_name}"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt,
                tools=tools,
                messages=messages
            )

        # Extract final text response
        result_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                result_text += block.text

        return result_text or "No answer generated."

    def basic_search(self, query):
        """Basic keyword search without AI."""
        results = []

        # Try entity search
        entity = self.db_tools.quick_search(query)
        if "No entities found" not in entity:
            results.append(entity)

        # Try manual search
        manual = self.db_tools.search_manual(query)
        if "No manual pages found" not in manual and "No pages found" not in manual:
            results.append("\n" + "=" * 40 + "\nMANUAL PAGES:\n" + manual)

        if not results:
            # Try individual words
            words = [w for w in query.lower().split() if len(w) > 3]
            for word in words:
                manual = self.db_tools.search_manual(word)
                if "No manual pages found" not in manual:
                    results.append(f"\nResults for '{word}':\n{manual}")
                    break

        if not results:
            return f"No results found for '{query}'.\n\nTip: Set your Claude API key for intelligent search!"

        return "\n".join(results)


def main():
    global HAS_ANTHROPIC
    if not HAS_ANTHROPIC:
        # Try to install it
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic", "-q"])
            import anthropic
            HAS_ANTHROPIC = True
        except:
            pass

    root = tk.Tk()
    app = MidwinterSearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
