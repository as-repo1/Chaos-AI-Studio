from flask import Blueprint, render_template

ui_bp = Blueprint("ui", __name__)

@ui_bp.route("/")
def index():
    return render_template("dashboard.html")

@ui_bp.route("/models")
def models_page():
    return render_template("models.html")

@ui_bp.route("/chat")
def chat_page():
    return render_template("chat.html")

@ui_bp.route("/image")
def image_page():
    return render_template("image.html")

@ui_bp.route("/tts")
def tts_page():
    return render_template("tts.html")
