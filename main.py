from flask import Flask
from flask_cors import CORS
import waitress
import rest_api
from flask_caching import Cache


if __name__ == '__main__':
    app = Flask(__name__)
    app.config.from_mapping({'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 24 * 60 * 60})
    cache = Cache(app)
    CORS(app)
    app.register_blueprint(rest_api.construct_blueprint(cache))
    waitress.serve(app, host='0.0.0.0', port=8003)
