import hashlib
import unicodedata

_HASH_TRANSLATION = str.maketrans(
    {
        # невидимые: пробел нулевой ширины, ZWNJ, ZWJ, word joiner, BOM, мягкий перенос
        **dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\xad"), None),
        # тире и дефисы → обычный дефис
        **dict.fromkeys(map(ord, "\u2010\u2012\u2013\u2014\u2015\u2212"), "-"),
        # двойные кавычки → "
        **dict.fromkeys(map(ord, "«»„“”‟"), '"'),
        # одинарные кавычки и апостроф → '
        **dict.fromkeys(map(ord, "‘’‚‛"), "'"),
        "ё": "е",
    }
)


def normalize_for_hash(text: str) -> str:
    """Текст для хеша: без различий в регистре,
    типографике, невидимых символах и вёрстке."""
    text = unicodedata.normalize("NFKC", text)
    text = text.casefold()
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_HASH_TRANSLATION)
    return " ".join(text.split())


def text_hash(text: str) -> str:
    """SHA-256 (hex) нормализованного текста."""
    return hashlib.sha256(normalize_for_hash(text).encode("utf-8")).hexdigest()
