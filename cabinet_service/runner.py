import uvicorn

from config import CABINET_SERVICE_HOST, CABINET_SERVICE_PORT
from cabinet_service.app import app


def run():
    uvicorn.run(
        app,
        host=CABINET_SERVICE_HOST,
        port=CABINET_SERVICE_PORT,
        log_level="warning"
    )
