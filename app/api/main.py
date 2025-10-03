# app/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import sessions, results

app = FastAPI(title="BANT Survey Prototype", version="1.0.0")

# CORS middleware для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(sessions.router)
app.include_router(results.router)

@app.get("/health")
def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "BANT Survey API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
