from fair3r_custom_overlay import create_app
from fair3r_custom_overlay.lib import config

app = create_app()

if __name__ == '__main__':
    # Run the app in debug mode if in development
    debug_mode = config.CONTEXT == 'dev' and config.DEBUG
    app.run(debug=debug_mode, host='0.0.0.0', port=8080)
