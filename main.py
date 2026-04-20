from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Happin Backend v1.0 - Deployment Test erfolgreich!"}


@app.get("/health")
def health():
    return {"status": "healthy"}
