from __future__ import annotations

from aiogram.types import User as TgUser
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


async def get_or_create_user(session: AsyncSession, tg_user: TgUser) -> User:
    result = await session.execute(select(User).where(User.telegram_id == tg_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "",
            last_name=tg_user.last_name,
        )
        session.add(user)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            user = await session.scalar(select(User).where(User.telegram_id == tg_user.id))
            if user is None:
                raise
            return user
        await session.refresh(user)
        return user

    changed = False
    new_values = {
        "username": tg_user.username,
        "first_name": tg_user.first_name or "",
        "last_name": tg_user.last_name,
    }
    for key, value in new_values.items():
        if getattr(user, key) != value:
            setattr(user, key, value)
            changed = True
    if changed:
        await session.commit()
    return user


async def reset_user_statistics(session: AsyncSession, user_id: int) -> None:
    from sqlalchemy import delete, update
    from app.database.models import QuizAnswer, QuizAttempt
    attempt_ids = select(QuizAttempt.id).where(QuizAttempt.user_id == user_id)
    await session.execute(delete(QuizAnswer).where(QuizAnswer.attempt_id.in_(attempt_ids)))
    await session.execute(delete(QuizAttempt).where(QuizAttempt.user_id == user_id))
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(score=0, total_questions=0, correct_answers=0, wrong_answers=0, streak=0, last_quiz_day=None)
    )
    await session.commit()


async def search_users(session: AsyncSession, query: str, limit: int = 10) -> list[User]:
    q = query.strip()
    if not q:
        return []
    if q.startswith("@"):
        q = q[1:]
    conditions = [User.username.ilike(f"%{q}%")]
    if q.isdigit():
        conditions.insert(0, User.telegram_id == int(q))
    result = await session.execute(select(User).where(or_(*conditions)).order_by(User.id.desc()).limit(limit))
    return list(result.scalars().all())
