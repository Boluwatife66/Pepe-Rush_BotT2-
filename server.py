import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"PepeRush Bot is running!")
    
    def log_message(self, format, *args):
        pass  # suppress logs

def run_server():
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()

def start():
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
