from pathlib import Path

import config
from scripts import write_streamlit_secrets


def test_pilot_rejects_more_than_two_evaluators(monkeypatch):
    monkeypatch.setenv("BIZPILOT_DEPLOYMENT_MODE", "pilot")
    monkeypatch.setenv(
        "BIZPILOT_OWNER_SUBJECTS",
        "https://accounts.google.com|one;https://accounts.google.com|two;https://accounts.google.com|three",
    )
    try:
        config.owner_subject_allowlist()
    except ValueError as error:
        assert "at most two" in str(error)
    else:
        raise AssertionError("pilot must reject a third evaluator")


def test_oidc_secret_file_uses_exact_https_callback(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    values = {
        "BIZPILOT_PUBLIC_URL": "https://pilot.example/",
        "OIDC_CLIENT_ID": "client-value",
        "OIDC_CLIENT_SECRET": "secret-value",
        "OIDC_COOKIE_SECRET": "cookie-value",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    assert write_streamlit_secrets.main() == 0
    rendered = Path(".streamlit/secrets.toml").read_text(encoding="utf-8")
    assert 'redirect_uri = "https://pilot.example/oauth2callback"' in rendered
    output = capsys.readouterr().out
    assert all(value not in output for value in values.values())


def test_render_blueprint_is_restricted_and_persistent():
    rendered = (Path(__file__).resolve().parents[1] / "render.yaml").read_text(encoding="utf-8")
    required = (
        "region: singapore",
        "numInstances: 1",
        "healthCheckPath: /_stcore/health",
        "initialDeployHook: python -m database.seed",
        "mountPath: /var/data",
        "BIZPILOT_DEPLOYMENT_MODE",
        "value: pilot",
        "BIZPILOT_DATA_MODE",
        "value: synthetic",
        "sync: false",
    )
    assert all(value in rendered for value in required)
