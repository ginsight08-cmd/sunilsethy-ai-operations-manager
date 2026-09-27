"""Server-selected products. Account isolation requires three distinct auth projects."""
from urllib.parse import urlparse
from collections.abc import Mapping

PRODUCTS = {
    "bpo": {"name": "IT Operations Manager", "industry": "BPO"},
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
    auth = urlparse(settings.get("NEON_AUTH_URL", ""))
    database = urlparse(settings.get("NEON_DATABASE_URL", ""))
    if (auth.scheme != 'https' or not auth.hostname or not auth.hostname.endswith('.neon.tech')
            or '.neonauth.' not in auth.hostname or not auth.path.endswith('/auth')
            or auth.username or auth.password or auth.query or auth.fragment):
        raise ValueError('Configure the Neon authentication address for this product.')
    if (database.scheme not in ('postgres','postgresql') or not database.hostname
            or not database.hostname.endswith('.neon.tech') or not database.username or not database.password
            or database.hostname.split('.')[0].removesuffix('-pooler') != auth.hostname.split('.')[0]):
        raise ValueError('Authentication and database connections must belong to the same Neon endpoint.')
    public = urlparse(settings.get("APP_PUBLIC_URL", ""))
    if public.scheme != "https" or not public.hostname or public.username or public.password or public.query or public.fragment:
        raise ValueError("Configure this app's HTTPS public address.")
    return PRODUCTS[product]
