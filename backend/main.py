"""
Legacy entry point redirection.
Redirects to the modular app entry point at app.main.
"""

from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
