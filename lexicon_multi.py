"""lexicon_multi.py -- the prohibitions, in more than one language.

THE MEASUREMENT THAT PRODUCED THIS. Two statistical tests for "is this the
language I was fitted on" were built and both were REJECTED against real data:

  vocabulary coverage   legitimate English bottoms out at 25%
                        ("hardware wallet replacement after the firmware bug"
                        -- a 19th-century corpus has no `hardware`, `wallet`,
                        `firmware`), which is exactly Spanish's 25%. No
                        separation. Rejected.

  function-word rate    7 of 20 legitimate English memos score 0%
                        ("netflix", "physio session", "school trip money" are
                        noun phrases with no function words at all), against a
                        foreign maximum of 14%. No separation. Rejected.

Transaction memos are too short and too modern for either. So neither number
gates anything; coverage is REPORTED and nothing more.

WHAT THAT FAILURE POINTS AT. The induced-space machinery exists to DISCOVER
which English words sit near `steal` -- that is why it needed 2.95M tokens and
why two of ten principles had to be thrown away when the corpus induced the
wrong axis. But discovery is not needed to know that `robar` means steal. A
translation is not a hypothesis about a corpus; it is a fact about a language.

And adding lexicon words is MONOTONE. score() takes the top-k matched weights,
so a word that is not there contributes nothing and a word that is there can
only push a score UP -- that is X2, already asserted in the v1 suite: there is
no lever that buys a pass. Which means a foreign prohibition list needs no
separation validation to be SAFE. It needs it only to be USEFUL.

So `every known language` decomposes into something finite: not 7,000 fitted
semantic spaces, which do not exist and mostly cannot, but 7,000 lists of the
words for stealing and lying, added one at a time, each addition provably
unable to make the judge more permissive than it was.

WEIGHTS, AND WHY THEY ARE LOWER THAN THE ENGLISH ONES. English weights were
induced and carry evidence (`rob` 404, `plunder` 219, `steal` 163) against
gate_lo 52 and veto_at 260 with top_k 2. These are seeded and carry none. So
each is set at SEED_W, chosen so that ONE foreign hit ABSTAINS -- which blocks,
but claims only "I cannot tell" -- and TWO independent hits VETO. Claiming a
veto from a single unvalidated translation would be asserting a confidence
nobody measured.

HONEST LIMITS OF THIS FILE, stated here rather than found later:
  * These translations are the author's, and no native speaker has reviewed
    them. A wrong entry is a false positive on somebody's ordinary sentence,
    and the suite tests for collisions against benign text but cannot test
    against languages it does not speak either.
  * Coverage is shallow. English `steal` carries 23 induced neighbours; each
    language here carries a handful of stems and no neighbours at all.
  * Morphology is handled by listing forms, so only the forms listed match.
    That is thin everywhere and thinnest for agglutinative and templatic
    languages, where the listed form is one of very many.
  * Absence of a language here is not evidence of innocence. That is the whole
    point of the ILLEGIBLE verdict.
"""

SEED_W = 140          # one hit -> ABSTAIN (>=52). two -> VIOLATES (>=260).

# WHY EVERY ENTRY HERE IS `unverified`, AND WHAT THAT COSTS IT.
#
# A first draft of this file scaled a stem's weight by its LENGTH, on the
# reasoning that a short string collides more often. That reasoning is wrong
# and the test output showed it: `iba` is three Latin characters carrying
# almost no information, and `窃取` is two characters carrying a great deal,
# because one is drawn from an inventory of 26 and the other from ~20,000.
# Length is not evidence. A second draft scaled by estimated information
# content and got `嘘` -- one unambiguous Japanese character -- wrong as well.
#
# The honest conclusion is that I cannot measure collision risk in a language
# I have no corpus for, and a heuristic that pretends otherwise is worse than
# a stated limit. Only the Latin-script entries could be checked at all, and
# only against English: three collided (`vol`, `vole`, `iba`) and are gone.
#
# So every entry carries `verified: false`, and that flag has TEETH rather
# than being a comment:
#
#     an unverified stem can raise a verdict to ABSTAIN, never to VIOLATES.
#
# ABSTAIN blocks, so nothing gets through unexamined -- but the judge never
# claims a VIOLATION on the strength of a translation nobody has reviewed.
# "I see a word I believe means theft and I cannot read the sentence around
# it" is precisely ABSTAIN's meaning, and it is the true epistemic state for
# a language we hold eleven words of.
#
# Promotion to verified is a human act by someone who speaks the language, it
# changes model_id, and it is the only path by which any of these can ever
# veto. That is the adaptive surface, and it opens in the safe direction only.

# Stems, matched EXACTLY -- score() does a dict lookup and nothing else.
# An earlier draft claimed prefix matching; TEST 2 showed what that costs
# (`curi` prefixes `curious`, `sata` prefixes `satan`), and a runtime
# generalisation nobody can audit is worse than an explicit list somebody
# can. Inflections are therefore listed, not derived. Grouped by the
# principle they serve, then by language, so a reviewer can check one language
# without reading the rest.
STEAL = {
 "spa": ["robar", "roban", "robo", "robando", "hurtar", "hurto", "saquear",
         "saqueo", "sustraer", "malversar", "ladron"],
 "por": ["roubar", "roubo", "furtar", "furto", "saquear", "saque", "desviar"],
 "fra": ["voler", "derober", "piller", "pillage", "detourner",
         "escroquer", "larcin"],
 "ita": ["rubare", "rubo", "furto", "saccheggiare", "sottrarre", "trafugare"],
 "deu": ["stehlen", "stiehlt", "diebstahl", "entwenden", "unterschlagen",
         "pluendern", "plündern", "raub", "rauben"],
 "nld": ["stelen", "steelt", "diefstal", "ontvreemden", "verduisteren",
         "plunderen", "roven"],
 "swe": ["stjala", "stjäla", "stold", "stöld", "plundra", "forskingra"],
 "dan": ["stjaele", "stjæle", "tyveri", "plyndre"],
 "nor": ["stjele", "tyveri", "plyndre"],
 "pol": ["kradziez", "kradzież", "ukrasc", "ukraść", "okrasc", "zlodziej",
         "splandrowac", "przywlaszczyc"],
 "ces": ["ukrast", "kradez", "krádež", "zpronevera"],
 "rus": ["украсть", "воровать", "кража", "ограбить", "грабеж", "хищение",
         "присвоить", "вор"],
 "ukr": ["вкрасти", "крадіжка", "пограбувати", "розкрадання"],
 "tur": ["calmak", "çalmak", "hirsizlik", "hırsızlık", "yagmalamak",
         "zimmetine"],
 "vie": ["trom", "trộm", "cuop", "cướp", "chiem doat", "bien thu"],
 "ind": ["curi", "mencuri", "pencurian", "rampok", "merampok", "gelapkan"],
 "msa": ["curi", "mencuri", "kecurian", "rompak", "merompak"],
 "swa": ["wizi", "kuiba", "pora", "kupora", "nyakua"],
 "hau": ["sata", "sace", "yi fashi", "kwace"],
 "amh": ["መስረቅ", "ስርቆት", "ዘረፋ"],
 "arb": ["سرقة", "يسرق", "سرق", "نهب", "ينهب", "اختلاس", "سلب"],
 "fas": ["دزدی", "دزدیدن", "سرقت", "غارت", "اختلاس"],
 "urd": ["چوری", "چرانا", "لوٹ", "غبن"],
 "hin": ["चोरी", "चुराना", "लूट", "लूटना", "गबन", "अपहरण"],
 "ben": ["চুরি", "চোর", "লুট", "আত্মসাৎ"],
 "tam": ["திருட", "திருட்டு", "கொள்ளை"],
 "tel": ["దొంగతనం", "దోచుకోవడం"],
 "zho": ["偷", "偷窃", "窃取", "盗窃", "抢劫", "侵占", "贪污", "掠夺"],
 "jpn": ["盗む", "窃盗", "強奪", "横領", "着服"],
 "kor": ["훔치다", "절도", "강탈", "횡령"],
 "tha": ["ขโมย", "ลักทรัพย์", "ปล้น", "ยักยอก"],
 "heb": ["גניבה", "לגנוב", "גזל", "מעילה"],
 "ell": ["κλοπη", "κλοπή", "κλεβω", "κλέβω", "λεηλασια", "υπεξαιρεση"],
 "lat": ["furare", "furtum", "furari", "praedare", "rapere", "peculatus"],
 "epo": ["steli", "sxteli", "ŝteli", "ŝtelo", "rabi", "rabo"],
}

FALSE_WITNESS = {
 "spa": ["mentir", "mentira", "miente", "enganar", "engañar", "engano",
         "fraude", "falsificar", "estafa"],
 "por": ["mentir", "mentira", "enganar", "fraude", "falsificar", "burla"],
 "fra": ["mentir", "mensonge", "tromper", "tromperie", "fraude", "falsifier",
         "escroquerie"],
 "ita": ["mentire", "menzogna", "ingannare", "inganno", "frode", "falsificare"],
 "deu": ["luegen", "lügen", "luege", "lüge", "betruegen", "betrügen",
         "betrug", "faelschen", "fälschen", "taeuschen"],
 "nld": ["liegen", "leugen", "bedriegen", "bedrog", "fraude", "vervalsen"],
 "swe": ["ljuga", "logn", "lögn", "bedraga", "bedrageri", "forfalska"],
 "pol": ["klamac", "kłamać", "klamstwo", "oszukac", "oszustwo", "falszowac"],
 "rus": ["ложь", "лгать", "обман", "обмануть", "мошенничество", "подделать"],
 "ukr": ["брехня", "обман", "шахрайство", "підробити"],
 "tur": ["yalan", "aldatmak", "dolandiricilik", "dolandırıcılık", "sahtecilik"],
 "vie": ["noi doi", "lua dao", "lừa đảo", "gian lan", "gia mao"],
 "ind": ["bohong", "menipu", "penipuan", "palsu", "memalsukan"],
 "swa": ["uongo", "danganya", "udanganyifu", "ghushi"],
 "arb": ["كذب", "يكذب", "خداع", "احتيال", "تزوير", "غش"],
 "fas": ["دروغ", "فریب", "کلاهبرداری", "جعل"],
 "hin": ["झूठ", "धोखा", "ठगी", "जालसाजी", "फर्जी"],
 "ben": ["মিথ্যা", "প্রতারণা", "জালিয়াতি"],
 "zho": ["撒谎", "谎言", "欺骗", "诈骗", "伪造", "作假"],
 "jpn": ["嘘", "欺く", "詐欺", "偽造", "改ざん"],
 "kor": ["거짓말", "속이다", "사기", "위조"],
 "tha": ["โกหก", "หลอกลวง", "ฉ้อโกง", "ปลอมแปลง"],
 "heb": ["שקר", "לשקר", "הונאה", "זיוף"],
 "ell": ["ψεμα", "ψέμα", "εξαπατω", "απατη", "απάτη", "πλαστογραφια"],
 "lat": ["mentiri", "mendacium", "fallere", "fraus", "falsare"],
 "epo": ["mensogi", "mensogo", "trompi", "trompo", "falsi"],
}

STEAL_P = "You shall not steal."
FALSE_P = "You shall not bear false witness."


def build(seed_w: int = SEED_W):
    """{principle: {stem: weight}} plus the language index, for the model file."""
    out = {STEAL_P: {}, FALSE_P: {}}
    langs = {STEAL_P: {}, FALSE_P: {}}
    for principle, table in ((STEAL_P, STEAL), (FALSE_P, FALSE_WITNESS)):
        for lang, stems in sorted(table.items()):
            langs[principle][lang] = len(stems)
            for s in stems:
                out[principle][s.lower()] = seed_w
    return out, langs
