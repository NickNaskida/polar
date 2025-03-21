import structlog

from polar.logging import Logger
from polar.worker import AsyncSessionMaker, CronTrigger, JobContext, task

from .service import magic_link as magic_link_service

log: Logger = structlog.get_logger()


@task("magic_link.delete_expired", cron_trigger=CronTrigger(hour=0, minute=0))
async def magic_link_delete_expired(ctx: JobContext) -> None:
    async with AsyncSessionMaker(ctx) as session:
        await magic_link_service.delete_expired(session)
