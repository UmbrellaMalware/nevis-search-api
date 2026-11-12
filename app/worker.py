"""Summary worker: `python -m app.worker`.

Polls Postgres for documents with a pending summary and summarises them one at a time.
It does not load the embedding model, so it stays small in memory.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db import create_engine
from app.services.summaries import OpenAISummarizer, Summarizer, summarize_next

logger = logging.getLogger("app.worker")


async def run(
    sessionmaker: async_sessionmaker[AsyncSession], summarizer: Summarizer, poll_interval: float
) -> None:
    """Summarise documents forever; sleep `poll_interval` seconds whenever the queue is empty.

    A database error (e.g. Postgres restarting) is logged and retried after the same pause,
    instead of killing the worker.
    """
    while True:
        try:
            async with sessionmaker() as session:
                processed = await summarize_next(session, summarizer)
        except Exception:
            logger.exception("Summary worker iteration failed")
            processed = False
        if not processed:
            await asyncio.sleep(poll_interval)


async def main() -> None:
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is not set: the summary worker cannot run")

    engine = create_engine(settings.database_url)
    summarizer = OpenAISummarizer(settings.openai_api_key, settings.summary_model)
    logger.info("Summary worker started (model %s)", settings.summary_model)
    try:
        await run(
            async_sessionmaker(engine, expire_on_commit=False),
            summarizer,
            settings.summary_poll_interval_seconds,
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(main())
