from fastapi import FastAPI, Query

app = FastAPI()
_memory = []

@app.get("/health")
def health():
    return "ok"

@app.get("/eat")
def eat(mb: int = Query(..., gt=0)):
    chunk = b"x" * (mb * 1024 * 1024)
    _memory.append(chunk)
    return {"allocated_mb": mb, "chunks": len(_memory)}

@app.get("/burn")
def burn():
    while True:
        pass