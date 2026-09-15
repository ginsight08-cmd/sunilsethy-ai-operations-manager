"""Persistent, idempotent trial analysis admission."""
import hashlib
import json

TRIAL_DAYS = 3
TRIAL_ANALYSES = 5


def analysis_key(content, industry, settings=None):
    digest = hashlib.sha256()
    digest.update(content)
    digest.update(json.dumps([industry, settings or {}], sort_keys=True).encode())
    return digest.hexdigest()


def admit_analysis(db, user_id, content, industry, settings=None):
    response = db.rpc("admit_trial_analysis", {
        "p_user_id": user_id,
        "p_analysis_key": analysis_key(content, industry, settings),
    }).execute()
    data = response.data
    if not isinstance(data, dict) or "allowed" not in data:
        raise RuntimeError("Trial usage could not be verified")
    return data
