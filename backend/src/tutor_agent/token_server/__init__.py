"""HTTP token server — mints short-lived LiveKit access tokens (spec §11).

This is the ONLY place ``LIVEKIT_API_SECRET`` is read; the app never holds it.
"""
