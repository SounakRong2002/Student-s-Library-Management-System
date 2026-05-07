import json
from urllib.parse import parse_qs


def handler(request):
    """Minimal health endpoint.

    Vercel serverless function entrypoint. Returns JSON so deployments
    do not crash with FUNCTION_INVOCATION_FAILED.

    This project is a Streamlit UI (app.py). Streamlit is not meant to run
    as a serverless request handler.
    """

    # Basic request introspection (safe, no heavy work)
    method = getattr(request, "method", "GET")
    query = ""
    try:
        query = getattr(request, "query", "")
    except Exception:
        query = ""

    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(
            {
                "ok": True,
                "service": "student-library-management",
                "method": method,
                "query": query,
                "note": "Streamlit UI lives in app.py and must be served separately (streamlit run app.py).",
            }
        ),
    }

