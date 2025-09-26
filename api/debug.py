"""
Debug endpoint to test URL parsing
"""

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path

        # Same parsing logic as oauth.py
        if '?' in path:
            base_path, query_string = path.split('?', 1)
            normalized_query = (query_string
                               .replace('?', '&')
                               .replace('%3F', '&')
                               .replace('%3D', '=')
                               .replace('%26', '&'))
            query_params = parse_qs(normalized_query)
        else:
            query_params = {}

        action = query_params.get('action', [''])[0]
        response_type = query_params.get('response_type', [''])[0]
        client_id = query_params.get('client_id', [''])[0]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        debug_info = {
            "original_path": path,
            "query_string_after_first_question": query_string if '?' in path else "",
            "normalized_query": normalized_query if '?' in path else "",
            "parsed_params": query_params,
            "extracted_action": action,
            "extracted_response_type": response_type,
            "extracted_client_id": client_id,
            "should_show_login": response_type == "code" and bool(client_id),
            "action_authorize_check": action == "authorize"
        }

        self.wfile.write(json.dumps(debug_info, indent=2).encode())