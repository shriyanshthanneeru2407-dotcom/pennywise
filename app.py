"""
app.py — Flask application entry point.

This file is the WSGI entry point for both local development and Vercel.

Local development:
    flask --app app run --debug

Vercel:
    Vercel looks for an `app` callable in this file.
    vercel.json points to this file.
"""

from app import create_app

# Create the application using the factory.
# FLASK_ENV environment variable selects 'development' or 'production'.
app = create_app()

if __name__ == "__main__":
    app.run()
