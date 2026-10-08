from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import delete, func, select, update

from app.config import Settings
from app.database.models import Question, QuizAnswer, QuizAttempt, User
from app.database.session import Database
from app.keyboards.reply import admin_quiz_keyboard
from app.services.settings import get_setting, set_setting
from app.states.admin import AdminSettingStates
from app.utils.auth import can_manage_users, require_admin

router = Router(name="admin_quiz")


@router.message(F.text == "🧠 TEST BOSHQARUVI")
async def home(message: Message, db: Database) -> None:
    if not can_manage_users(await require_admin(message, db)):
        return
    await message.answer("🧠 <b>TEST BOSHQARUVI</b>", reply_markup=admin_quiz_keyboard())


@router.message(F.text == "⚙️ TEST SOZLAMALARI")
async def settings(message: Message, db: Database, settings: Settings) -> None:
    if not can_manage_users(await require_admin(message, db)):
        return
    async with db.session() as session:
        points = await get_setting(session, "points_per_correct", str(settings.points_per_correct))
        daily = await get_setting(session, "daily_question_id", "")
    await message.answer(
        "⚙️ <b>TEST SOZLAMALARI</b>\n\n"
        f"⭐ To‘g‘ri javob: <b>{points}</b> ball\n"
        f"🔥 Bugungi savol ID: <b>{daily or 'belgilanmagan'}</b>\n\n"
        "Ball yoki Daily savol ID sini o‘zgartirish uchun maxsus sozlama oqimi mavjud."
    )


@router.message(F.text == "📊 TEST STATISTIKASI")
async def statistics(message: Message, db: Database) -> None:
    if not can_manage_users(await require_admin(message, db)):
        return
    async with db.session() as session:
        attempts = await session.scalar(select(func.count(QuizAttempt.id))) or 0
        completed = await session.scalar(select(func.count(QuizAttempt.id)).where(QuizAttempt.completed.is_(True))) or 0
        answers = await session.scalar(select(func.count(QuizAnswer.id))) or 0
        questions = await session.scalar(select(func.count(Question.id)).where(Question.is_active.is_(True))) or 0
    await message.answer(
        "📊 <b>TEST STATISTIKASI</b>\n\n"
        f"📚 Faol savollar: <b>{questions}</b>\n"
        f"🧠 Boshlangan testlar: <b>{attempts}</b>\n"
        f"🏁 Tugallangan: <b>{completed}</b>\n"
        f"✅ Javoblar: <b>{answers}</b>"
    )


@router.message(F.text == "🎯 BALLNI O‘ZGARTIRISH")
async def edit_points_start(message: Message, state: FSMContext, db: Database) -> None:
    if not can_manage_users(await require_admin(message, db)):
        return
    await state.set_state(AdminSettingStates.points)
    await message.answer("🎯 <b>BALL</b>\n\nHar bir to‘g‘ri javob uchun nechta ball berilsin?\nMasalan: <code>10</code>")


@router.message(AdminSettingStates.points)
async def edit_points_value(message: Message, state: FSMContext, db: Database) -> None:
    if not can_manage_users(await require_admin(message, db)):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= 1000:
        await message.answer("⚠️ 1–1000 oralig‘ida butun son yuboring.")
        return
    async with db.session() as session:
        await set_setting(session, "points_per_correct", raw)
    await state.clear()
    await message.answer(f"✅ Har bir to‘g‘ri javob endi <b>{raw}</b> ball.", reply_markup=admin_quiz_keyboard())


@router.message(F.text == "🔥 DAILY SAVOL")
async def edit_daily_start(message: Message, state: FSMContext, db: Database) -> None:
    if not can_manage_users(await require_admin(message, db)):
        return
    await state.set_state(AdminSettingStates.daily_question)
    await message.answer("🔥 <b>BUGUNGI SAVOL</b>\n\nSavol ID sini yuboring. O‘chirish uchun <code>0</code> yuboring.")


@router.message(AdminSettingStates.daily_question)
async def edit_daily_value(message: Message, state: FSMContext, db: Database) -> None:
    if not can_manage_users(await require_admin(message, db)):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("⚠️ Savol ID faqat raqam bo‘lishi kerak.")
        return
    value = "" if raw == "0" else raw
    async with db.session() as session:
        if value:
            question = await session.get(Question, int(value))
            if not question or not question.is_active or question.source != "manual":
                await message.answer("⚠️ Faol oddiy savol ID sini yuboring.")
                return
        await set_setting(session, "daily_question_id", value)
    await state.clear()
    await message.answer("✅ Bugungi savol sozlandi." if value else "✅ Bugungi savol o‘chirildi.", reply_markup=admin_quiz_keyboard())


@router.message(F.text == "🧹 NATIJALARNI TOZALASH")
async def clear_results(message: Message, db: Database) -> None:
    if await require_admin(message, db) != "superadmin":
        return
    async with db.session() as session:
        await session.execute(delete(QuizAnswer))
        await session.execute(delete(QuizAttempt))
        await session.execute(
            update(User).values(
                score=0, total_questions=0, correct_answers=0, wrong_answers=0, streak=0, last_quiz_day=None
            )
        )
        await session.commit()
    await message.answer("🧹 <b>TEST NATIJALARI TO‘LIQ TOZALANDI.</b>\n\nBarcha test javoblari, test urinishlari va user test statistikasi 0 ga qaytarildi.")
