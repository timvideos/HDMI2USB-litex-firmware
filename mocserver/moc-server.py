import os
from http.server import HTTPServer, BaseHTTPRequestHandler

from pprint import pprint

def show_attribs(o):
    for k in dir(o):
        if not k.startswith("_") and not callable(getattr(o,k)):
            pprint("{}: {}".format(k, getattr(o,k)))

class web_server(BaseHTTPRequestHandler):

    def do_GET(self):
        show_attribs(self)

        if self.path == '/':
            self.path = '/index.html'

        try:
            content = open(self.path[1:]).read()
            self.send_response(200)
            if os.path.splitext(self.path)[1]==".json":
                self.send_header('Content-type', 'application/json')

        except FileNotFoundError as e:
            content = "File not found"
            self.send_response(404)

        self.end_headers()
        self.wfile.write(bytes(content, 'utf-8'))

httpd = HTTPServer(('localhost', 8087), web_server)
show_attribs(httpd)
httpd.serve_forever()

