import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from polar.auth.scope import Scope
from polar.models import Benefit, Customer, Organization, Subscription, UserOrganization
from polar.models.benefit import BenefitType
from tests.fixtures.auth import AuthSubjectFixture
from tests.fixtures.database import SaveFixture
from tests.fixtures.random_objects import create_benefit, create_benefit_grant


@pytest.mark.asyncio
class TestListBenefits:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.get("/v1/benefits/")

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_user_not_organization_member(
        self, client: AsyncClient, benefits: list[Benefit]
    ) -> None:
        response = await client.get("/v1/benefits/")

        assert response.status_code == 200

        json = response.json()
        assert json["pagination"]["total_count"] == 0

    @pytest.mark.auth(
        AuthSubjectFixture(scopes={Scope.web_default}),
        AuthSubjectFixture(scopes={Scope.benefits_read}),
    )
    async def test_user_valid(
        self,
        client: AsyncClient,
        user_organization: UserOrganization,
        benefits: list[Benefit],
    ) -> None:
        response = await client.get("/v1/benefits/")

        assert response.status_code == 200

        json = response.json()
        assert json["pagination"]["total_count"] == 3

    @pytest.mark.auth(
        AuthSubjectFixture(subject="organization", scopes={Scope.web_default}),
        AuthSubjectFixture(subject="organization", scopes={Scope.benefits_read}),
    )
    async def test_organization(
        self, client: AsyncClient, benefits: list[Benefit]
    ) -> None:
        response = await client.get("/v1/benefits/")

        assert response.status_code == 200

        json = response.json()
        assert json["pagination"]["total_count"] == 3


@pytest.mark.asyncio
class TestGetBenefit:
    async def test_anonymous(
        self, client: AsyncClient, benefit_organization: Benefit
    ) -> None:
        response = await client.get(f"/v1/benefits/{benefit_organization.id}")

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_not_existing(self, client: AsyncClient) -> None:
        response = await client.get(f"/v1/benefits/{uuid.uuid4()}")

        assert response.status_code == 404

    @pytest.mark.auth
    async def test_valid(
        self,
        client: AsyncClient,
        benefit_organization: Benefit,
        user_organization: UserOrganization,
    ) -> None:
        response = await client.get(f"/v1/benefits/{benefit_organization.id}")

        assert response.status_code == 200

        json = response.json()
        assert json["id"] == str(benefit_organization.id)
        assert "properties" in json


@pytest.mark.asyncio
class TestCreateBenefit:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/benefits/",
            json={
                "type": "custom",
                "description": "Benefit",
                "properties": {"note": None},
                "organization_id": str(uuid.uuid4()),
            },
        )

        assert response.status_code == 401

    @pytest.mark.parametrize(
        "payload",
        [
            {
                "properties": {"note": None},
                "description": (
                    "This is just a simple benefit description that should not be allowed because it's too long"
                ),
            },
            {
                "properties": {"note": None},
                "description": "Th",
            },
        ],
    )
    @pytest.mark.auth
    async def test_validation(
        self,
        payload: dict[str, Any],
        client: AsyncClient,
        organization: Organization,
        user_organization: UserOrganization,
    ) -> None:
        response = await client.post(
            "/v1/benefits/",
            json={
                "type": "custom",
                "organization_id": str(organization.id),
                **payload,
            },
        )

        assert response.status_code == 422

    @pytest.mark.auth
    async def test_valid(
        self,
        client: AsyncClient,
        organization: Organization,
        user_organization: UserOrganization,
    ) -> None:
        response = await client.post(
            "/v1/benefits/",
            json={
                "type": "custom",
                "description": "Benefit",
                "properties": {"note": None},
                "organization_id": str(organization.id),
            },
        )

        assert response.status_code == 201

        json = response.json()
        assert "properties" in json


@pytest.mark.asyncio
class TestUpdateBenefit:
    async def test_anonymous(
        self,
        client: AsyncClient,
        benefit_organization: Benefit,
    ) -> None:
        response = await client.patch(
            f"/v1/benefits/{benefit_organization.id}",
            json={
                "type": benefit_organization.type,
                "description": "Updated Name",
            },
        )

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_not_existing(self, client: AsyncClient) -> None:
        response = await client.patch(
            f"/v1/benefits/{uuid.uuid4()}",
            json={"type": "custom", "description": "Updated Name"},
        )

        assert response.status_code == 404

    @pytest.mark.parametrize(
        "payload",
        [
            {
                "description": (
                    "This is just a simple product description that should be allowed"
                )
            },
        ],
    )
    @pytest.mark.auth
    async def test_validation(
        self,
        payload: dict[str, Any],
        client: AsyncClient,
        benefit_organization: Benefit,
        user_organization: UserOrganization,
    ) -> None:
        response = await client.patch(
            f"/v1/benefits/{benefit_organization.id}",
            json={"type": benefit_organization.type, **payload},
        )

        assert response.status_code == 422

    @pytest.mark.auth
    async def test_valid(
        self,
        client: AsyncClient,
        benefit_organization: Benefit,
        user_organization: UserOrganization,
    ) -> None:
        response = await client.patch(
            f"/v1/benefits/{benefit_organization.id}",
            json={
                "type": benefit_organization.type,
                "description": "Updated Description",
            },
        )

        assert response.status_code == 200

        json = response.json()
        assert json["description"] == "Updated Description"
        assert "properties" in json

    @pytest.mark.auth
    async def test_can_update_custom_properties(
        self,
        save_fixture: SaveFixture,
        client: AsyncClient,
        organization: Organization,
        user_organization: UserOrganization,
    ) -> None:
        benefit = await create_benefit(
            save_fixture,
            type=BenefitType.custom,
            organization=organization,
            properties={"note": "NOTE"},
        )

        response = await client.patch(
            f"/v1/benefits/{benefit.id}",
            json={
                "type": benefit.type,
                "description": "Updated Description",
                "properties": {"note": "UPDATED NOTE"},
            },
        )

        assert response.status_code == 200

        json = response.json()
        assert json["description"] == "Updated Description"
        assert "properties" in json
        assert json["properties"]["note"] == "UPDATED NOTE"


@pytest.mark.asyncio
class TestDeleteBenefit:
    async def test_anonymous(
        self,
        client: AsyncClient,
        benefit_organization: Benefit,
    ) -> None:
        response = await client.delete(f"/v1/benefits/{benefit_organization.id}")

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_not_existing(self, client: AsyncClient) -> None:
        response = await client.delete(f"/v1/benefits/{uuid.uuid4()}")

        assert response.status_code == 404

    @pytest.mark.auth
    async def test_valid(
        self,
        client: AsyncClient,
        benefit_organization: Benefit,
        user_organization: UserOrganization,
    ) -> None:
        response = await client.delete(f"/v1/benefits/{benefit_organization.id}")

        assert response.status_code == 204


@pytest.mark.asyncio
class TestViewGrants:
    async def test_anonymous(
        self,
        client: AsyncClient,
        benefit_organization: Benefit,
    ) -> None:
        response = await client.get(
            f"/v1/benefits/{benefit_organization.id}/grants",
        )

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_not_existing(self, client: AsyncClient) -> None:
        response = await client.get(
            f"/v1/benefits/{uuid.uuid4()}/grants",
        )

        assert response.status_code == 404

    @pytest.mark.auth
    async def test_empty_grants(
        self,
        client: AsyncClient,
        benefit_organization: Benefit,
        user_organization: UserOrganization,
    ) -> None:
        response = await client.get(
            f"/v1/benefits/{benefit_organization.id}/grants",
        )

        assert response.status_code == 200

        json = response.json()
        assert json["items"] == []

    @pytest.mark.auth
    async def test_with_granted_grants(
        self,
        client: AsyncClient,
        save_fixture: SaveFixture,
        benefit_organization: Benefit,
        user_organization: UserOrganization,
        customer: Customer,
        subscription: Subscription,
    ) -> None:
        grant = await create_benefit_grant(
            save_fixture,
            customer,
            benefit_organization,
            granted=True,
            subscription=subscription,
        )

        response = await client.get(
            f"/v1/benefits/{benefit_organization.id}/grants",
        )

        assert response.status_code == 200

        json = response.json()
        assert len(json["items"]) == 1

        granted_item = json["items"][0]
        assert granted_item["id"] == str(grant.id)
        assert granted_item["is_granted"] is True
        assert granted_item["granted_at"] is not None
        assert granted_item["is_revoked"] is False
        assert granted_item["revoked_at"] is None
        assert granted_item["customer_id"] == str(customer.id)
        assert granted_item["benefit_id"] == str(benefit_organization.id)
        assert granted_item["subscription_id"] == str(subscription.id)
        assert granted_item["error"] is None

    @pytest.mark.auth
    async def test_with_revoked_grants(
        self,
        client: AsyncClient,
        save_fixture: SaveFixture,
        benefit_organization: Benefit,
        user_organization: UserOrganization,
        customer: Customer,
        subscription: Subscription,
    ) -> None:
        revoked_grant = await create_benefit_grant(
            save_fixture,
            customer,
            benefit_organization,
            granted=False,
            subscription=subscription,
        )

        response = await client.get(
            f"/v1/benefits/{benefit_organization.id}/grants",
        )

        assert response.status_code == 200

        json = response.json()
        assert len(json["items"]) == 1

        revoked_item = json["items"][0]
        assert revoked_item["id"] == str(revoked_grant.id)
        assert revoked_item["is_granted"] is False
        assert revoked_item["granted_at"] is None
        assert revoked_item["is_revoked"] is True
        assert revoked_item["revoked_at"] is not None
        assert revoked_item["customer_id"] == str(customer.id)
        assert revoked_item["benefit_id"] == str(benefit_organization.id)
        assert revoked_item["subscription_id"] == str(subscription.id)
        assert revoked_item["error"] is None

    @pytest.mark.auth
    async def test_with_errored_grants(
        self,
        client: AsyncClient,
        save_fixture: SaveFixture,
        benefit_organization: Benefit,
        user_organization: UserOrganization,
        customer: Customer,
        subscription: Subscription,
    ) -> None:
        error_grant = await create_benefit_grant(
            save_fixture,
            customer,
            benefit_organization,
            subscription=subscription,
        )
        error_message = "Test error message"
        error_grant.set_grant_failed(Exception(error_message))
        await save_fixture(error_grant)

        response = await client.get(
            f"/v1/benefits/{benefit_organization.id}/grants",
        )

        assert response.status_code == 200

        json = response.json()
        assert len(json["items"]) == 1

        error_item = json["items"][0]
        assert error_item["id"] == str(error_grant.id)
        assert error_item["is_granted"] is False
        assert error_item["granted_at"] is None
        assert error_item["is_revoked"] is False
        assert error_item["error"] is not None
        assert error_item["error"]["message"] == error_message
        assert error_item["error"]["type"] == "Exception"
        assert "timestamp" in error_item["error"]
