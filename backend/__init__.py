import os
from flask import Flask
from backend.process_manager import start_watchdog

def create_app():
    # Because we are running from the parent directory, we need to explicitly
    # point Flask to the correct static and templates folders.
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )

    # Register routes
    from backend.routes_ui import ui_bp
    from backend.routes_api import api_bp

    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp)

    # Start the background watchdog thread for process monitoring
    start_watchdog()

    return app
