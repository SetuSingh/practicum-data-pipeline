#!/usr/bin/env python3
"""
API Package for Secure Data Pipeline Dashboard
Provides modular API endpoints organized by functionality
"""

from flask import Blueprint

# Create main API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import blueprints directly from route modules
from .routes.status import bp as status_bp
from .routes.files import bp as files_bp
from .routes.jobs import bp as jobs_bp
from .routes.database import bp as database_bp
from .routes.pipeline import bp as pipeline_bp

# Register route modules with the blueprint
api_bp.register_blueprint(status_bp)
api_bp.register_blueprint(files_bp)
api_bp.register_blueprint(jobs_bp)
api_bp.register_blueprint(database_bp)
api_bp.register_blueprint(pipeline_bp) 