"""Server-selected products. Account isolation requires three distinct auth projects."""
from urllib.parse import urlparse
from collections.abc import Mapping

PRODUCTS = {
    "bpo": {"name": "BPO AI Operations Manager", "industry": "BPO"},
    "procurement": {"name": "AI Procurement", "industry": "Manufacturing"},
    "vakil": {"name": "AI Vakil", "industry": "CaseManagement"},
}


def validate_deployment(product, settings):
    if product not in PRODUCTS or settings.get("PRODUCT_ID") != product:
        raise ValueError("Product configuration does not match this app.")
    projects = settings.get("PRODUCT_PROJECTS", {})
    if not isinstance(projects, Mapping):
        raise ValueError("Configure a different authentication project for each product.")
    refs = [projects.get(key, "") for key in PRODUCTS]
    if any(not ref or not isinstance(ref, str) for ref in refs) or len(set(refs)) != 3:
        raise ValueError("Configure a different authentication project for each product.")
    expected = f"https://{projects[product]}.supabase.co"
    if settings.get("SUPABASE_URL", "").rstrip("/") != expected:
        raise ValueError("This app is connected to the wrong authentication project.")
    public = urlparse(settings.get("APP_PUBLIC_URL", ""))
    if public.scheme != "https" or not public.hostname or public.username or public.password or public.query or public.fragment:
        raise ValueError("Configure this app's HTTPS public address.")
    return PRODUCTS[product]
