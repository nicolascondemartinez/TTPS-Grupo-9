import os

from src.web import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=int(os.environ.get("FLASK_RUN_PORT", 5001)))