export const PRICE = 5_000;
export const DURATION_MIN = 60;

export const PRICE_LABEL = `${PRICE.toLocaleString("ru-RU")} ₽`;
export const SESSION_LABEL = `${PRICE_LABEL} / ${DURATION_MIN} минут`;

export const priceFaqItem = {
  question: "Сколько стоит консультация?",
  answer: `Стоимость консультации — ${PRICE_LABEL} за ${DURATION_MIN} минут. Первая встреча проходит в том же формате — вы рассказываете о своей ситуации, я объясняю, чем могу помочь. Встреча ни к чему не обязывает.`,
};

// Russian messenger, listed first: the practice is aimed at clients in Russia
export const MAX_URL = "https://max.ru/u/f9LHodD0cOLjSTb7GhaDmaB-R57UI5gU6Ay_nZvGKr6fKqEEcqWUjn0GDBs";
