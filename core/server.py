"""
PATCH INSTRUCTIONS — add /latest endpoint to server.py
-------------------------------------------------------
Find the do_GET method in server.py (the /status block).
Add the /latest block shown below BEFORE the final 404 fallback line.
"""

# ── Find this line in do_GET ───────────────────────────────────────────────────

#         self._respond(404, {"error": "Unknown endpoint"})

# ── Add this BEFORE it ────────────────────────────────────────────────────────

        # ── /latest — overlay polls this for new DM responses ─────────────
        if self.path == "/latest":
            mem      = self.memory or {}
            dm_name  = self.config.get("dm", {}).get("name", "")
            last     = mem.get("dm_last_remark")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "response": last,
                "dm_name":  dm_name,
            }).encode())
            return

# ── Also update the startup banner ────────────────────────────────────────────
# Find this block in start_server() and add the /latest line:

#     print(f"    POST /memory/pattern   — log a recurring behavior")
#     print(f"    GET  /status           — health check")

# Change to:

#     print(f"    POST /memory/pattern   — log a recurring behavior")
#     print(f"    GET  /latest           — latest DM response (overlay polls this)")
#     print(f"    GET  /status           — health check")
