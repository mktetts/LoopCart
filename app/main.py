import logging

import uvicorn
from config.settings import settings
from fastapi import FastAPI
from db.mongodb_manager import mongodb_manager
from fastapi.middleware.cors import CORSMiddleware
from routes import api_router


def create_application() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(api_router)
    return app


app = create_application()


def main() -> None:
    env = settings.ENVIRONTMENT.lower()
    if env == "production":
        uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=False, workers=1)
    else:
        uvicorn.run(
            "main:app", host=settings.HOST, port=settings.PORT, reload=True, reload_includes=".env"
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.exception("Application stopped")
