from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Book, Question


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().strip().split())[:1000]


async def search_books(session: AsyncSession, query: str, limit: int = 20) -> list[Book]:
    q = f"%{query.strip()}%"
    result = await session.execute(
        select(Book)
        .where(Book.is_active.is_(True), or_(Book.title.ilike(q), Book.author.ilike(q)))
        .order_by(Book.title, Book.id)
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_books(session: AsyncSession, offset: int = 0, limit: int = 20) -> list[Book]:
    result = await session.execute(
        select(Book).where(Book.is_active.is_(True)).order_by(Book.title, Book.id).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def list_books_with_counts(session: AsyncSession, offset: int = 0, limit: int = 20) -> list[tuple[Book, int]]:
    result = await session.execute(
        select(Book, func.count(Question.id))
        .outerjoin(Question, (Question.book_id == Book.id) & (Question.is_active.is_(True)) & (Question.source == "manual"))
        .where(Book.is_active.is_(True))
        .group_by(Book.id)
        .order_by(Book.title, Book.id)
        .offset(offset)
        .limit(limit)
    )
    return [(book, int(count)) for book, count in result.all()]


async def search_books_with_counts(session: AsyncSession, query: str, limit: int = 20) -> list[tuple[Book, int]]:
    q = f"%{query.strip()}%"
    result = await session.execute(
        select(Book, func.count(Question.id))
        .outerjoin(Question, (Question.book_id == Book.id) & (Question.is_active.is_(True)) & (Question.source == "manual"))
        .where(Book.is_active.is_(True), or_(Book.title.ilike(q), Book.author.ilike(q)))
        .group_by(Book.id)
        .order_by(Book.title, Book.id)
        .limit(limit)
    )
    return [(book, int(count)) for book, count in result.all()]


async def list_all_active_books(session: AsyncSession, limit: int = 100) -> list[Book]:
    result = await session.execute(select(Book).where(Book.is_active.is_(True)).order_by(Book.title).limit(limit))
    return list(result.scalars().all())


async def get_book(session: AsyncSession, book_id: int) -> Book | None:
    return await session.scalar(select(Book).where(Book.id == book_id, Book.is_active.is_(True)))


async def book_question_count(session: AsyncSession, book_id: int) -> int:
    result = await session.execute(
        select(func.count(Question.id))
        .join(Book, Book.id == Question.book_id)
        .where(Question.book_id == book_id, Question.is_active.is_(True), Question.source == "manual", Book.is_active.is_(True))
    )
    return int(result.scalar_one())


async def delete_book(session: AsyncSession, book_id: int) -> None:
    # Soft-delete so historical QuizAnswer/QuizAttempt rows and user statistics remain consistent.
    book = await session.get(Book, book_id)
    if not book:
        return
    book.is_active = False
    await session.execute(
        Question.__table__.update()
        .where(Question.book_id == book_id)
        .values(is_active=False)
    )
    await session.commit()
