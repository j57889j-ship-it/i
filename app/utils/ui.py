from __future__ import annotations

from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from app.database.session import Database
from app.keyboards.inline import subscription_keyboard
from app.keyboards.reply import main_keyboard
from app.services.admins import is_admin
from app.services.subscriptions import active_channels, is_subscribed_to_all


def h(value: object) -> str:
    return escape(str(value), quote=False)


def divider(char: str = "━", width: int = 24) -> str:
    return char * width


def progress_bar(current: int, total: int, width: int = 10) -> str:
    if total <= 0:
        return "⬜" * width
    filled = round(width * max(0.0, min(1.0, current / total)))
    return "🟦" * filled + "⬜" * (width - filled)


def menu_text() -> str:
    return (
        "✨ <b>SAHIFA QUIZ</b> ✨\n"
        "<i>Kitob o‘qish, bilimni sinash va natijani kuzatish uchun premium quiz maydoni.</i>\n\n"
        f"<code>{divider()}</code>\n"
        "📚 <b>Toping</b> — kitob va mualliflarni qidiring\n"
        "🧠 <b>Sinang</b> — oddiy yoki 🤖 AI quiz yarating\n"
        "🏆 <b>Raqobatlashing</b> — TOP’da o‘rningizni biling\n"
        "👤 <b>Kuzating</b> — shaxsiy statistikangizni ko‘ring\n"
        f"<code>{divider()}</code>\n\n"
        "🌟 <b>Har bir savol — yangi sahifa.</b>"
    )


def section_text(icon: str, title: str, subtitle: str = "") -> str:
    body = f"{icon} <b>{h(title)}</b>\n<code>{divider()}</code>"
    if subtitle:
        body += f"\n\n<i>{h(subtitle)}</i>"
    return body


def book_text(title: str, author: str, description: str, question_count: int) -> str:
    desc = description.strip() or "Bu kitob uchun qisqa ma’lumot hali kiritilmagan."
    return (
        "📖 <b>SAHIFA | KITOB KARTASI</b> ✨\n"
        f"<code>{divider()}</code>\n\n"
        f"📚 <u><b>{h(title)}</b></u>\n"
        f"✍️ <i>{h(author or 'Noma’lum muallif')}</i>\n\n"
        f"<blockquote>💬 {h(desc[:900])}</blockquote>\n\n"
        f"🧠 <b>{question_count}</b> ta faol savol\n"
        "🤖 <i>AI TEST tugmasi orqali shu kitob asosida yangi quiz yaratiladi.</i>"
    )


def quiz_intro(title: str, available: int) -> str:
    return (
        "🧠 <b>TEST UCHUN TAYYORLANING</b> ✨\n"
        f"<code>{divider()}</code>\n\n"
        f"📖 <u><b>{h(title)}</b></u>\n"
        f"📚 Mavjud savollar: <b>{available}</b> ta\n\n"
        "⭐ Har bir to‘g‘ri javob ball beradi.\n"
        "⚡ Javobni tanlang — keyingi savol darhol ochiladi."
    )


def ai_quiz_intro(title: str, author: str, description_length: int) -> str:
    quality = "🟢 Yetarli tavsif" if description_length >= 250 else "🟡 Tavsif qisqa — AI savollarni ehtiyotkorlik bilan tuzadi"
    return (
        "🤖 <b>AI-GENERATED QUIZ</b> ✨\n"
        f"<code>{divider()}</code>\n\n"
        f"📖 <b>{h(title)}</b>\n"
        f"✍️ {h(author or 'Noma’lum muallif')}\n"
        f"📝 {quality}\n\n"
        "AI mavjud kitob ma’lumotlari asosida yangi savollarni yaratadi.\n"
        "⚠️ Savollar viktorina uchun generatsiya qilinadi va alohida saqlanadi."
    )


def question_text(title: str, question, index: int, total: int) -> str:
    return (
        f"📚 <b>{h(title)}</b> ✨\n"
        f"<code>{divider()}</code>\n"
        f"🧠 <b>SAVOL {index + 1} / {total}</b>  <i>{round(((index + 1) / total) * 100) if total else 0}%</i>\n"
        f"{progress_bar(index + 1, total)}\n\n"
        f"❓ <blockquote><b>{h(question.text)}</b></blockquote>\n\n"
        f"🅰️ <i>{h(question.option_a)}</i>\n"
        f"🅱️ <i>{h(question.option_b)}</i>\n"
        f"🅲️ <i>{h(question.option_c)}</i>\n"
        f"🅳️ <i>{h(question.option_d)}</i>\n\n"
        "👇 <i>Javobni tanlang.</i>"
    )


def answer_feedback_text(question, selected: str, correct: bool, points: int, streak: int) -> str:
    options = {"A": question.option_a, "B": question.option_b, "C": question.option_c, "D": question.option_d}
    symbols = {"A": "🅰️", "B": "🅱️", "C": "🅲️", "D": "🅳️"}
    chosen = options.get(selected, "")
    correct_option = question.correct_option.upper()
    correct_text = options.get(correct_option, "")
    explanation = getattr(question, "explanation", "") or ""
    explanation_block = f"\n💡 <i>{h(explanation[:600])}</i>\n" if explanation else ""
    if correct:
        return (
            "🎉 <b>AJOYIB!</b>\n"
            f"<code>{divider()}</code>\n\n"
            f"✅ <b>To‘g‘ri javob:</b> {symbols.get(selected, selected)} {h(chosen)}\n"
            f"⭐ <b>+{points} ball</b>\n"
            f"🔥 <b>Streak: {streak} kun</b>\n"
            f"{explanation_block}\n"
            "✨ <i>Keyingi savol tayyorlanmoqda…</i>"
        )
    return (
        "📚 <b>DAVOM ETAMIZ</b>\n"
        f"<code>{divider()}</code>\n\n"
        f"❌ Siz: {symbols.get(selected, selected)} {h(chosen)}\n"
        f"✅ To‘g‘ri: {symbols.get(correct_option, correct_option)} {h(correct_text)}\n"
        f"🔥 <b>Streak: {streak} kun</b>\n"
        f"{explanation_block}\n"
        "➡️ <i>Keyingi savol ochilmoqda…</i>"
    )


def result_text(correct: int, total: int, score: int) -> str:
    accuracy = round(correct / total * 100) if total else 0
    if accuracy >= 90:
        badge, comment = "👑 <b>MUKAMMAL!</b>", "Siz asarni juda yaxshi bilasiz."
    elif accuracy >= 70:
        badge, comment = "🔥 <b>JUDA YAXSHI!</b>", "Bilimingiz mustahkam."
    elif accuracy >= 50:
        badge, comment = "📖 <b>YAXSHI BOSHLANISH!</b>", "Yana bir test bilan natijani oshiring."
    else:
        badge, comment = "🌱 <b>YANA URINIB KO‘RING!</b>", "Xato savollarni qayta ishlab ko‘ring."
    return (
        "🏆 <b>TEST YAKUNLANDI</b> ✨\n"
        f"<code>{divider()}</code>\n\n"
        f"{badge}\n\n"
        f"✅ To‘g‘ri: <b>{correct}</b>\n"
        f"❌ Xato: <b>{max(total - correct, 0)}</b>\n"
        f"🎯 Aniqlik: <b>{accuracy}%</b>\n"
        f"⭐ Ball: <b>{score}</b>\n\n"
        f"💬 <i>{comment}</i>\n\n"
        "📚 <b>Har bir test — yangi sahifa.</b>"
    )


def catalog_text(items: list[tuple[object, int]], page: int) -> str:
    styles = (
        ("📖", "classic"),
        ("✨", "premium"),
        ("🌿", "soft"),
    )
    icon, style = styles[page % len(styles)]
    lines = [
        f"{icon} <b>KITOBLAR KATALOGI</b>",
        f"<code>{divider()}</code>",
        f"<i>{'Tanlangan asarlar • tartibli katalog' if style == 'classic' else 'Bugungi kutubxona • yangi kashfiyotlar' if style == 'premium' else 'Sokin o‘qish • mazmunli tanlov'}</i>",
        "",
    ]
    for idx, (book, count) in enumerate(items, start=1):
        title = h(book.title[:70])
        author = h(book.author or "Noma’lum muallif")
        if style == "classic":
            lines.extend([f"<b>{idx:02d}. {title}</b>", f"   ✍️ {author}  •  🧠 {count} savol", ""])
        elif style == "premium":
            lines.extend([f"✨ <b>{title}</b>", f"   └ ✍️ {author}  |  🧠 {count} savol", ""])
        else:
            lines.extend([f"🌿 <b>{title}</b>", f"   {author} · {count} savol · 🤖 AI quiz", ""])
    return "\n".join(lines).strip()


def search_catalog_text(items: list[tuple[object, int]]) -> str:
    lines = ["🔎 <b>QIDIRUV NATIJALARI</b>", f"<code>{divider()}</code>", f"✨ <b>{len(items)}</b> ta mos kitob topildi", ""]
    for i, (book, count) in enumerate(items, start=1):
        lines.append(f"<b>{i:02d}.</b> 📖 {h(book.title)}\n   ✍️ {h(book.author or 'Noma’lum')} · 🧠 {count} savol\n")
    return "\n".join(lines).strip()


async def safe_edit_text(message: Message, *, text: str, reply_markup=None) -> bool:
    try:
        await message.edit_text(text=text, reply_markup=reply_markup)
        return True
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            try:
                await message.edit_reply_markup(reply_markup=reply_markup)
                return True
            except Exception:
                return False
        return False
    except Exception:
        return False


async def require_subscription(message: Message, bot: Bot, db: Database) -> bool:
    async with db.session() as session:
        if await is_admin(session, message.from_user.id):
            return True
        ok = await is_subscribed_to_all(session, bot, message.from_user.id)
        channels = await active_channels(session)
    if ok:
        return True
    await message.answer(
        "📢 <b>OBUNA TALAB QILINADI</b>\n\nSahifa Quiz’dan foydalanish uchun quyidagi kanallarga obuna bo‘ling.",
        reply_markup=subscription_keyboard(channels),
    )
    return False


async def require_callback_subscription(callback, bot: Bot, db: Database) -> bool:
    async with db.session() as session:
        if await is_admin(session, callback.from_user.id):
            return True
        ok = await is_subscribed_to_all(session, bot, callback.from_user.id)
        channels = await active_channels(session)
    if ok:
        return True
    if callback.message:
        await callback.message.answer(
            "⚠️ <b>OBUNA TALAB QILINADI</b>\n\nAvval barcha majburiy kanallarga obuna bo‘ling.",
            reply_markup=subscription_keyboard(channels),
        )
    return False


async def send_main_menu(message: Message, db: Database) -> None:
    async with db.session() as session:
        admin = await is_admin(session, message.from_user.id)
    await message.answer(menu_text(), reply_markup=main_keyboard(admin))
