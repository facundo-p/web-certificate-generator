from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['UPLOAD_FOLDER'] = 'app/uploads'

    # Register routes
    from app.routes import main
    app.register_blueprint(main)

    return app