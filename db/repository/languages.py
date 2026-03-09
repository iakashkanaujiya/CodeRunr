from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.language import Language
from schema.language import LanguageCreate


async def create_language(db: AsyncSession, data: LanguageCreate) -> Language:
    """
    Create a new language.

    Args:
        db (AsyncSession): The database session.
        data (LanguageCreate): The language data.

    Returns:
        Language: The created language.
    """
    language = Language(
        name=data.name,
        compile_cmd=data.compile_cmd,
        run_cmd=data.run_cmd,
        source_file=data.source_file,
        is_archived=data.is_archived,
    )
    db.add(language)
    await db.commit()
    await db.refresh(language)
    return language


async def get_language(db: AsyncSession, language_id: int) -> Language | None:
    """
    Get a language by its ID.

    Args:
        db (AsyncSession): The database session.
        language_id (int): The ID of the language to retrieve.

    Returns:
        Language | None: The language if found, None otherwise.
    """
    result = await db.execute(select(Language).where(Language.id == language_id))
    return result.scalar_one_or_none()


async def get_languages(db: AsyncSession) -> list[Language]:
    """
    Get all languages.

    Args:
        db (AsyncSession): The database session.

    Returns:
        list[Language]: A list of languages.
    """
    result = await db.execute(
        select(Language)
        .where(Language.is_archived.is_not(True))
        .order_by(Language.name)
    )
    return list(result.scalars().all())
