from fastapi import FastAPI

app = FastAPI(title="Chat with Your Docs API")


@app.get("/")
def root():
    return {"message": "API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}