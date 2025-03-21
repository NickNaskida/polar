from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException

from polar.auth.dependencies import AdminUser
from polar.enums import Platforms
from polar.exceptions import ResourceNotFound
from polar.external_organization.service import (
    external_organization as external_organization_service,
)
from polar.integrations.github.service.issue import github_issue
from polar.issue.schemas import Issue
from polar.issue.service import issue as issue_service
from polar.kit.pagination import ListResource, Pagination
from polar.kit.schemas import Schema
from polar.models.issue_reward import IssueReward
from polar.models.pledge import Pledge as PledgeModel
from polar.models.pledge_transaction import PledgeTransaction as PledgeTransactionModel
from polar.openapi import APITag
from polar.pledge.service import pledge as pledge_service
from polar.postgres import AsyncSession, get_db_session
from polar.redis import Redis, get_redis
from polar.repository.service import repository as repository_service
from polar.reward.endpoints import to_resource as reward_to_resource
from polar.reward.service import reward_service
from polar.routing import APIRouter
from polar.worker import enqueue_job

from .pledge_service import bo_pledges_service
from .schemas import (
    BackofficeBadge,
    BackofficeBadgeResponse,
    BackofficePledge,
    BackofficeReward,
)

router = APIRouter(tags=["backoffice", APITag.private], prefix="/backoffice")


@router.get("/pledges", response_model=list[BackofficePledge])
async def pledges(
    auth_subject: AdminUser,
    session: AsyncSession = Depends(get_db_session),
) -> list[BackofficePledge]:
    return await bo_pledges_service.list_pledges(session)


def r(
    pledge: PledgeModel, reward: IssueReward, transaction: PledgeTransactionModel
) -> BackofficeReward:
    r = reward_to_resource(
        pledge,
        reward,
        transaction,
        include_receiver_admin_fields=True,
        include_sender_admin_fields=True,
        include_sender_fields=True,
    )
    return BackofficeReward(
        pledge=r.pledge,
        user=r.user,
        organization=r.organization,
        amount=r.amount,
        state=r.state,
        paid_at=r.paid_at,
        transfer_id=transaction.transaction_id if transaction else None,
        issue_reward_id=reward.id,
        pledge_payment_id=pledge.payment_id,
        pledger_email=pledge.email,
    )


@router.get(
    "/rewards/by_issue",
    response_model=ListResource[BackofficeReward],
)
async def rewards(
    auth_subject: AdminUser,
    issue_id: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ListResource[BackofficeReward]:
    rewards = await reward_service.list(session, issue_id=issue_id)

    return ListResource(
        items=[
            r(pledge, reward, transaction) for pledge, reward, transaction in rewards
        ],
        pagination=Pagination(total_count=len(rewards), max_page=1),
    )


@router.get(
    "/rewards/pending",
    response_model=ListResource[BackofficeReward],
)
async def rewards_pending(
    auth_subject: AdminUser,
    session: AsyncSession = Depends(get_db_session),
) -> ListResource[BackofficeReward]:
    rewards = await reward_service.list(session, is_transfered=False)

    return ListResource(
        items=[
            r(pledge, reward, transaction) for pledge, reward, transaction in rewards
        ],
        pagination=Pagination(total_count=len(rewards), max_page=1),
    )


@router.get("/issue/{id}", response_model=Issue)
async def issue(
    id: UUID,
    auth_subject: AdminUser,
    session: AsyncSession = Depends(get_db_session),
) -> Issue:
    i = await issue_service.get_loaded(session, id)
    if not i:
        raise HTTPException(
            status_code=404,
            detail="Issue not found",
        )

    return Issue.model_validate(i)


async def get_pledge(session: AsyncSession, pledge_id: UUID) -> BackofficePledge:
    pledge = await pledge_service.get_with_loaded(session, pledge_id)
    if not pledge:
        raise HTTPException(
            status_code=404,
            detail="Pledge not found",
        )
    return BackofficePledge.from_db(
        pledge,
    )


class PledgeRewardTransfer(Schema):
    pledge_id: UUID
    issue_reward_id: UUID


@router.post("/pledges/approve", response_model=BackofficeReward)
async def pledge_reward_transfer(
    body: PledgeRewardTransfer,
    auth_subject: AdminUser,
    session: AsyncSession = Depends(get_db_session),
) -> BackofficeReward:
    await pledge_service.transfer(session, body.pledge_id, body.issue_reward_id)

    reward_tuple = await reward_service.get(
        session, pledge_id=body.pledge_id, issue_reward_id=body.issue_reward_id
    )

    if not reward_tuple:
        raise HTTPException(
            status_code=404,
            detail="Reward not found",
        )

    (pledge, reward, transaction) = reward_tuple

    return r(pledge, reward, transaction)


@router.post(
    "/pledges/create_invoice/{pledge_id}",
    response_model=BackofficePledge,
)
async def pledge_create_invoice(
    pledge_id: UUID,
    auth_subject: AdminUser,
    session: AsyncSession = Depends(get_db_session),
) -> BackofficePledge:
    await pledge_service.send_invoice(session, pledge_id)
    return await get_pledge(session, pledge_id)


@router.post(
    "/pledges/mark_disputed/{pledge_id}",
    response_model=BackofficePledge,
)
async def pledge_mark_disputed(
    pledge_id: UUID,
    auth_subject: AdminUser,
    session: AsyncSession = Depends(get_db_session),
) -> BackofficePledge:
    await pledge_service.mark_disputed(
        session,
        pledge_id,
        by_user_id=auth_subject.subject.id,
        reason="Disputed via Backoffice",
    )
    return await get_pledge(session, pledge_id)


@router.post("/badge", response_model=BackofficeBadgeResponse)
async def manage_badge(
    badge: BackofficeBadge,
    auth_subject: AdminUser,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> BackofficeBadgeResponse:
    external_org = await external_organization_service.get_by_name(
        session, Platforms.github, badge.org_slug
    )
    if not external_org:
        raise ResourceNotFound()

    if external_org.organization_id is None:
        raise ResourceNotFound()

    repo = await repository_service.get_by_org_and_name(
        session, external_org.organization_id, badge.repo_slug
    )
    if not repo:
        raise ResourceNotFound()

    issue = await issue_service.get_by_number(
        session,
        Platforms.github,
        external_org.id,
        repo.id,
        badge.issue_number,
    )
    if not issue:
        raise ResourceNotFound()

    if repo.pledge_badge_auto_embed:
        raise HTTPException(403)

    if badge.action == "remove":
        issue = await github_issue.remove_polar_label(
            session,
            redis,
            organization=external_org,
            repository=repo,
            issue=issue,
        )
        success = not issue.has_pledge_badge_label
    else:
        issue = await github_issue.add_polar_label(
            session,
            redis,
            organization=external_org,
            repository=repo,
            issue=issue,
        )
        success = issue.has_pledge_badge_label

    return BackofficeBadgeResponse(
        org_slug=external_org.name,
        repo_slug=repo.name,
        issue_number=issue.number,
        action=badge.action,
        success=success,
    )


@router.post(
    "/update_badge_contents",
    response_model=dict[Any, Any],
)
async def update_badge_contents(
    org_slug: str,
    repo_slug: str,
    auth_subject: AdminUser,
    session: AsyncSession = Depends(get_db_session),
) -> dict[Any, Any]:
    external_org = await external_organization_service.get_by_name(
        session, Platforms.github, org_slug
    )
    if not external_org:
        raise ResourceNotFound()

    if external_org.organization_id is None:
        raise ResourceNotFound()

    repo = await repository_service.get_by_org_and_name(
        session, external_org.organization_id, repo_slug
    )
    if not repo:
        raise ResourceNotFound()

    (issues, _) = await issue_service.list_by_repository_type_and_status(
        session,
        repository_ids=[repo.id],
        have_polar_badge=True,
    )

    queued = []

    for issue in issues:
        if not issue.pledge_badge_currently_embedded:
            continue

        enqueue_job(
            "github.badge.update_on_issue",
            issue_id=issue.id,
        )

        queued.append(issue.id)

    return {
        "status": True,
        "queued": queued,
    }
