import os
import sys

# Set the Python path to your application's root directory
sys.path.insert(0, os.path.dirname(__file__))

# Import the create_app() factory function from your app package
from app import create_app

# Create the application instance and expose it as 'application'
# This is the object that Phusion Passenger will use to run your app
application = create_app()