from flask import Flask
from werkzeug.exceptions import HTTPException
from .logging_config import setup_logging
import os
def create_app():
    # 1. Set up logging **before** app instantiation to capture all logs
    setup_logging()


    # 2. Create app

    app = Flask(
        __name__,
        static_folder='calculator/build',
        template_folder='calculator/build'
    )

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    app.secret_key = os.environ.get('FLASK_SECRET_KEY')
    if not app.secret_key:
            # For production, it's critical to have a secret key.
            # You might raise an exception to prevent the app from starting in an insecure state.
            app.logger.critical("FLASK_SECRET_KEY not set! Session management will be insecure or fail.")


    # 3. Register views
    from .routes import bp as calculator_blueprint
    app.register_blueprint(calculator_blueprint)

    app.logger.info("Flask application initialized.")

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Pass through HTTP errors
        if isinstance(e, HTTPException):
            return e

        # Log internal server errors (500) with traceback
        app.logger.exception('Unhandled exception during request processing.')
        return "Internal Server Error", 500

    return app
