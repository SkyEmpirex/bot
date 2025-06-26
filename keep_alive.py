
from threading import Thread
import time

def run():
    from web import app
    app.run(host='0.0.0.0', port=8080, debug=False)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    Thread(target=run).start()
