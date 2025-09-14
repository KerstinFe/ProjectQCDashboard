from ProjectQCDashboard.pipeline.runApp import app

# Gunicorn looks for a variable called 'server' or 'application'
server = app.server

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8000)