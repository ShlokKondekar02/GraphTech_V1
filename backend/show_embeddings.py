import psycopg2

conn = psycopg2.connect('postgresql://postgres:password@localhost:5432/GraphTech')
cur = conn.cursor()

cur.execute("""
    SELECT 
        ROW_NUMBER() OVER (ORDER BY created_at) as num,
        LEFT(prompt, 60) as prompt,
        diagram_type,
        embedding::text as raw_vec
    FROM diagram_requests
    ORDER BY created_at
""")

rows = cur.fetchall()

print(f"{'='*80}")
print(f"  pgvector — diagram_requests.embedding  ({len(rows)} rows)")
print(f"{'='*80}\n")

for row in rows:
    num, prompt, dtype, raw_vec = row
    # parse the vector string "[v1,v2,...,v1024]"
    values = [float(x) for x in raw_vec.strip('[]').split(',')]
    
    # stats
    min_v  = min(values)
    max_v  = max(values)
    mean_v = sum(values) / len(values)
    norm   = sum(v*v for v in values) ** 0.5
    nonzero = sum(1 for v in values if abs(v) > 1e-6)
    
    print(f"  Row #{num}  [{dtype}]")
    print(f"  Prompt : {prompt}...")
    print(f"  Dims   : {len(values)}  |  Non-zero: {nonzero}")
    print(f"  Min    : {min_v:.6f}  |  Max: {max_v:.6f}  |  Mean: {mean_v:.6f}  |  L2-norm: {norm:.4f}")
    print(f"  First 8 dims : [{', '.join(f'{v:.4f}' for v in values[:8])}]")
    print(f"  Last  8 dims : [{', '.join(f'{v:.4f}' for v in values[-8:])}]")
    print()

# Show similarity of row 1 against all others
cur.execute("""
    SELECT 
        LEFT(b.prompt, 55) as prompt,
        b.diagram_type,
        ROUND(CAST(1 - (a.embedding <=> b.embedding) AS numeric), 5) as cosine_sim
    FROM diagram_requests a
    JOIN diagram_requests b ON a.id != b.id
    WHERE a.created_at = (SELECT MIN(created_at) FROM diagram_requests)
    ORDER BY cosine_sim DESC
""")
results = cur.fetchall()
print(f"{'='*80}")
print(f"  Cosine similarity of Row #1 (microservices e-commerce) vs all others")
print(f"{'='*80}")
for r in results:
    bar = '█' * int(r[2] * 40)
    print(f"  {r[2]:.5f}  {bar:<40}  {r[1]:<14}  {r[0][:50]}")

conn.close()
