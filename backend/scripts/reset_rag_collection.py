"""Reset ONLY the government_scheme_documents ChromaDB collection."""
import sqlite3
import shutil
import sys
from pathlib import Path

BASE = Path(r"d:\Codes\Final-Year-Project\AI-Powered-Government-Scheme-Fulfillment-Engine\backend")
DB = BASE / "storage" / "chromadb" / "chroma.sqlite3"
PERSIST = BASE / "storage" / "chromadb"

print("=== RAG Collection Reset ===")
print(f"DB: {DB}")

conn = sqlite3.connect(str(DB))
cur = conn.cursor()

# Find collection ID
rows = cur.execute(
    "SELECT id FROM collections WHERE name = ?", ("government_scheme_documents",)
).fetchall()
if not rows:
    print("Collection not found; nothing to do.")
    conn.close()
    sys.exit(0)

col_id = rows[0][0]
seg_ids = [r[0] for r in cur.execute(
    "SELECT id FROM segments WHERE collection = ?", (col_id,)
).fetchall()]
print(f"Collection: {col_id}")
print(f"Segments: {seg_ids}")

# Delete embedding metadata + embeddings for the RAG segments
for seg in seg_ids:
    emb_ids = [r[0] for r in cur.execute(
        "SELECT id FROM embeddings WHERE segment_id = ?", (seg,)
    ).fetchall()]
    print(f"  Segment {seg}: {len(emb_ids)} embeddings")
    for i in range(0, len(emb_ids), 900):
        batch = emb_ids[i:i + 900]
        ph = ",".join("?" * len(batch))
        cur.execute(f"DELETE FROM embedding_metadata WHERE id IN ({ph})", batch)
        cur.execute(f"DELETE FROM embeddings WHERE id IN ({ph})", batch)

# Delete segments + collection records
cur.execute("DELETE FROM segments WHERE collection = ?", (col_id,))
cur.execute("DELETE FROM collection_metadata WHERE collection_id = ?", (col_id,))
cur.execute("DELETE FROM collections WHERE id = ?", (col_id,))
conn.commit()
conn.close()

# Delete HNSW segment directories
for seg in seg_ids:
    d = PERSIST / seg
    if d.exists():
        shutil.rmtree(d)
        print(f"Deleted segment dir: {d}")

print("=== Reset Complete ===")