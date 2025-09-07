"""
Minimal FastAPI app to test if the server itself works.
This bypasses all our complex code.
"""

from fastapi import FastAPI
import uvicorn
import os

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Simple test server works!"}

@app.get("/test")
async def test():
    return {"status": "ok"}

@app.post("/test-post")
async def test_post():
    return {"method": "POST", "status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)