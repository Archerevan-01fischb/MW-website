#!/usr/bin/env python3
"""
Flask API backend for Midwinter manual search
Implements MCP-style tools for Claude to use via Anthropic API

UPDATED: Added show_page, filter_by_section, better prompts, larger snippets
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import sqlite3
import os
import json
import uuid
import threading
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Job queue for async searches
search_jobs = {}

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), 'midwinter_unified.db')
KEY_FILE = os.path.join(os.path.dirname(__file__), '.anthropic_key')

def get_api_key():
    """Get API key from file (preferred) or environment"""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'r') as f:
            return f.read().strip()
    return os.environ.get('ANTHROPIC_API_KEY')

def get_client():
    """Get Anthropic client with current API key"""
    key = get_api_key()
    return anthropic.Anthropic(api_key=key) if key else None

# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

def search_manual_db(query: str) -> str:
    """Full-text search across the manual - returns larger snippets"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        results = []

        # Try FTS first with larger snippets
        try:
            cursor = conn.execute("""
                SELECT page_number, section_type,
                       snippet(manual_fts, 2, '>>>', '<<<', '...', 200) as snippet,
                       bm25(manual_fts) as rank
                FROM manual_fts
                WHERE manual_fts MATCH ?
                ORDER BY rank
                LIMIT 15
            """, (query,))
            results = cursor.fetchall()
        except:
            pass

        # If no FTS results, try LIKE search
        if not results:
            words = [w for w in query.split() if len(w) > 2]
            if words:
                where_clauses = " OR ".join([f"content LIKE ?" for _ in words])
                params = [f"%{word}%" for word in words]
                cursor = conn.execute(f"""
                    SELECT page_number, section_type,
                           substr(content, 1, 500) as snippet
                    FROM manual_pages
                    WHERE {where_clauses}
                    ORDER BY page_number
                    LIMIT 15
                """, params)
                results = cursor.fetchall()

        conn.close()

        if not results:
            return f"No results found for '{query}'. Try different keywords or check spelling."

        output = [f"Found {len(results)} results for '{query}':\n"]
        for r in results:
            output.append(f"**Page {r['page_number']}** [{r['section_type']}]")
            output.append(f"  {r['snippet']}\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error: {str(e)}"


def show_page_db(page_number: int) -> str:
    """Get full content of a specific page"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("""
            SELECT page_number, section_type, content
            FROM manual_pages
            WHERE page_number = ?
        """, (page_number,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return f"Page {page_number} not found. Valid pages are 1-196."

        return f"=== Page {row['page_number']} [{row['section_type']}] ===\n\n{row['content']}"

    except Exception as e:
        return f"Error: {str(e)}"


def filter_by_section_db(section: str, query: str) -> str:
    """Search within a specific section"""
    valid_sections = ['characters', 'equipment', 'locations', 'story_sections', 'general_content']

    if section not in valid_sections:
        return f"Invalid section '{section}'. Valid sections: {', '.join(valid_sections)}"

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        results = []

        # Try FTS with section filter
        try:
            cursor = conn.execute("""
                SELECT page_number, section_type,
                       snippet(manual_fts, 2, '>>>', '<<<', '...', 200) as snippet,
                       bm25(manual_fts) as rank
                FROM manual_fts
                WHERE manual_fts MATCH ? AND section_type = ?
                ORDER BY rank
                LIMIT 15
            """, (query, section))
            results = cursor.fetchall()
        except:
            pass

        # Fallback to LIKE
        if not results:
            words = [w for w in query.split() if len(w) > 2]
            if words:
                where_clauses = " OR ".join([f"content LIKE ?" for _ in words])
                params = [f"%{word}%" for word in words]
                cursor = conn.execute(f"""
                    SELECT page_number, section_type,
                           substr(content, 1, 500) as snippet
                    FROM manual_pages
                    WHERE ({where_clauses}) AND section_type = ?
                    ORDER BY page_number
                    LIMIT 15
                """, params + [section])
                results = cursor.fetchall()

        conn.close()

        if not results:
            return f"No results for '{query}' in {section} section."

        output = [f"Found {len(results)} results for '{query}' in {section}:\n"]
        for r in results:
            output.append(f"**Page {r['page_number']}** [{r['section_type']}]")
            output.append(f"  {r['snippet']}\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error: {str(e)}"


def quick_search_db(query: str) -> str:
    """Fast entity lookup for characters, buildings, etc."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        results = []

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
                    bio = c['biography'][:500] + "..." if len(c['biography']) > 500 else c['biography']
                    results.append(f"  Bio: {bio}")

        conn.close()

        if not results:
            return f"No entities found matching '{query}'"

        return "\n".join(results)

    except Exception as e:
        return f"Error: {str(e)}"


# =============================================================================
# TOOL DEFINITIONS FOR CLAUDE
# =============================================================================

TOOLS = [
    {
        "name": "search_manual",
        "description": "Full-text search across the Midwinter game manual. Returns page numbers with text snippets. Use this first to find relevant pages, then use show_page to read the full content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords - try single important words first, then phrases"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "show_page",
        "description": "Get the FULL content of a specific manual page. Use this after search_manual finds a promising page to read all the details and verify information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_number": {
                    "type": "integer",
                    "description": "Page number to display (1-196)"
                }
            },
            "required": ["page_number"]
        }
    },
    {
        "name": "filter_by_section",
        "description": "Search within a specific manual section: characters, equipment, locations, story_sections, or general_content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "enum": ["characters", "equipment", "locations", "story_sections", "general_content"],
                    "description": "Section to search in"
                },
                "query": {
                    "type": "string",
                    "description": "Search keywords"
                }
            },
            "required": ["section", "query"]
        }
    },
    {
        "name": "quick_search",
        "description": "Fast lookup for character details by name. Returns biography, occupation, age.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Character name to search for"
                }
            },
            "required": ["query"]
        }
    }
]


# =============================================================================
# SYSTEM PROMPT FOR BETTER SEARCH BEHAVIOR
# =============================================================================

SYSTEM_PROMPT = """You are a search assistant for the 1989 video game Midwinter's manual.

IMPORTANT SEARCH STRATEGY:
1. Start with search_manual using simple keywords (one or two words work best)
2. If a search result looks promising, ALWAYS use show_page to read the FULL page content before answering
3. If your first search doesn't find what you need, try different keywords or synonyms
4. For game mechanics questions, search for the mechanic name directly (e.g., "morale", "energy", "skiing")
5. For "how does X work" questions, also try searching for related terms

VERIFICATION RULE:
- Never answer based only on search snippets - they may be incomplete
- Always verify by reading the full page with show_page before giving a definitive answer
- If you cannot find clear information after multiple searches, say so honestly

ANSWER FORMAT:
- Be concise but complete
- Cite page numbers for your sources
- Use **bold** for key game terms
- If the manual doesn't cover something, say "The manual does not explicitly cover this" rather than guessing"""


def execute_tool(name: str, input_data: dict) -> str:
    """Execute a tool by name"""
    if name == "search_manual":
        return search_manual_db(input_data["query"])
    elif name == "show_page":
        return show_page_db(input_data["page_number"])
    elif name == "filter_by_section":
        return filter_by_section_db(input_data["section"], input_data["query"])
    elif name == "quick_search":
        return quick_search_db(input_data["query"])
    else:
        return f"Unknown tool: {name}"


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'api_configured': get_api_key() is not None,
        'database_configured': os.path.exists(DB_PATH),
        'version': '2.0'
    })


@app.route('/api/search/fast', methods=['POST'])
def search_fast():
    """Fast search - 2 tool rounds max, uses Haiku"""
    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({'error': 'Query parameter required'}), 400

    client = get_client()
    if not client:
        return jsonify({'error': 'API not configured'}), 500

    try:
        messages = [{"role": "user", "content": query}]

        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # Process up to 2 rounds of tool calls
        rounds = 0
        while response.stop_reason == "tool_use" and rounds < 2:
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

            response = client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )
            rounds += 1

        # Extract text
        answer = ""
        for block in response.content:
            if hasattr(block, 'text'):
                answer += block.text

        return jsonify({
            'success': True,
            'query': query,
            'results': [],
            'raw_response': answer or "No results found."
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search', methods=['POST'])
def search():
    """Main search endpoint - uses Sonnet, up to 5 tool rounds"""
    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({'error': 'Query parameter required'}), 400

    client = get_client()
    if not client:
        return jsonify({'error': 'API not configured'}), 500

    try:
        messages = [{"role": "user", "content": query}]

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # Process up to 5 rounds of tool calls
        rounds = 0
        while response.stop_reason == "tool_use" and rounds < 5:
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )
            rounds += 1

        # Extract final text
        final_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                final_text += block.text

        # Parse page references for structured results
        import re
        results = []
        page_pattern = r'\*\*Page (\d+)\*\* \[([^\]]+)\]'
        matches = re.finditer(page_pattern, final_text)

        for match in matches:
            start = match.end()
            next_match = re.search(r'\*\*Page \d+\*\*', final_text[start:])
            end = start + next_match.start() if next_match else len(final_text)
            snippet = final_text[start:end].strip()

            results.append({
                'page_number': int(match.group(1)),
                'section': match.group(2),
                'content': snippet[:500]
            })

        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'raw_response': final_text if not results else None
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search/section', methods=['POST'])
def search_section():
    """Search within a specific section"""
    data = request.get_json()
    query = data.get('query', '').strip()
    section = data.get('section', '')

    if not query:
        return jsonify({'error': 'Query parameter required'}), 400

    data['query'] = f"Search the {section} section for: {query}"
    return search()


# =============================================================================
# ASYNC SEARCH (for long-running queries)
# =============================================================================

def run_search_job(job_id, query):
    """Run search in background thread"""
    try:
        search_jobs[job_id]['status'] = 'running'

        client = get_client()
        if not client:
            search_jobs[job_id] = {'status': 'error', 'error': 'API not configured'}
            return

        messages = [{"role": "user", "content": query}]

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # Process up to 6 rounds
        rounds = 0
        while response.stop_reason == "tool_use" and rounds < 6:
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )
            rounds += 1

        # Force final answer if still requesting tools
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results + [{"type": "text", "text": "Now provide your final answer based on all search results."}]})
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=messages
            )

        # Extract final text
        final_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                final_text += block.text

        # Parse results
        import re
        results = []
        page_pattern = r'\*\*Page (\d+)\*\* \[([^\]]+)\]'
        matches = re.finditer(page_pattern, final_text)

        for match in matches:
            start = match.end()
            next_match = re.search(r'\*\*Page \d+\*\*', final_text[start:])
            end = start + next_match.start() if next_match else len(final_text)
            snippet = final_text[start:end].strip()

            results.append({
                'page_number': int(match.group(1)),
                'section': match.group(2),
                'content': snippet[:500]
            })

        search_jobs[job_id] = {
            'status': 'complete',
            'result': {
                'success': True,
                'query': query,
                'results': results,
                'raw_response': final_text if not results else None
            }
        }

    except Exception as e:
        search_jobs[job_id] = {'status': 'error', 'error': str(e)}


@app.route('/api/search/start', methods=['POST'])
def search_start():
    """Start async search - returns job_id immediately"""
    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({'error': 'Query parameter required'}), 400

    job_id = str(uuid.uuid4())[:8]
    search_jobs[job_id] = {'status': 'pending', 'created': datetime.now().isoformat()}

    thread = threading.Thread(target=run_search_job, args=(job_id, query))
    thread.daemon = True
    thread.start()

    return jsonify({'job_id': job_id, 'status': 'pending'})


@app.route('/api/search/status/<job_id>', methods=['GET'])
def search_status(job_id):
    """Check async search status"""
    if job_id not in search_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = search_jobs[job_id]

    if job['status'] == 'complete':
        result = job['result']
        del search_jobs[job_id]
        return jsonify({'status': 'complete', 'result': result})
    elif job['status'] == 'error':
        error = job.get('error', 'Unknown error')
        del search_jobs[job_id]
        return jsonify({'status': 'error', 'error': error})
    else:
        return jsonify({'status': job['status']})


# =============================================================================
# MAILING LIST ENDPOINT
# =============================================================================

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GMAIL_USER = 'lane01evan@gmail.com'
GMAIL_APP_PASSWORD = 'onkojkqiecgkktbo'

rate_limit_cache = {}

@app.route('/api/mailing-list', methods=['POST', 'OPTIONS'])
def mailing_list():
    if request.method == 'OPTIONS':
        return '', 200

    name = request.form.get('name', 'Anonymous').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', 'fan').strip()
    message = request.form.get('message', '').strip()

    ip = request.remote_addr

    now = datetime.now().timestamp()
    if ip in rate_limit_cache:
        if now - rate_limit_cache[ip] < 60:
            return jsonify({'success': False, 'message': 'Please wait before submitting again'}), 429

    if not email or '@' not in email:
        return jsonify({'success': False, 'message': 'Valid email required'}), 400

    try:
        msg = MIMEMultipart()
        msg['From'] = f'MW Website <{GMAIL_USER}>'
        msg['To'] = GMAIL_USER
        msg['Reply-To'] = email
        msg['Subject'] = f'MW Mailing List: New {role} signup'

        body = f"""New Midwinter Mailing List Submission

Name: {name}
Email: {email}
Role: {role}
Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
IP: {ip}

Message:
{message if message else '(none)'}
"""
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        rate_limit_cache[ip] = now

        log_file = os.path.join(os.path.dirname(__file__), 'mailing_list.csv')
        with open(log_file, 'a') as f:
            if os.path.getsize(log_file) == 0:
                f.write('timestamp,name,email,role,message,ip\n')
            f.write(f'"{datetime.now()}","{name}","{email}","{role}","{message.replace(chr(34), chr(39))}","{ip}"\n')

        return jsonify({'success': True, 'message': 'Welcome to the resistance! You have been added to the mailing list.'})

    except Exception as e:
        print(f'Mailing list error: {e}')
        return jsonify({'success': False, 'message': 'Error sending email. Please try Discord instead.'}), 500


if __name__ == '__main__':
    print("Starting Midwinter Manual Search API v2.0...")
    print(f"API Key configured: {get_api_key() is not None}")
    print(f"Database path: {DB_PATH}")
    print(f"Database exists: {os.path.exists(DB_PATH)}")
    app.run(host='0.0.0.0', port=5000, debug=True)
