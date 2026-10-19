# coding=utf-8
"""Month name helpers for monthly show parsing and search templates.

Languages follow Medusa indexer valid_languages, plus Romanian (ro):
  da, fi, nl, de, it, es, fr, pl, hu, el, tr, ru, he, ja, pt, zh, cs, sl, hr,
  ko, en, sv, no, ro

Used by:
- guessit month/year release parsing
- episode naming / search template tokens %MM and %Mm

Scene-oriented Latin spellings prefer unaccented forms when scene packs
typically drop diacritics. Index 0 is unused; months are 1..12.
"""
from __future__ import unicode_literals

import unicodedata
from datetime import date

# Alias non-ISO codes used elsewhere in Medusa (e.g. guessit allowed_languages).
_LANG_ALIASES = {
    'jp': 'ja',
    'nb': 'no',
    'nn': 'no',
    'iw': 'he',
    'cn': 'zh',
}

MONTH_NAMES_FULL = {
    'en': (
        None,
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December',
    ),
    'fr': (
        None,
        'Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin',
        'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre',
    ),
    'es': (
        None,
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
    ),
    'de': (
        None,
        'Januar', 'Februar', 'Marz', 'April', 'Mai', 'Juni',
        'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
    ),
    'it': (
        None,
        'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre',
    ),
    'pt': (
        None,
        'Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
    ),
    'nl': (
        None,
        'Januari', 'Februari', 'Maart', 'April', 'Mei', 'Juni',
        'Juli', 'Augustus', 'September', 'Oktober', 'November', 'December',
    ),
    'da': (
        None,
        'Januar', 'Februar', 'Marts', 'April', 'Maj', 'Juni',
        'Juli', 'August', 'September', 'Oktober', 'November', 'December',
    ),
    'sv': (
        None,
        'Januari', 'Februari', 'Mars', 'April', 'Maj', 'Juni',
        'Juli', 'Augusti', 'September', 'Oktober', 'November', 'December',
    ),
    'no': (
        None,
        'Januar', 'Februar', 'Mars', 'April', 'Mai', 'Juni',
        'Juli', 'August', 'September', 'Oktober', 'November', 'Desember',
    ),
    'fi': (
        None,
        'Tammikuu', 'Helmikuu', 'Maaliskuu', 'Huhtikuu', 'Toukokuu', 'Kesakuu',
        'Heinakuu', 'Elokuu', 'Syyskuu', 'Lokakuu', 'Marraskuu', 'Joulukuu',
    ),
    'pl': (
        None,
        'Styczen', 'Luty', 'Marzec', 'Kwiecien', 'Maj', 'Czerwiec',
        'Lipiec', 'Sierpien', 'Wrzesien', 'Pazdziernik', 'Listopad', 'Grudzien',
    ),
    'cs': (
        None,
        'Leden', 'Unor', 'Brezen', 'Duben', 'Kveten', 'Cerven',
        'Cervenec', 'Srpen', 'Zari', 'Rijen', 'Listopad', 'Prosinec',
    ),
    'sl': (
        None,
        'Januar', 'Februar', 'Marec', 'April', 'Maj', 'Junij',
        'Julij', 'Avgust', 'September', 'Oktober', 'November', 'December',
    ),
    'hr': (
        None,
        'Sijecanj', 'Veljaca', 'Ozujak', 'Travanj', 'Svibanj', 'Lipanj',
        'Srpanj', 'Kolovoz', 'Rujan', 'Listopad', 'Studeni', 'Prosinac',
    ),
    'hu': (
        None,
        'Januar', 'Februar', 'Marcius', 'Aprilis', 'Majus', 'Junius',
        'Julius', 'Augusztus', 'Szeptember', 'Oktober', 'November', 'December',
    ),
    'ro': (
        None,
        'Ianuarie', 'Februarie', 'Martie', 'Aprilie', 'Mai', 'Iunie',
        'Iulie', 'August', 'Septembrie', 'Octombrie', 'Noiembrie', 'Decembrie',
    ),
    'tr': (
        None,
        'Ocak', 'Subat', 'Mart', 'Nisan', 'Mayis', 'Haziran',
        'Temmuz', 'Agustos', 'Eylul', 'Ekim', 'Kasim', 'Aralik',
    ),
    'el': (
        None,
        'Ianouarios', 'Fevrouarios', 'Martios', 'Aprilios', 'Maios', 'Iounios',
        'Ioulios', 'Avgoustos', 'Septemvrios', 'Oktovrios', 'Noemvrios', 'Dekemvrios',
    ),
    'ru': (
        None,
        'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
        'Iyul', 'Avgust', 'Sentyabr', 'Oktyabr', 'Noyabr', 'Dekabr',
    ),
    'he': (
        None,
        'Yanuar', 'Fbruar', 'Martz', 'April', 'Mai', 'Yuni',
        'Yuli', 'August', 'September', 'Oktober', 'November', 'Dezember',
    ),
    'ja': (
        None,
        '1月', '2月', '3月', '4月', '5月', '6月',
        '7月', '8月', '9月', '10月', '11月', '12月',
    ),
    'zh': (
        None,
        '一月', '二月', '三月', '四月', '五月', '六月',
        '七月', '八月', '九月', '十月', '十一月', '十二月',
    ),
    'ko': (
        None,
        '1월', '2월', '3월', '4월', '5월', '6월',
        '7월', '8월', '9월', '10월', '11월', '12월',
    ),
}

MONTH_NAMES_ABBR = {
    'en': (
        None,
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ),
    'fr': (
        None,
        'Janv', 'Fevr', 'Mars', 'Avr', 'Mai', 'Juin',
        'Juil', 'Aout', 'Sept', 'Oct', 'Nov', 'Dec',
    ),
    'es': (
        None,
        'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
        'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
    ),
    'de': (
        None,
        'Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
        'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez',
    ),
    'it': (
        None,
        'Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu',
        'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic',
    ),
    'pt': (
        None,
        'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
    ),
    'nl': (
        None,
        'Jan', 'Feb', 'Mrt', 'Apr', 'Mei', 'Jun',
        'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec',
    ),
    'da': (
        None,
        'Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
        'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec',
    ),
    'sv': (
        None,
        'Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
        'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec',
    ),
    'no': (
        None,
        'Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
        'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des',
    ),
    'fi': (
        None,
        'Tammi', 'Helmi', 'Maalis', 'Huhti', 'Touko', 'Kesa',
        'Heina', 'Elo', 'Syys', 'Loka', 'Marras', 'Joulu',
    ),
    'pl': (
        None,
        'Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze',
        'Lip', 'Sie', 'Wrz', 'Paz', 'Lis', 'Gru',
    ),
    'cs': (
        None,
        'Led', 'Uno', 'Bre', 'Dub', 'Kve', 'Cer',
        'Cvc', 'Srp', 'Zar', 'Rij', 'Lis', 'Pro',
    ),
    'sl': (
        None,
        'Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
        'Jul', 'Avg', 'Sep', 'Okt', 'Nov', 'Dec',
    ),
    'hr': (
        None,
        'Sij', 'Velj', 'Ozu', 'Tra', 'Svi', 'Lip',
        'Srp', 'Kol', 'Ruj', 'Lis', 'Stu', 'Pro',
    ),
    'hu': (
        None,
        'Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
        'Jul', 'Aug', 'Sze', 'Okt', 'Nov', 'Dec',
    ),
    'ro': (
        None,
        'Ian', 'Feb', 'Mar', 'Apr', 'Mai', 'Iun',
        'Iul', 'Aug', 'Sep', 'Oct', 'Noi', 'Dec',
    ),
    'tr': (
        None,
        'Oca', 'Sub', 'Mar', 'Nis', 'May', 'Haz',
        'Tem', 'Agu', 'Eyl', 'Eki', 'Kas', 'Ara',
    ),
    'el': (
        None,
        'Ian', 'Fev', 'Mar', 'Apr', 'Mai', 'Ioun',
        'Ioul', 'Avg', 'Sep', 'Okt', 'Noe', 'Dek',
    ),
    'ru': (
        None,
        'Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn',
        'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek',
    ),
    'he': (
        None,
        'Yan', 'Fbr', 'Mar', 'Apr', 'Mai', 'Yun',
        'Yul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez',
    ),
    'ja': MONTH_NAMES_FULL['ja'],
    'zh': (
        None,
        '1月', '2月', '3月', '4月', '5月', '6月',
        '7月', '8月', '9月', '10月', '11月', '12月',
    ),
    'ko': MONTH_NAMES_FULL['ko'],
}

# Reverse map for parsing release names (accented + unaccented + common forms).
MONTH_NAME_TO_NUMBER = {
    # English
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12,
    # French
    'janvier': 1, 'janv': 1,
    'fevrier': 2, 'février': 2, 'fevr': 2, 'févr': 2,
    'mars': 3,
    'avril': 4, 'avr': 4,
    'mai': 5,
    'juin': 6,
    'juillet': 7, 'juil': 7,
    'aout': 8, 'août': 8,
    'septembre': 9,
    'octobre': 10,
    'novembre': 11,
    'decembre': 12, 'décembre': 12, 'déc': 12,
    # Spanish
    'enero': 1, 'ene': 1,
    'febrero': 2,
    'marzo': 3,
    'abril': 4, 'abr': 4,
    'mayo': 5,
    'junio': 6,
    'julio': 7,
    'agosto': 8, 'ago': 8,
    'septiembre': 9,
    'octubre': 10,
    'noviembre': 11,
    'diciembre': 12, 'dic': 12,
    # German
    'januar': 1,
    'februar': 2,
    'märz': 3, 'marz': 3, 'mär': 3,
    'juni': 6,
    'juli': 7,
    'oktober': 10, 'okt': 10,
    'dezember': 12, 'dez': 12,
    # Italian
    'gennaio': 1, 'gen': 1,
    'febbraio': 2,
    'aprile': 4,
    'maggio': 5, 'mag': 5,
    'giugno': 6, 'giu': 6,
    'luglio': 7, 'lug': 7,
    'settembre': 9, 'set': 9,
    'ottobre': 10, 'ott': 10,
    'dicembre': 12,
    # Portuguese
    'janeiro': 1,
    'fevereiro': 2, 'fev': 2,
    'marco': 3, 'março': 3,
    'maio': 5,
    'junho': 6,
    'julho': 7,
    'setembro': 9,
    'outubro': 10, 'out': 10,
    'novembro': 11,
    'dezembro': 12,
    # Dutch
    'januari': 1,
    'februari': 2,
    'maart': 3, 'mrt': 3,
    'mei': 5,
    'augustus': 8,
    # Danish / Norwegian / Swedish (shared + specific)
    'marts': 3,  # da
    'maj': 5,  # da/sv
    'augusti': 8,  # sv
    'desember': 12,  # no
    'des': 12,
    # Finnish
    'tammikuu': 1, 'tammi': 1,
    'helmikuu': 2, 'helmi': 2,
    'maaliskuu': 3, 'maalis': 3,
    'huhtikuu': 4, 'huhti': 4,
    'toukokuu': 5, 'touko': 5,
    'kesakuu': 6, 'kesäkuu': 6, 'kesa': 6, 'kesä': 6,
    'heinakuu': 7, 'heinäkuu': 7, 'heina': 7, 'heinä': 7,
    'elokuu': 8, 'elo': 8,
    'syyskuu': 9, 'syys': 9,
    'lokakuu': 10, 'loka': 10,
    'marraskuu': 11, 'marras': 11,
    'joulukuu': 12, 'joulu': 12,
    # Polish
    'styczen': 1, 'styczeń': 1, 'sty': 1,
    'luty': 2, 'lut': 2,
    'marzec': 3,
    'kwiecien': 4, 'kwiecień': 4, 'kwi': 4,
    'czerwiec': 6, 'cze': 6,
    'lipiec': 7,
    'sierpien': 8, 'sierpień': 8, 'sie': 8,
    'wrzesien': 9, 'wrzesień': 9, 'wrz': 9,
    'pazdziernik': 10, 'październik': 10, 'paz': 10, 'paź': 10,
    # 'listopad' is November in Polish/Czech and October in Croatian.
    # Lookup prefers the PL/CS meaning. A Croatian October token ("Listopad"),
    # including get_month_name(10, 'hr') used by the %MM search template,
    # therefore parses back as November, not October. Croatian has no unique
    # unaccented October form that avoids this collision; Croatian November
    # still maps uniquely via 'studeni'.
    'listopad': 11, 'lis': 11,
    'grudzien': 12, 'grudzień': 12, 'gru': 12,
    # Czech
    'leden': 1, 'led': 1,
    'unor': 2, 'únor': 2, 'uno': 2,
    'brezen': 3, 'březen': 3, 'bre': 3,
    'duben': 4, 'dub': 4,
    'kveten': 5, 'květen': 5, 'kve': 5,
    'cerven': 6, 'červen': 6, 'cer': 6,
    'cervenec': 7, 'červenec': 7, 'cvc': 7,
    'srpen': 8,
    'zari': 9, 'září': 9, 'zar': 9,
    'rijen': 10, 'říjen': 10, 'rij': 10,
    'prosinec': 12, 'pro': 12,
    # Slovenian
    'marec': 3,
    'junij': 6,
    'julij': 7,
    'avgust': 8, 'avg': 8,
    # Croatian (avoid short forms that collide with PL/CS)
    'sijecanj': 1, 'siječanj': 1, 'sij': 1,
    'veljaca': 2, 'veljača': 2, 'velj': 2,
    'ozujak': 3, 'ozu': 3,
    'travanj': 4, 'tra': 4,
    'svibanj': 5, 'svi': 5,
    'lipanj': 6,
    'srpanj': 7,
    'kolovoz': 8, 'kol': 8,
    'rujan': 9, 'ruj': 9,
    'studeni': 11, 'stu': 11,
    'prosinac': 12,
    # Hungarian
    'január': 1,
    'február': 2,
    'marcius': 3, 'március': 3,
    'aprilis': 4, 'április': 4,
    'majus': 5, 'május': 5,
    'junius': 6, 'június': 6,
    'julius': 7, 'július': 7,
    'augusztus': 8,
    'szeptember': 9, 'sze': 9,
    'október': 10,
    # Romanian
    'ianuarie': 1, 'ian': 1,
    'februarie': 2,
    'martie': 3,
    'aprilie': 4,
    'iunie': 6, 'iun': 6,
    'iulie': 7, 'iul': 7,
    'septembrie': 9,
    'octombrie': 10,
    'noiembrie': 11, 'noi': 11,
    'decembrie': 12,
    # Turkish
    'ocak': 1, 'oca': 1,
    'subat': 2, 'şubat': 2, 'sub': 2, 'şub': 2,
    'mart': 3,
    'nisan': 4, 'nis': 4,
    'mayis': 5, 'mayıs': 5,
    'haziran': 6, 'haz': 6,
    'temmuz': 7, 'tem': 7,
    'agustos': 8, 'ağustos': 8, 'agu': 8, 'ağu': 8,
    'eylul': 9, 'eylül': 9, 'eyl': 9,
    'ekim': 10, 'eki': 10,
    'kasim': 11, 'kasım': 11, 'kas': 11,
    'aralik': 12, 'aralık': 12, 'ara': 12,
    # Greek (transliterated scene forms)
    # 'ian' abbreviation is already mapped under Romanian (same month=1).
    'ianouarios': 1,
    'fevrouarios': 2,
    'martios': 3,
    'aprilios': 4,
    'maios': 5,
    'iounios': 6, 'ioun': 6,
    'ioulios': 7, 'ioul': 7,
    'avgoustos': 8,
    'septemvrios': 9,
    'oktovrios': 10,
    'noemvrios': 11, 'noe': 11,
    'dekemvrios': 12, 'dek': 12,
    # Russian (transliterated)
    'yanvar': 1, 'yan': 1, 'январь': 1, 'янв': 1,
    'fevral': 2, 'февраль': 2, 'февр': 2,
    'апрель': 4, 'апр': 4, 'aprel': 4,
    'май': 5,
    'iyun': 6, 'июнь': 6, 'iyn': 6,
    'iyul': 7, 'июль': 7, 'iyl': 7,
    'август': 8,
    'sentyabr': 9, 'сентябрь': 9, 'сент': 9, 'sen': 9,
    'oktyabr': 10, 'октябрь': 10,
    'noyabr': 11, 'ноябрь': 11, 'нояб': 11, 'noy': 11,
    'dekabr': 12, 'декабрь': 12, 'дек': 12,
    # Japanese / Chinese / Korean numeric month tokens
    '1月': 1, '2月': 2, '3月': 3, '4月': 4, '5月': 5, '6月': 6,
    '7月': 7, '8月': 8, '9月': 9, '10月': 10, '11月': 11, '12月': 12,
    '一月': 1, '二月': 2, '三月': 3, '四月': 4, '五月': 5, '六月': 6,
    '七月': 7, '八月': 8, '九月': 9, '十月': 10, '十一月': 11, '十二月': 12,
    '1월': 1, '2월': 2, '3월': 3, '4월': 4, '5월': 5, '6월': 6,
    '7월': 7, '8월': 8, '9월': 9, '10월': 10, '11월': 11, '12월': 12,
}


def normalize_lang(lang):
    """Return a 2-letter language code, defaulting to English."""
    if not lang:
        return 'en'
    code = str(lang).replace('-', '_').split('_')[0].lower()
    code = _LANG_ALIASES.get(code, code)
    return code or 'en'


def strip_accents(value):
    """Remove diacritics from a unicode string."""
    normalized = unicodedata.normalize('NFKD', value)
    return ''.join(char for char in normalized if not unicodedata.combining(char))


def month_from_name(name):
    """Return month number (1-12) for a month name, or None."""
    if not name:
        return None
    key = name.casefold()
    month = MONTH_NAME_TO_NUMBER.get(key)
    if month:
        return month
    return MONTH_NAME_TO_NUMBER.get(strip_accents(key))


def get_month_name(month, lang=None, abbreviated=False):
    """Return localized month name for search/naming templates.

    :param month: Month number 1-12
    :param lang: Show/indexer language code (e.g. fr, en, fr_FR)
    :param abbreviated: Use short form when True
    :return: Month name string
    """
    if not isinstance(month, int) or not 1 <= month <= 12:
        raise ValueError('month must be an integer from 1 to 12')

    lang_key = normalize_lang(lang)
    names = MONTH_NAMES_ABBR if abbreviated else MONTH_NAMES_FULL
    table = names.get(lang_key) or names['en']
    return table[month]


def first_date_of_month(year, month):
    """Return a placeholder date for month-only releases (day is not the air day).

    Monthly scene packs often omit the day (e.g. Mai.2016). The day value is only a
    technical placeholder; episode matching must resolve by year+month against the
    show database (e.g. first Saturday of the month for a monthly air-by-date show).
    """
    return date(year, month, 1)


def month_date_range(year, month):
    """Return [start, end) dates covering the whole calendar month."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end
