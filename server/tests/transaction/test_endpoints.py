import uuid

import pytest
from httpx import AsyncClient

from polar.models import Account, Pledge, Transaction, UserOrganization
from polar.models.transaction import TransactionType
from tests.fixtures.database import SaveFixture
from tests.transaction.conftest import create_transaction


@pytest.mark.asyncio
class TestSearchTransactions:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.get("/v1/transactions/search")

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_valid(
        self,
        client: AsyncClient,
        account: Account,
        user_organization: UserOrganization,
        readable_user_transactions: list[Transaction],
        all_transactions: list[Transaction],
    ) -> None:
        response = await client.get("/v1/transactions/search")

        assert response.status_code == 200

        json = response.json()
        assert json["pagination"]["total_count"] == len(readable_user_transactions)


@pytest.mark.asyncio
class TestLookupTransaction:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.get(
            "/v1/transactions/lookup", params={"transaction_id": str(uuid.uuid4())}
        )

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_transaction_payout(
        self,
        save_fixture: SaveFixture,
        account: Account,
        user_organization: UserOrganization,
        pledge: Pledge,
        client: AsyncClient,
    ) -> None:
        transaction = await create_transaction(
            save_fixture, type=TransactionType.payout, account=account, pledge=pledge
        )

        paid_transactions = [
            await create_transaction(
                save_fixture, account=account, payout_transaction=transaction
            ),
            await create_transaction(
                save_fixture, account=account, payout_transaction=transaction
            ),
            await create_transaction(
                save_fixture, account=account, payout_transaction=transaction
            ),
        ]

        response = await client.get(
            "/v1/transactions/lookup",
            params={"transaction_id": str(transaction.id)},
        )

        assert response.status_code == 200

        json = response.json()
        assert json["id"] == str(transaction.id)
        assert len(json["paid_transactions"]) == len(paid_transactions)


@pytest.mark.asyncio
class TestGetSummary:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.get(
            "/v1/transactions/summary", params={"account_id": str(uuid.uuid4())}
        )

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_not_existing_account(self, client: AsyncClient) -> None:
        response = await client.get(
            "/v1/transactions/summary", params={"account_id": str(uuid.uuid4())}
        )

        assert response.status_code == 404

    @pytest.mark.auth
    async def test_valid(
        self,
        client: AsyncClient,
        account: Account,
        user_organization: UserOrganization,
        account_transactions: list[Transaction],
    ) -> None:
        response = await client.get(
            "/v1/transactions/summary", params={"account_id": str(account.id)}
        )

        assert response.status_code == 200

        json = response.json()
        assert "balance" in json
        assert "payout" in json
