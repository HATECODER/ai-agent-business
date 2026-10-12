import logging
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from backend.app.api_auth import AuthServices
from backend.app.authorization import AuthorizationDenied, MerchantRole, TenantAuthority
from backend.app.business_facts import BusinessFactsUnavailable
from backend.app.copilot import (
    CopilotAnswer,
    CopilotQuestion,
    SourceFact,
    UnsupportedQuestion,
)
from backend.app.identity import VerifiedIdentity
from backend.app.main import create_app

TENANT_ID = "10000000-0000-0000-0000-000000000001"


class Verifier:
    def verify(self, _token):
        now = datetime.now(timezone.utc)
        return VerifiedIdentity("https://identity.example/", "subject", now, now)


def resolver(_identity, _tenant):
    return TenantAuthority(
        identity_id="10000000-0000-0000-0000-000000000002",
        membership_id="10000000-0000-0000-0000-000000000003",
        tenant_id=TENANT_ID,
        role=MerchantRole.OWNER,
        permission_version=1,
    )


def test_copilot_endpoint_forwards_only_bounded_authorized_request():
    calls = []

    def answer(authority, message, reference_date):
        calls.append((authority.tenant_id, message, reference_date))
        return CopilotAnswer(
            question_type=CopilotQuestion.TASKS,
            answer="No tasks.",
            sources=[SourceFact(label="Tasks", value="0")],
            reference_date=reference_date,
            language="English",
        )

    client = TestClient(
        create_app(AuthServices(Verifier(), resolver), copilot_reader=answer)
    )
    response = client.post(
        "/api/v1/copilot/query",
        headers={"Authorization": "Bearer token", "X-BizPilot-Tenant": TENANT_ID},
        json={"message": "tasks"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "No tasks."
    assert calls == [(TENANT_ID, "tasks", date(2026, 11, 1))]

    too_long = client.post(
        "/api/v1/copilot/query",
        headers={"Authorization": "Bearer token", "X-BizPilot-Tenant": TENANT_ID},
        json={"message": "x" * 501},
    )
    assert too_long.status_code == 422


def test_copilot_requires_authentication_and_workspace_selector():
    client = TestClient(
        create_app(
            AuthServices(Verifier(), resolver), copilot_reader=lambda *_args: None
        )
    )
    response = client.post("/api/v1/copilot/query", json={"message": "tasks"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}

    response = client.post(
        "/api/v1/copilot/query",
        headers={"Authorization": "Bearer private-token"},
        json={"message": "tasks"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Select a workspace."}


def test_copilot_domain_denial_and_source_failure_are_sanitized(caplog):
    caplog.set_level(logging.WARNING, logger="bizpilot.security")

    def denied(*_args):
        raise AuthorizationDenied("private role and membership details")

    denied_client = TestClient(
        create_app(AuthServices(Verifier(), resolver), copilot_reader=denied)
    )
    response = denied_client.post(
        "/api/v1/copilot/query",
        headers={
            "Authorization": "Bearer private-token",
            "X-BizPilot-Tenant": TENANT_ID,
        },
        json={"message": "financial summary private-prompt"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Permission denied for this question."}

    def unavailable(*_args):
        raise BusinessFactsUnavailable("private database hostname and query")

    unavailable_client = TestClient(
        create_app(AuthServices(Verifier(), resolver), copilot_reader=unavailable)
    )
    response = unavailable_client.post(
        "/api/v1/copilot/query",
        headers={
            "Authorization": "Bearer private-token",
            "X-BizPilot-Tenant": TENANT_ID,
        },
        json={"message": "financial summary private-prompt"},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Source facts unavailable."}
    assert "private-token" not in caplog.text
    assert "private-prompt" not in caplog.text
    assert "private role" not in caplog.text
    assert "private database" not in caplog.text

    def invalid_source(*_args):
        raise ValueError("private parser or source detail")

    invalid_client = TestClient(
        create_app(AuthServices(Verifier(), resolver), copilot_reader=invalid_source)
    )
    response = invalid_client.post(
        "/api/v1/copilot/query",
        headers={
            "Authorization": "Bearer private-token",
            "X-BizPilot-Tenant": TENANT_ID,
        },
        json={"message": "financial summary private-prompt"},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Source facts unavailable."}
    assert "private parser" not in caplog.text


def test_only_declared_unsupported_question_message_is_returned():
    def unsupported(*_args):
        raise UnsupportedQuestion(
            "Ask about restocking, finance, inactive customers, or tasks."
        )

    client = TestClient(
        create_app(AuthServices(Verifier(), resolver), copilot_reader=unsupported)
    )
    response = client.post(
        "/api/v1/copilot/query",
        headers={"Authorization": "Bearer token", "X-BizPilot-Tenant": TENANT_ID},
        json={"message": "write a poem"},
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": "Ask about restocking, finance, inactive customers, or tasks."
    }
