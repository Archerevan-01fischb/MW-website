#!/usr/bin/env python3
"""
Extract character relationships from biographies and build a recruitment matrix.
Uses direct extraction based on manual analysis of character bios.
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "midwinter_unified.db"

# Direct relationship definitions based on manual bio analysis
# Format: (from_character, to_character, relationship_type, sentiment)
RELATIONSHIPS = [
    # Captain John Stark
    ("Captain John Stark", "Lieutenant Howard Courtenay", "friend", "positive"),
    ("Captain John Stark", "Karl Rudzinski", "friend", "positive"),
    ("Captain John Stark", "Nurse Sarah Maddocks", "lover", "positive"),

    # Constable Harvey Pringle
    ("Constable Harvey Pringle", "Constable Gordon Macleod", "regards_as_friend", "positive"),
    ("Constable Harvey Pringle", "Constable Fergus Flynn", "regards_as_friend", "positive"),
    ("Constable Harvey Pringle", "Jean-Luc Chabrun", "blames", "negative"),

    # Constable Gordon Macleod
    ("Constable Gordon Macleod", "Franco Grazzini", "dislikes", "negative"),
    ("Franco Grazzini", "Constable Gordon Macleod", "dislikes", "negative"),
    ("Sergeant George Tasker", "Constable Gordon Macleod", "respects", "positive"),
    ("Captain John Stark", "Constable Gordon Macleod", "respects", "positive"),

    # Constable Fergus Flynn - no specific friends/enemies listed beyond being target of jokes

    # Karl Rudzinski
    ("Karl Rudzinski", "Virginia Caygill", "engaged", "positive"),
    ("Karl Rudzinski", "Jeremiah Gunn", "dislikes", "negative"),
    ("Karl Rudzinski", "Franco Grazzini", "dislikes", "negative"),
    ("Karl Rudzinski", "Captain John Stark", "mentor", "positive"),

    # Franco Grazzini
    ("Franco Grazzini", "Virginia Caygill", "in_love", "positive"),
    ("Franco Grazzini", "Karl Rudzinski", "hates", "negative"),
    ("Franco Grazzini", "Nurse Sarah Maddocks", "admires", "positive"),

    # Jean-Luc Chabrun
    ("Jean-Luc Chabrun", "Constable Fergus Flynn", "friend", "positive"),
    ("Jean-Luc Chabrun", "Constable Gordon Macleod", "friend", "positive"),
    ("Sergeant Victor Grice", "Jean-Luc Chabrun", "hates", "negative"),
    ("Constable Harvey Pringle", "Jean-Luc Chabrun", "hates", "negative"),
    ("Constable Bill Doughty", "Jean-Luc Chabrun", "hates", "negative"),

    # Sergeant George Tasker
    ("Sergeant George Tasker", "Doctor Pierre Revel", "unforgiven", "negative"),
    ("Sergeant George Tasker", "Jeremiah Gunn", "disapproves", "negative"),
    ("Sergeant George Tasker", "Lieutenant Charles Ambler", "disapproves", "negative"),

    # Sergeant Tom Llewellyn - bears few grudges, most colleagues are friends
    ("Lieutenant Barnaby Gaunt", "Sergeant Tom Llewellyn", "dislikes", "negative"),
    ("Gregory Flint", "Sergeant Tom Llewellyn", "grudge", "negative"),

    # Sergeant Victor Grice
    ("Sergeant Victor Grice", "Captain John Stark", "resents", "negative"),
    ("Sergeant Victor Grice", "Lieutenant Barnaby Gaunt", "resents", "negative"),
    ("Sergeant Victor Grice", "Lieutenant Howard Courtenay", "respects", "positive"),

    # Doctor Pierre Revel
    ("Doctor Pierre Revel", "Lieutenant Howard Courtenay", "friend", "positive"),

    # Konrad Rudel
    ("Konrad Rudel", "Davy Hart", "friend", "positive"),

    # Virginia Caygill
    ("Virginia Caygill", "Karl Rudzinski", "engaged", "positive"),
    ("Virginia Caygill", "Doctor Pierre Revel", "despises", "negative"),
    ("Virginia Caygill", "Davy Hart", "teacher", "positive"),
    ("Virginia Caygill", "Jenny Adams", "teacher", "positive"),

    # Professor Olaf Kristiansen
    ("Professor Olaf Kristiansen", "Captain John Stark", "dislikes", "negative"),
    ("Professor Olaf Kristiansen", "Lieutenant Howard Courtenay", "dislikes", "negative"),
    ("Professor Olaf Kristiansen", "Gregory Flint", "friend", "positive"),
    ("Professor Olaf Kristiansen", "Davy Hart", "grandparent", "positive"),

    # Jeremiah Gunn
    ("Jeremiah Gunn", "Franco Grazzini", "friend", "positive"),
    ("Jeremiah Gunn", "Nurse Sarah Maddocks", "friend", "positive"),

    # Constable Federico Garcia
    ("Constable Federico Garcia", "Constable Kurt Muller", "friend", "positive"),

    # Constable Homer Wright
    ("Constable Homer Wright", "Constable Kurt Muller", "friend", "positive"),
    ("Constable Homer Wright", "Constable Oliver Jessop", "friend", "positive"),
    ("Constable Homer Wright", "Constable Shigeru Iwamoto", "friend", "positive"),
    ("Constable Luke Jackson", "Constable Homer Wright", "loathes", "negative"),

    # Constable Harry Cropper - has host of friends (general)

    # Constable Shigeru Iwamoto
    ("Constable Shigeru Iwamoto", "Constable Homer Wright", "friend", "positive"),

    # Constable Bill Doughty
    ("Constable Bill Doughty", "Constable Kurt Muller", "friend", "positive"),
    ("Constable Bill Doughty", "Constable Federico Garcia", "friend", "positive"),
    ("Lieutenant Howard Courtenay", "Constable Bill Doughty", "dislikes", "negative"),

    # Lieutenant Howard Courtenay
    ("Lieutenant Howard Courtenay", "Captain John Stark", "friend", "positive"),
    ("Lieutenant Howard Courtenay", "Virginia Caygill", "family", "positive"),
    ("Lieutenant Howard Courtenay", "Doctor Pierre Revel", "friend", "positive"),

    # Davy Hart
    ("Davy Hart", "Professor Olaf Kristiansen", "grandchild", "positive"),
    ("Davy Hart", "Konrad Rudel", "hero", "positive"),
    ("Davy Hart", "Jenny Adams", "boyfriend", "positive"),
    ("Davy Hart", "Virginia Caygill", "crush", "positive"),

    # Jenny Adams
    ("Jenny Adams", "Nurse Sarah Maddocks", "admires", "positive"),
    ("Jenny Adams", "Davy Hart", "boyfriend", "positive"),

    # Constable Bob Hammond
    ("Constable Bob Hammond", "Constable Harry Cropper", "friend", "positive"),

    # Constable Oliver Jessop
    ("Constable Oliver Jessop", "Constable Fergus Flynn", "dislikes", "negative"),
    ("Constable Oliver Jessop", "Constable Gordon Macleod", "dislikes", "negative"),
    ("Constable Oliver Jessop", "Constable Homer Wright", "friend", "positive"),
    ("Constable Oliver Jessop", "Constable Shigeru Iwamoto", "friend", "positive"),

    # Lieutenant Barnaby Gaunt
    ("Lieutenant Barnaby Gaunt", "Captain John Stark", "respects", "positive"),
    ("Lieutenant Barnaby Gaunt", "Sergeant George Tasker", "respects", "positive"),
    ("Lieutenant Barnaby Gaunt", "Sergeant Tom Llewellyn", "scornful", "negative"),
    ("Lieutenant Barnaby Gaunt", "Lieutenant Charles Ambler", "scornful", "negative"),
    ("Lieutenant Barnaby Gaunt", "Constable Fergus Flynn", "scornful", "negative"),
    ("Lieutenant Barnaby Gaunt", "Constable Harry Cropper", "scornful", "negative"),

    # Nurse Sarah Maddocks
    ("Nurse Sarah Maddocks", "Captain John Stark", "lover", "positive"),
    ("Nurse Sarah Maddocks", "Franco Grazzini", "fond", "positive"),
    ("Nurse Sarah Maddocks", "Doctor Pierre Revel", "dislikes", "negative"),

    # Constable Kurt Muller
    ("Constable Kurt Muller", "Constable Federico Garcia", "friend", "positive"),
    ("Constable Kurt Muller", "Constable Bill Doughty", "friend", "positive"),
    ("Constable Kurt Muller", "Constable Homer Wright", "friend", "positive"),
    ("Constable Kurt Muller", "Constable Shigeru Iwamoto", "dislikes", "negative"),

    # Constable Luke Jackson
    ("Constable Luke Jackson", "Captain John Stark", "hates", "negative"),
    ("Constable Luke Jackson", "Constable Federico Garcia", "friend", "positive"),
    ("Constable Luke Jackson", "Gregory Flint", "friend", "positive"),

    # Gregory Flint
    ("Gregory Flint", "Captain John Stark", "blames", "negative"),
    ("Gregory Flint", "Lieutenant Barnaby Gaunt", "blames", "negative"),
    ("Gregory Flint", "Sergeant Tom Llewellyn", "blames", "negative"),
    ("Gregory Flint", "Professor Olaf Kristiansen", "friend", "positive"),
    ("Gregory Flint", "Constable Luke Jackson", "friend", "positive"),
    ("Gregory Flint", "Constable Fergus Flynn", "friend", "positive"),

    # Lieutenant Charles Ambler
    ("Lieutenant Charles Ambler", "Karl Rudzinski", "friend", "positive"),
    ("Lieutenant Charles Ambler", "Constable Harry Cropper", "friend", "positive"),
    ("Lieutenant Charles Ambler", "Lieutenant Barnaby Gaunt", "dislikes", "negative"),

    # Mrs Amelia Randles - liked by everyone (special case)
]


def build_relationship_database():
    """Build the relationship database from direct definitions."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row

    # Create relationships table
    conn.execute("DROP TABLE IF EXISTS character_relationships")
    conn.execute("""
        CREATE TABLE character_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_character TEXT NOT NULL,
            to_character TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            UNIQUE(from_character, to_character, relationship_type)
        )
    """)
    conn.execute("CREATE INDEX idx_rel_from ON character_relationships(from_character)")
    conn.execute("CREATE INDEX idx_rel_to ON character_relationships(to_character)")
    conn.execute("CREATE INDEX idx_rel_sentiment ON character_relationships(sentiment)")

    # Insert all relationships
    for from_char, to_char, rel_type, sentiment in RELATIONSHIPS:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO character_relationships
                (from_character, to_character, relationship_type, sentiment)
                VALUES (?, ?, ?, ?)
            """, (from_char, to_char, rel_type, sentiment))
        except Exception as e:
            print(f"Error inserting {from_char} -> {to_char}: {e}")

    conn.commit()

    # Print summary
    cursor = conn.execute("SELECT COUNT(*) as count FROM character_relationships")
    total = cursor.fetchone()['count']

    cursor = conn.execute("SELECT COUNT(*) as count FROM character_relationships WHERE sentiment = 'positive'")
    positive = cursor.fetchone()['count']

    cursor = conn.execute("SELECT COUNT(*) as count FROM character_relationships WHERE sentiment = 'negative'")
    negative = cursor.fetchone()['count']

    print(f"Built relationship database with {total} relationships:")
    print(f"  - {positive} positive (can recruit)")
    print(f"  - {negative} negative (cannot recruit)")

    conn.close()
    return total


def test_queries():
    """Test some relationship queries."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row

    print("\n=== Can Stark recruit? ===")
    cursor = conn.execute("""
        SELECT to_character, relationship_type
        FROM character_relationships
        WHERE from_character = 'Captain John Stark' AND sentiment = 'positive'
    """)
    for row in cursor.fetchall():
        print(f"  {row['to_character']} ({row['relationship_type']})")

    print("\n=== Who cannot recruit Stark? ===")
    cursor = conn.execute("""
        SELECT from_character, relationship_type
        FROM character_relationships
        WHERE to_character = 'Captain John Stark' AND sentiment = 'negative'
    """)
    for row in cursor.fetchall():
        print(f"  {row['from_character']} ({row['relationship_type']})")

    print("\n=== Who can recruit Wright? ===")
    cursor = conn.execute("""
        SELECT from_character, relationship_type
        FROM character_relationships
        WHERE to_character LIKE '%Wright%' AND sentiment = 'positive'
    """)
    for row in cursor.fetchall():
        print(f"  {row['from_character']} ({row['relationship_type']})")

    print("\n=== Who can recruit Adams? ===")
    cursor = conn.execute("""
        SELECT from_character, relationship_type
        FROM character_relationships
        WHERE to_character LIKE '%Adams%' AND sentiment = 'positive'
    """)
    for row in cursor.fetchall():
        print(f"  {row['from_character']} ({row['relationship_type']})")

    print("\n=== Are Llewellyn/Wright enemies with Adams? ===")
    cursor = conn.execute("""
        SELECT from_character, to_character, relationship_type
        FROM character_relationships
        WHERE ((from_character LIKE '%Llewellyn%' AND to_character LIKE '%Adams%')
           OR (from_character LIKE '%Adams%' AND to_character LIKE '%Llewellyn%')
           OR (from_character LIKE '%Wright%' AND to_character LIKE '%Adams%')
           OR (from_character LIKE '%Adams%' AND to_character LIKE '%Wright%'))
          AND sentiment = 'negative'
    """)
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f"  {row['from_character']} -> {row['to_character']}: {row['relationship_type']}")
    else:
        print("  No - they are not enemies")

    conn.close()


if __name__ == "__main__":
    print("Building character relationship database...")
    build_relationship_database()
    test_queries()
