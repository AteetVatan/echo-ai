"""Extract all cached Q&A pairs for review."""
import sqlite3

conn = sqlite3.connect("src/db/audio_cache.db")
rows = conn.execute("SELECT user_text, response_text FROM reply_cache ORDER BY rowid").fetchall()
conn.close()

with open("_cache_review.md", "w", encoding="utf-8") as f:
    f.write("# Pre-Built Cache — All Answers for Review\n\n")
    for i, (q, a) in enumerate(rows, 1):
        f.write(f"---\n\n## Q{i}: {q}\n\n{a}\n\n")
    f.write(f"---\n\n**Total: {len(rows)} cached answers**\n")

print(f"Wrote {len(rows)} Q&A pairs to _cache_review.md")
