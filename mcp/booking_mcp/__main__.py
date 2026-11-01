import os

from mcp.server.transport_security import TransportSecuritySettings

from booking_mcp.construct import construct_booking_server

if __name__ == "__main__":
    construct_booking_server().run(
        "streamable-http",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "3200")),
        stateless_http=True,
        json_response=True,
        # public, read-only, no auth: the localhost-only Host and Origin guard would just reject Claude and ChatGPT
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
