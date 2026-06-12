#!/usr/bin/env python
"""
Heartfulness NGO Management System
Main Application Entry Point
"""

import os
import sys
from app import create_app, db

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Run the app on all network interfaces (so it can be accessed from other computers on the network)
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
