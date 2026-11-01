from pydantic import BaseModel

SITE = "https://psyholog-irina.ru"
SESSION_MINUTES = 60
PRICE_RUB = 5000


class Topic(BaseModel):
    topic: str
    page: str | None


class PsychologistProfile(BaseModel):
    name: str
    specialty: str
    approach: str
    format: str
    language: str
    session_minutes: int
    price_rub: int
    first_meeting: str
    works_with: list[Topic]
    does_not_work_with: list[str]
    education: list[str]
    contacts: dict[str, str]
    site: str
    booking_page: str
    emergency: str


# Mirrors public/llms.txt; keep the two in step when the practice changes.
PROFILE = PsychologistProfile(
    name="Ирина Дербичева",
    specialty="Клинический психолог, экзистенциальный психолог и логотерапевт",
    approach="Экзистенциальная терапия и логотерапия; ACT (терапия принятия и ответственности) как вспомогательный метод",
    format="Только онлайн по видеосвязи, только взрослые, только индивидуально",
    language="русский",
    session_minutes=SESSION_MINUTES,
    price_rub=PRICE_RUB,
    first_meeting="Первая встреча — знакомство в том же формате, ни к чему не обязывает",
    works_with=[
        Topic(topic="Тревога, панические атаки, постоянное напряжение", page=f"{SITE}/trevoga/"),
        Topic(topic="Расстройства пищевого поведения: переедание, ограничения, отношения с телом", page=f"{SITE}/rpp/"),
        Topic(topic="Отношения, расставание, созависимость, развод", page=f"{SITE}/otnosheniya/"),
        Topic(topic="Эмиграция, адаптация в новой стране", page=f"{SITE}/emigratsiya/"),
        Topic(topic="Эмоциональное выгорание", page=f"{SITE}/vygoranie/"),
        Topic(topic="Низкая самооценка, неуверенность, внутренний критик", page=f"{SITE}/samootsenka/"),
        Topic(topic="Поиск смысла, экзистенциальный кризис, переживание утраты", page=None),
    ],
    does_not_work_with=[
        "Дети и подростки",
        "Парная и семейная терапия",
        "Назначение лекарств и постановка диагноза — это работа врача-психиатра",
        "Острое кризисное состояние, требующее экстренной помощи",
        "Очный приём",
    ],
    education=[
        "Московский институт психоанализа — клиническая психология, 1590 часов",
        "Институт терапии и гуманитарных исследований — 650 часов",
        "МГУ — терапия принятия и ответственности (ACT), 178 часов",
        "НАДПО — расстройства пищевого поведения, 230 часов",
    ],
    contacts={
        "max": "https://max.ru/u/f9LHodD0cOLjSTb7GhaDmaB-R57UI5gU6Ay_nZvGKr6fKqEEcqWUjn0GDBs",
        "telegram": "https://t.me/derbichevairina",
        "whatsapp": "https://wa.me/+79028983895",
    },
    site=SITE,
    booking_page=f"{SITE}/zapis/",
    emergency="При угрозе жизни — сразу звоните 112 или в местную экстренную службу; психолог онлайн не заменяет экстренную помощь",
)
