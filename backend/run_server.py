import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import uvicorn
from app.main import app
uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", access_log=False)
