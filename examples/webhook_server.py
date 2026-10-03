"""MISTA_WEBHOOK_SECRET=whsec_... python examples/webhook_server.py

Receives delivery report webhooks on http://localhost:3000/webhooks/mista (standard library only).
"""

import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from mista import SIGNATURE_HEADER, WebhookVerificationError, verify_webhook

SECRET = os.environ.get("MISTA_WEBHOOK_SECRET", "")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/webhooks/mista":
            self.send_response(404)
            self.end_headers()
            return

        raw_body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            event = verify_webhook(raw_body, self.headers.get(SIGNATURE_HEADER), SECRET)
        except WebhookVerificationError as error:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(str(error).encode())
            return

        data = event["data"]
        print(event["type"], data["uid"], data["status"], data["status_detail"] or "")
        self.send_response(200)
        self.end_headers()


if __name__ == "__main__":
    print("Listening on http://localhost:3000/webhooks/mista")
    HTTPServer(("", 3000), Handler).serve_forever()
