#!/usr/bin/env python3
"""
Ultra-minimal FastAPI app - NO complex imports
"""
import os

# Create the most basic FastAPI app possible
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="CryptoUniverse")

@app.get("/")
def root():
    return {"message": "CryptoUniverse API Running"}

@app.get("/api/v1/status")
def status():
    return {"status": "healthy", "service": "backend"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
