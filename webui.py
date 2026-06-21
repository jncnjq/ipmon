#!/usr/bin/env python3
import json
from http.server import (
    HTTPServer,
    BaseHTTPRequestHandler
)
from urllib.parse import (
    urlparse,
    parse_qs
)
from constants import (
    state_to_text,
    availability,
    tier
)
from db import db
class WebHandler(BaseHTTPRequestHandler):
    server_version = "IPMON/2.0"
    def log_message(self, fmt, *args):
        return
    def send_html(self, content):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )
        self.end_headers()
        self.wfile.write(
            content.encode("utf-8")
        )
    def send_json(self, obj):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "application/json"
        )
        self.end_headers()
        self.wfile.write(
            json.dumps(
                obj,
                ensure_ascii=False,
                indent=2
            ).encode("utf-8")
        )
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.show_status(parsed)
            return
        if parsed.path == "/events":
            self.show_events()
            return
        if parsed.path == "/api/status":
            self.api_status(parsed)
            return
        if parsed.path == "/api/events":
            self.api_events()
            return
        self.send_response(404)
        self.end_headers()
    def show_status(self, parsed):
        args = parse_qs(parsed.query)
        group_filter = args.get(
            "group",
            [None]
        )[0]
        sql = """
        SELECT
            name,
            group_name,
            ip,
            check_type,
            port,
            state,
            state_changed,
            total_checks,
            success_checks,
            description
        FROM hosts
        """
        params = ()
        if group_filter:
            sql += """
            WHERE group_name=?
            """
            params = (
                group_filter,
            )
        sql += """
        ORDER BY name
        """
        rows = db.query_all(
            sql,
            params
        )
        html = []
        html.append("""
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="30">
<style>
body {
    font-family: Arial;
}
table {
    border-collapse: collapse;
}
th, td {
    border:1px solid black;
    padding:5px;
}
.up {
    background:#c0ffc0;
}
.down {
    background:#ffc0c0;
}
.unknown {
    background:#ffffc0;
}
</style>
<title>IPMON 2.0</title>
</head>
<body>
<h2>IPMON 2.0</h2>
<table>
<tr>
<th>Name</th>
<th>Group</th>
<th>IP</th>
<th>Type</th>
<th>Port</th>
<th>Status</th>
<th>Availability</th>
<th>Tier</th>
<th>Description</th>
</tr>
""")
        for row in rows:
            av = availability(
                row["total_checks"],
                row["success_checks"]
            )
            tier_name = tier(av)
            if row["state"] == 1:
                css = "up"
            elif row["state"] == 0:
                css = "down"
            else:
                css = "unknown"
            html.append(f"""
<tr class="{css}">
<td>{row['name']}</td>
<td>{row['group_name']}</td>
<td>{row['ip']}</td>
<td>{row['check_type']}</td>
<td>{row['port'] or '-'}</td>
<td>{state_to_text(row['state'])}</td>
<td>{av:.4f}%</td>
<td>{tier_name}</td>
<td>{row['description']}</td>
</tr>
""")
        html.append("""
</table>
<br>
<a href="/events">Events</a>
</body>
</html>
""")
        self.send_html(
            "".join(html)
        )
    def show_events(self):
        rows = db.query_all("""
            SELECT
                e.event_time,
                h.name,
                e.old_state,
                e.new_state
            FROM events e
            JOIN hosts h
                ON h.id=e.host_id
            ORDER BY e.event_time DESC
            LIMIT 200
        """)
        html = []
        html.append("""
<html>
<head>
<meta charset="utf-8">
<title>Events</title>
</head>
<body>
<h2>Events</h2>
<table>
<tr>
<th>Time</th>
<th>Host</th>
<th>Event</th>
</tr>
""")
        from datetime import datetime
        for row in rows:
            ts = datetime.fromtimestamp(
                row["event_time"]
            )
            event = (
                f"{state_to_text(row['old_state'])}"
                f" → "
                f"{state_to_text(row['new_state'])}"
            )
            html.append(f"""
<tr>
<td>{ts}</td>
<td>{row['name']}</td>
<td>{event}</td>
</tr>
""")
        html.append("""
</table>
<br>
<a href="/">Status</a>
</body>
</html>
""")
        self.send_html(
            "".join(html)
        )
    def api_status(self, parsed):
        args = parse_qs(parsed.query)
        group_filter = args.get(
            "group",
            [None]
        )[0]
        sql = """
        SELECT *
        FROM hosts
        """
        params = ()
        if group_filter:
            sql += """
            WHERE group_name=?
            """
            params = (
                group_filter,
            )
        rows = db.query_all(
            sql,
            params
        )
        result = []
        for row in rows:
            av = availability(
                row["total_checks"],
                row["success_checks"]
            )
            result.append({
                "name":
                    row["name"],
                "group":
                    row["group_name"],
                "ip":
                    row["ip"],
                "type":
                    row["check_type"],
                "port":
                    row["port"],
                "state":
                    state_to_text(
                        row["state"]
                    ),
                "availability":
                    av,
                "tier":
                    tier(av),
                "description":
                    row["description"]
            })
        self.send_json(
            result
        )
    def api_events(self):
        rows = db.query_all("""
            SELECT
                e.event_time,
                h.name,
                e.old_state,
                e.new_state
            FROM events e
            JOIN hosts h
                ON h.id=e.host_id
            ORDER BY e.event_time DESC
            LIMIT 100
        """)
        result = []
        for row in rows:
            result.append({
                "time":
                    row["event_time"],
                "host":
                    row["name"],
                "old":
                    state_to_text(
                        row["old_state"]
                    ),
                "new":
                    state_to_text(
                        row["new_state"]
                    )
            })
        self.send_json(
            result
        )
def start_http(port):
    server = HTTPServer(
        ("0.0.0.0", port),
        WebHandler
    )
    print(
        f"HTTP server listening on {port}"
    )
    server.serve_forever()