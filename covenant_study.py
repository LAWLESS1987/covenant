#!/usr/bin/env python3
"""covenant_study.py -- the covenant reads the moral traditions and turns what
it finds into cases it can be judged on.

WHY (asked 2026-09-04: "study all philosophy and religious texts and
teachings", "learn from all useable science and tech to improve repeatedly",
and "we can't be reliant on other companies")

  The student judge learns from ops/verdicts.jsonl and nothing else. Its
  material so far is what a teacher model invented plus what I wrote by hand.
  Both are narrow, and both are somebody's opinion. The moral traditions are
  the widest source of stated principle there is, they are public domain, and
  they cost nothing to read.

  So: fetch the texts, extract the PRECEPTS (the sentences that actually tell
  someone to do or not do something), and hand each precept to the covenant's
  teacher to turn into two transactions -- one that violates it and one that
  honours it -- which are then judged BLIND, exactly as covenant_distill.py
  already does, and kept only where the blind verdict matches the intent.

WHAT IS LOCAL AND WHAT IS NOT

  Fetching is one HTTP GET per book from Project Gutenberg, cached on disk, so
  it happens once. EXTRACTION IS ENTIRELY LOCAL -- no model, no network, plain
  Python over the text. That is the part that would otherwise be expensive,
  and it is the part the covenant does for itself. Only the last step, turning
  a precept into transactions, needs a model, and it uses whichever teacher
  covenant_distill is configured for.

WHAT IT REFUSES TO DO

  It does not train on the texts. A bag of words fitted to scripture would
  learn the vocabulary of a translation, not a principle -- "thou" is not
  evidence of anything. Only the generated, blind-judged TRANSACTIONS reach
  the ledger, and every one carries the precept and the book it came from.

  It does not decide which tradition is right. A precept is recorded as what
  a text says, with its source, and the disagreements are kept: two traditions
  that contradict each other both go in, and the judging step is what settles
  whether a given transaction is a violation.

USE
  python covenant_study.py --list                  # the reading list
  python covenant_study.py --fetch [--limit N]     # download and cache
  python covenant_study.py --extract               # precepts -> ops/study/PRECEPTS.jsonl
  python covenant_study.py --report                # what has been read, by tradition
LICENCE: public domain. The texts are too; that is why they were chosen.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "private", "study")          # gitignored: 20 MB of public text
OUT = os.path.join(HERE, "ops", "study")
PRECEPTS = os.path.join(OUT, "PRECEPTS.jsonl")

# How many rejections retire a precept from the queue. See the block in
# generate() that uses it: a precept enters the `done` set only when its pair
# was KEPT, so without this a precept whose pair keeps failing is re-served
# every night for ever. Three, not one: a rejection can be the teacher having a
# bad night, and retiring on a single failure would throw away precepts that
# would have worked on the next pass.
RETIRE_AFTER = 3
REPORT = os.path.join(OUT, "STUDY.md")

# The reading list. Public domain, Project Gutenberg ids, chosen for breadth of
# TRADITION rather than agreement: the point is not one ethic but many, because
# a principle that only one tradition states is a principle the judge should
# know is contested.
# Three ids left this list on 2026-09-04 because the files behind them are not
# what the id was believed to be: 7147 is "The French in the Heart of America",
# 2412 is Aristotle's "Categories" (logic, not ethics) and 17529 is "Othello".
# They were caught by verify(), not by reading. Two more were relabelled to what
# their files actually say. A source that cannot be checked is not a source.
BOOKS = [
    (10, "The Bible, King James Version", "hebrew-christian"),
    (2800, "The Koran (Rodwell translation)", "islamic"),
    (2388, "The Bhagavad Gita", "hindu"),
    (2680, "Meditations", "stoic"),
    (10661, "A Selection from the Discourses of Epictetus with the Encheiridion", "stoic"),
    (4280, "The Critique of Pure Reason", "kantian"),
    (5682, "The Fundamental Principles of the Metaphysic of Morals", "kantian"),
    (8438, "The Ethics of Aristotle (Nicomachean)", "aristotelian"),
    (1497, "The Republic", "platonic"),
    (3330, "The Analects of Confucius", "confucian"),
    (216, "The Tao Teh King (Tao Te Ching)", "taoist"),
    (11224, "Utilitarianism (Mill)", "utilitarian"),
    (34901, "On Liberty", "liberal"),
    (1232, "The Prince", "machiavellian"),
    (3207, "Leviathan", "hobbesian"),
    (7370, "Second Treatise of Government", "lockean"),
    (4363, "Beyond Good and Evil", "nietzschean"),
    (1080, "A Modest Proposal", "satire"),
    (3300, "The Wealth of Nations", "smithian"),
    # A206 (2026-09-21, his words: "have the system incorporate every piece of
    # literature on early childhood development you can find also on teaching
    # autistic children and human psychology then go to the top 20
    # philosophers"). What can be incorporated is what is public domain and
    # verifiable: every id below is checked against the file's own title by
    # verify(), and a mismatch is skipped, not read. Modern work on autism
    # (Kanner 1943 onward) is in copyright and is NOT here; the nearest public
    # texts are the founders of special education and of teaching a child who
    # does not learn the ordinary way.
    # -- early childhood development and education
    (5427, "Emile; or, Concerning Education (Rousseau)", "child-development"),
    (39863, "The Montessori Method: Scientific Pedagogy as Applied to Child Education", "child-development"),
    (29635, "Dr. Montessori's Own Handbook", "child-development"),
    (852, "Democracy and Education (Dewey)", "child-development"),
    (37423, "How We Think (Dewey)", "child-development"),
    (53910, "The School and Society (Dewey)", "child-development"),
    (16287, "Talks to Teachers on Psychology (James)", "child-development"),
    (2397, "The Story of My Life (Helen Keller, with Anne Sullivan's letters on teaching)", "teaching-the-different-child"),
    (19549, "The Mind of the Child, Part II: The Development of the Intellect (Preyer)", "child-development"),
    (62175, "Studies of Childhood (Sully)", "child-development"),
    # -- human psychology
    (57628, "The Principles of Psychology, Volume 1 (James)", "psychology"),
    (15489, "Dream Psychology (Freud)", "psychology"),
    (38219, "A General Introduction to Psychoanalysis (Freud)", "psychology"),
    (65903, "Psychology of the Unconscious (Jung)", "psychology"),
    (445, "The Crowd: A Study of the Popular Mind (Le Bon)", "psychology"),
    # -- the philosophers not already above
    (59, "Discourse on the Method (Descartes)", "cartesian"),
    (3800, "The Ethics (Spinoza)", "spinozist"),
    (9662, "An Enquiry Concerning Human Understanding (Hume)", "humean"),
    (4705, "A Treatise of Human Nature (Hume)", "humean"),
    (3296, "The Confessions of St. Augustine", "augustinian"),
    (17611, "Summa Theologica, Part I (Aquinas)", "thomist"),
    (18269, "Pascal's Pensees", "pascalian"),
    (46333, "The Social Contract (Rousseau)", "rousseauian"),
    (5683, "The Critique of Practical Reason (Kant)", "kantian"),
    (785, "On the Nature of Things (Lucretius)", "epicurean"),
    (2017, "The Dhammapada", "buddhist"),
    (10732, "The Essays of Arthur Schopenhauer: The Wisdom of Life", "schopenhauerian"),
    (4723, "A Treatise Concerning the Principles of Human Knowledge (Berkeley)", "berkeleian"),
    (45988, "Novum Organum (Bacon)", "baconian"),
    (61, "The Communist Manifesto", "marxist"),
    (52190, "Ecce Homo (Nietzsche)", "nietzschean"),
    (1600, "Symposium (Plato)", "platonic"),
    (6762, "Politics (Aristotle)", "aristotelian"),
    (19942, "Candide (Voltaire)", "enlightenment"),
    (51635, "Hegel's Lectures on the History of Philosophy, Volume 1", "hegelian"),
    (37020, "Children's Ways (Sully)", "child-development"),
    (11667, "Gentle Measures in the Management and Training of the Young (Abbott)", "child-development"),
    (41386, "Human Nature and Conduct: An Introduction to Social Psychology (Dewey)", "psychology"),
    # ids found by catalogue search (gutendex), not recalled; thirteen recalled
    # ids were wrong and are gone -- not on Gutenberg under those titles:
    # Locke's Thoughts on Education, Froebel, Pestalozzi, Kirkpatrick, Tanner,
    # Thorndike, Baldwin, McDougall, Adler, Wundt, the Monadology, Kierkegaard.
    # A209 (2026-09-21, his words: 'access to all "banned" books'): every
    # English book on Gutenberg's own banned-books shelf (Anne Haight's list),
    # 137 found by catalogue query, 22 already above or duplicate titles, 115
    # here. Banned or challenged books still in copyright are not fetched:
    # "free" does not mean "taken".
    (1661, "The Adventures of Sherlock Holmes (Doyle)", "banned-books-shelf"),
    (2527, "The Sorrows of Young Werther (Goethe)", "banned-books-shelf"),
    (6593, "History of Tom Jones, a Foundling (Fielding)", "banned-books-shelf"),
    (74, "The Adventures of Tom Sawyer, Complete (Twain)", "banned-books-shelf"),
    (76, "Adventures of Huckleberry Finn (Twain)", "banned-books-shelf"),
    (4300, "Ulysses (Joyce)", "banned-books-shelf"),
    (27827, "The Kama Sutra of Vatsyayana: Translated From the Sanscrit i (Vatsyayana)", "banned-books-shelf"),
    (20, "Paradise Lost (Milton)", "banned-books-shelf"),
    (160, "The Awakening, and Selected Short Stories (Chopin)", "banned-books-shelf"),
    (203, "Uncle Tom's Cabin (Stowe)", "banned-books-shelf"),
    (215, "The call of the wild (London)", "banned-books-shelf"),
    (5921, "The History of Don Quixote, Volume 1, Complete (Cervantes Saavedra)", "banned-books-shelf"),
    (2610, "Notre-Dame de Paris (Hugo)", "banned-books-shelf"),
    (1200, "Gargantua and Pantagruel (Rabelais)", "banned-books-shelf"),
    (829, "Gulliver's Travels into Several Remote Nations of the World (Swift)", "banned-books-shelf"),
    (7700, "Lysistrata (Aristophanes)", "banned-books-shelf"),
    (5225, "The Satyricon — Complete (Petronius Arbiter)", "banned-books-shelf"),
    (25344, "The Scarlet Letter (Hawthorne)", "banned-books-shelf"),
    (135, "Les Misérables (Hugo)", "banned-books-shelf"),
    (1228, "On the Origin of Species By Means of Natural Selection: Or,  (Darwin)", "banned-books-shelf"),
    (25717, "The History of the Decline and Fall of the Roman Empire: Tab (Gibbon)", "banned-books-shelf"),
    (30201, "In Praise of Folly: Illustrated with Many Curious Cuts (Erasmus)", "banned-books-shelf"),
    (3600, "Essays of Michel de Montaigne — Complete (Montaigne)", "banned-books-shelf"),
    (2814, "Dubliners (Joyce)", "banned-books-shelf"),
    (1322, "Leaves of Grass (Whitman)", "banned-books-shelf"),
    (3160, "The Odyssey (Homer)", "banned-books-shelf"),
    (14591, "Faust [part 1]. Translated Into English in the Original Metr (Goethe)", "banned-books-shelf"),
    (110, "Tess of the d'Urbervilles: A Pure Woman (Hardy)", "banned-books-shelf"),
    (2413, "Madame Bovary (Flaubert)", "banned-books-shelf"),
    (10615, "An Essay Concerning Humane Understanding, Volume 1: MDCXC, B (Locke)", "banned-books-shelf"),
    (25305, "Memoirs of Fanny Hill: A New and Genuine Edition from the Or (Cleland)", "banned-books-shelf"),
    (140, "The Jungle (Sinclair)", "banned-books-shelf"),
    (2981, "The Memoirs of Jacques Casanova de Seingalt, 1725-1798. Comp (Casanova)", "banned-books-shelf"),
    (27942, "A System of Logic, Ratiocinative and Inductive (Mill)", "banned-books-shelf"),
    (13610, "Studies in the Psychology of Sex, Volume 1: The Evolution of (Ellis)", "banned-books-shelf"),
    (30107, "Principles of Political Economy: Abridged with Critical, Bib (Mill)", "banned-books-shelf"),
    (1515, "The Merchant of Venice (Shakespeare)", "banned-books-shelf"),
    (5500, "The Advancement of Learning (Bacon)", "banned-books-shelf"),
    (153, "Jude the Obscure (Hardy)", "banned-books-shelf"),
    (28885, "Alice's Adventures in Wonderland: Illustrated by Arthur Rack (Carroll)", "banned-books-shelf"),
    (3328, "Man and Superman: A Comedy and a Philosophy (Shaw)", "banned-books-shelf"),
    (217, "Sons and Lovers (Lawrence)", "banned-books-shelf"),
    (28488, "Tartuffe; Or, The Hypocrite (Molière)", "banned-books-shelf"),
    (507, "Adam Bede (Eliot)", "banned-books-shelf"),
    (689, "The Kreutzer Sonata and Other Stories (Tolstoy)", "banned-books-shelf"),
    (6124, "Pamela, or Virtue Rewarded (Richardson)", "banned-books-shelf"),
    (608, "Areopagitica: A Speech for the Liberty of Unlicensed Printin (Milton)", "banned-books-shelf"),
    (8121, "Ghosts (Ibsen)", "banned-books-shelf"),
    (4240, "Women in Love (Lawrence)", "banned-books-shelf"),
    (18569, "Voltaire's Philosophical Dictionary (Voltaire)", "banned-books-shelf"),
    (4094, "The Chinese Classics — Volume 1: Confucian Analects (Legge)", "banned-books-shelf"),
    (1666, "The Golden Asse (Apuleius)", "banned-books-shelf"),
    (28948, "The Rainbow (Lawrence)", "banned-books-shelf"),
    (1097, "Mrs. Warren's Profession (Shaw)", "banned-books-shelf"),
    (3742, "The Writings of Thomas Paine — Volume 2 (1779-1792): The Rig (Paine)", "banned-books-shelf"),
    (808, "The Complete Plays of Gilbert and Sullivan (Gilbert)", "banned-books-shelf"),
    (2562, "The Clouds (Aristophanes)", "banned-books-shelf"),
    (3013, "The Birds (Aristophanes)", "banned-books-shelf"),
    (1290, "Salammbo (Flaubert)", "banned-books-shelf"),
    (6782, "The Robbers (Schiller)", "banned-books-shelf"),
    (5300, "Tales and Novels of J. de La Fontaine — Complete (La Fontaine)", "banned-books-shelf"),
    (9371, "The Praise of Folly (Erasmus)", "banned-books-shelf"),
    (274, "Disputation of Doctor Martin Luther on the Power and Efficac (Luther)", "banned-books-shelf"),
    (3100, "The Chinese Classics: with a translation, critical and exege (Legge)", "banned-books-shelf"),
    (3726, "The Decameron, Volume I (Boccaccio)", "banned-books-shelf"),
    (586, "Religio Medici, Hydriotaphia, and the Letter to a Friend (Browne)", "banned-books-shelf"),
    (30433, "Émile; Or, Concerning Education; Extracts (Rousseau)", "banned-books-shelf"),
    (30344, "The Fortunate Mistress (Parts 1 and 2): or a History of the  (Defoe)", "banned-books-shelf"),
    (33797, "Sinister Street, vol. 1 (MacKenzie)", "banned-books-shelf"),
    (37478, "The Prose Writings of Heinrich Heine (Heine)", "banned-books-shelf"),
    (4737, "A Tale of a Tub (Swift)", "banned-books-shelf"),
    (17824, "Little Black Sambo (Bannerman)", "banned-books-shelf"),
    (392, "Jerusalem Delivered (Tasso)", "banned-books-shelf"),
    (21262, "The Works of Christopher Marlowe, Vol. 3 (of 3) (Marlowe)", "banned-books-shelf"),
    (4797, "The Complete Poetical Works of Percy Bysshe Shelley — Volume (Shelley)", "banned-books-shelf"),
    (20580, "Napoleon the Little (Hugo)", "banned-books-shelf"),
    (35402, "Poems & Ballads (First Series) (Swinburne)", "banned-books-shelf"),
    (33896, "Dante. An essay. To which is added a translation of De Monar (Dante Alighieri)", "banned-books-shelf"),
    (804, "A Sentimental Journey Through France and Italy (Sterne)", "banned-books-shelf"),
    (38841, "The Commercial Restraints of Ireland (Hely-Hutchinson)", "banned-books-shelf"),
    (11248, "The Delights of Wisdom Pertaining to Conjugial Love: To Whic (Swedenborg)", "banned-books-shelf"),
    (13102, "The Decameron, Volume II (Boccaccio)", "banned-books-shelf"),
    (20015, "The Child of Pleasure (D'Annunzio)", "banned-books-shelf"),
    (7114, "Une Vie, a Piece of String and Other Stories (Maupassant)", "banned-books-shelf"),
    (6886, "First Footsteps in East Africa (Burton)", "banned-books-shelf"),
    (450, "Susan Lenox: Her Fall and Rise (Phillips)", "banned-books-shelf"),
    (31053, "The History of the Devil, As Well Ancient as Modern: In Two  (Defoe)", "banned-books-shelf"),
    (5267, "Sister Carrie (Dreiser)", "banned-books-shelf"),
    (31732, "The sex side of life : $b an explanation for young people (Dennett)", "banned-books-shelf"),
    (12784, "The Prose Works of Jonathan Swift, D.D. — Volume 06: The Dra (Swift)", "banned-books-shelf"),
    (27401, "Poems & Ballads (Second Series): Swinburne's Poems Volume II (Swinburne)", "banned-books-shelf"),
    (1090, "The Bickerstaff-Partridge Papers (Swift)", "banned-books-shelf"),
    (8771, "Jurgen: A Comedy of Justice (Cabell)", "banned-books-shelf"),
    (31824, "The 'Genius' (Dreiser)", "banned-books-shelf"),
    (25053, "The Temptation of St. Antony; Or, A Revelation of the Soul (Flaubert)", "banned-books-shelf"),
    (31015, "The Poetical Works of Elizabeth Barrett Browning, Volume 4 (Browning)", "banned-books-shelf"),
    (18863, "The Loom of Youth (Waugh)", "banned-books-shelf"),
    (39133, "The Dramas of Victor Hugo: Mary Tudor, Marion de Lorme, Esme (Hugo)", "banned-books-shelf"),
    (16896, "Corinne; Or, Italy. Volume 1 (of 2) (Staël)", "banned-books-shelf"),
    (9310, "Casanova's Homecoming (Schnitzler)", "banned-books-shelf"),
    (8157, "Esther Waters (Moore)", "banned-books-shelf"),
    (6828, "The Works of Henry Fielding, vol. 12 (Fielding)", "banned-books-shelf"),
    (4788, "Mademoiselle Fifi (Maupassant)", "banned-books-shelf"),
    (2250, "King Richard II (Shakespeare)", "banned-books-shelf"),
    (2266, "King Lear (Shakespeare)", "banned-books-shelf"),
    (8899, "Three Weeks (Glyn)", "banned-books-shelf"),
    (26884, "The backwash of war : $b the human wreckage of the battlefie (La Motte)", "banned-books-shelf"),
    (5722, "The Shewing-up of Blanco Posnet (Shaw)", "banned-books-shelf"),
    (2137, "Rosamund, Queen of the Lombards: A Tragedy (Swinburne)", "banned-books-shelf"),
    (18726, "Poems and Ballads (Third Series): Taken from The Collected P (Swinburne)", "banned-books-shelf"),
    (31790, "Family Limitation (Sanger)", "banned-books-shelf"),
    (18545, "A Mummer's Tale (France)", "banned-books-shelf"),
    (7508, "A Mummer's Wife (Moore)", "banned-books-shelf"),
]

UA = {"User-Agent": "covenant-study/1 (public-domain texts; one fetch, cached)"}

# The covenant's own governing documents. Lawrence wrote these, they are in the
# repository, and they are the one source whose attribution is not in doubt.
#
# WHAT WAS TRIED FIRST AND REJECTED, 2026-09-04. He asked that his AI accounts
# and social media be used to learn from. The material already collected is
# private/njest1987_videos/text/*.md -- 105 OCR transcripts of screen
# recordings of his own chats. Reading them: the OCR is heavy ("thqrp's a real
# intonal critique", "vvoik"), and the speaker labels are themselves OCR
# guesses -- "Me", "Them", "?", "Peace.:", "Thought process:" -- so a line
# cannot be reliably attributed to him rather than to the model he was talking
# to. Training an ethics judge on that would teach it OCR noise and put words
# in his mouth, or the model's words in his. The right source for his voice is
# the text he actually wrote and committed.
OWN_DOCS = [
    ("CONTRIBUTING.md", "covenant"),
    (os.path.join("docs", "CONSTITUTION.md"), "covenant"),
    (os.path.join("docs", "GOVERNANCE.md"), "covenant"),
]

# A precept is a sentence that tells someone to do or not do something. These
# are the shapes that survived reading the output: deontic modals, imperatives
# of prohibition, and explicit statements of what is right or wrong. Everything
# else in a book of philosophy is argument, and argument is not a rule.
PROHIBIT = re.compile(
    r"\b(shall not|shalt not|must not|ought not|should not|do not|don't|never|"
    r"let no man|no one (?:should|ought|may)|it is (?:wrong|unjust|evil|wicked) to|"
    r"forbidden|unlawful to)\b", re.I)
OBLIGE = re.compile(
    r"\b(shall|shalt|must|ought to|should|let (?:him|us|them)|it is (?:right|just|good|our duty) to|"
    r"we are bound to|thou shalt)\b", re.I)
# The sentence has to be about what this judge actually judges: value moving
# between people, and honesty about it. The first filter used any
# other-regarding word at all and returned Kant on causation and Smith on the
# silver content of the livre -- true sentences, and not rules about conduct.
# MEASURED 2026-09-04: of the first 1795 extracted that way, a hand sample of
# 12 held 4 genuine precepts. Both a DEONTIC marker and a TRANSFER term are
# now required, and the argument words that marked the false positives are
# excluded outright.
TRANSFER = re.compile(
    r"\b(debt|debtor|creditor|wages?|hire[ds]?|lend|lent|lends|borrow(?:ed|s)?|usury|"
    r"interest|money|silver|gold|price|pay|paid|payment|weight|measure|balance|"
    r"steal|stole|stolen|theft|thief|rob|robbed|defraud|fraud|cheat|deceive|"
    r"deceit|false witness|oath|vow|promise|pledge|trade|buy|bought|sell|sold|"
    r"gift|alms|charity|tithe|offering|lend|loan|property|goods|possessions?|"
    r"owe[sd]?|owing|wealth|riches|poor|needy|widow|orphan|stranger|servant|hire)\b", re.I)
# Marks of argument rather than rule. A sentence explaining WHY is not a
# precept, and generating a transaction from it produces nonsense.
ARGUMENT = re.compile(
    r"\b(therefore|for instance|for example|in other words|it follows|hence|"
    r"thus we|philosoph|metaphysic|proposition|syllogism|hypothesis|"
    r"chapter|footnote|preface|translat)\b", re.I)
# Ritual, cultic and household-law vocabulary. These sentences pass the
# transfer filter because they mention silver, servants, payment or measures,
# and they are not rules a TRANSFER can break. MEASURED 2026-09-04: the first
# precepts handed to the teacher were Levitical, and it dutifully wrote
# "Bought a slave to work on a farm" and "Skipped circumcision for a child
# born at home" as ledger memos. The gate's own prompt already says a transfer
# cannot break the Sabbath or make a carved image; the extractor has to know
# it too, or it feeds the judge a world it will never see.
RITUAL = re.compile(
    r"\b(circumcis|sacrific|burnt offering|meat offering|sin offering|altar|"
    r"priest|levite|tabernacle|sanctuary|unclean|leaven|unleaven|holy convocation"
    r"|atonement|anoint|incense|vow unto the lord|firstborn|tithe of the herd|"
    r"sabbath|jubile|passover|idol|graven|sabbaths|congregation of israel|"
    r"bondman|bondmaid|concubine|slave|slaves|stoned|put to death)\b", re.I)
VERSE = re.compile(r"^\s*\d+[:.]\d+\s*")
_SENT = re.compile(r"(?<=[.;:!?])\s+")


# A208 (2026-09-21, his words: "Find open source autism stuff"). Modern work on
# autism is in copyright, but its open-access half is not closed: Europe PMC
# serves the full text of every article whose authors chose a Creative
# Commons BY (or CC0) licence, by REST, no key. Measured the day this was
# written: 13,392 open-access CC-licensed autism articles on teaching,
# education or intervention; 611 CC BY reviews with full text. The most
# cited come first, a bounded few per topic per pass, each cached with its
# title, licence and source URL so it can be checked like a Gutenberg file.
OA_REGISTRY = os.path.join(OUT, "oa_sources.jsonl")
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
UA = {"User-Agent": "covenant-study (public-domain study pipeline; contact via github.com/LAWLESS1987/covenant)"}

# topic -> Europe PMC query. Open access, Creative Commons BY (or CC0) with
# full text only: what may be cached and studied with attribution.
OA_QUERIES = [
    ("open-access: autism teaching",
     '(TITLE:autism OR TITLE:autistic) AND (teaching OR classroom OR education OR "evidence-based practice") AND OPEN_ACCESS:Y AND (LICENSE:"cc by" OR LICENSE:"cc0") AND HAS_FT:Y AND (PUB_TYPE:review OR PUB_TYPE:"systematic review")'),
    ("open-access: autism early childhood",
     '(TITLE:autism OR TITLE:autistic) AND (toddler OR preschool OR "early childhood" OR "early intervention" OR "parent-mediated") AND OPEN_ACCESS:Y AND (LICENSE:"cc by" OR LICENSE:"cc0") AND HAS_FT:Y'),
    ("open-access: autistic voices",
     '(TITLE:autistic) AND (participatory OR "lived experience" OR "autistic adults" OR neurodiversity) AND OPEN_ACCESS:Y AND (LICENSE:"cc by" OR LICENSE:"cc0") AND HAS_FT:Y'),
    ("open-access: child development",
     '(TITLE:"child development") AND OPEN_ACCESS:Y AND (LICENSE:"cc by" OR LICENSE:"cc0") AND HAS_FT:Y'),
]


def oa_search(query, n):
    u = EPMC + "/search?" + urllib.parse.urlencode({"query": query, "format": "json", "pageSize": n,
                                                     "resultType": "core", "sort": "CITED desc"})
    d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
    return d.get("hitCount", 0), d.get("resultList", {}).get("result", [])


def oa_text(pmcid):
    xml = urllib.request.urlopen(urllib.request.Request(EPMC + "/%s/fullTextXML" % pmcid, headers=UA), timeout=90).read().decode("utf-8", "replace")
    m = re.search(r"<article-title>(.*?)</article-title>", xml, re.S)
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
    parts = []
    for tag in ("abstract", "body"):
        if "<%s" % tag in xml and "</%s>" % tag in xml:
            seg = xml.split("<%s" % tag, 1)[1].split(">", 1)[1].split("</%s>" % tag, 1)[0]
            seg = re.sub(r"<(table-wrap|fig|ref-list|xref)[^>]*>.*?</\1>", " ", seg, flags=re.S)
            seg = re.sub(r"</(p|sec|title)>", "\n\n", seg)
            parts.append(re.sub(r"<[^>]+>", " ", seg))
    text = re.sub(r"[ \t]+", " ", "\n".join(parts))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return title, text.strip()


def fetch_oa(cache=None, registry=None, per_query=5, say=print, queries=None, search=None, get_text=None):
    cache = cache or CACHE; registry = registry or OA_REGISTRY; queries = queries or OA_QUERIES
    search = search or oa_search; get_text = get_text or oa_text
    """Cache up to per_query new articles per topic; registry is a jsonl of
    what was cached (pmcid, title, tradition, licence, url). Returns (new, skipped)."""
    os.makedirs(cache, exist_ok=True)
    have = set()
    try:
        with open(registry, encoding="utf-8") as fh:
            for line in fh:
                try:
                    have.add(json.loads(line)["pmcid"])
                except (ValueError, KeyError):
                    pass
    except OSError:
        pass
    new = skipped = 0
    for tradition, query in queries:
        try:
            hits, rows = search(query, per_query * 3)
        except Exception as e:                                   # noqa: BLE001
            say("  %-40s search FAILED %s: %s" % (tradition, type(e).__name__, str(e)[:60])); continue
        got = 0
        for r in rows:
            pmcid, lic = r.get("pmcid"), str(r.get("license", "")).lower()
            if not pmcid or pmcid in have or not (lic.startswith("cc by") and "nc" not in lic and "nd" not in lic or lic == "cc0"):
                skipped += 1; continue
            if got >= per_query:
                break
            try:
                title, text = get_text(pmcid)
            except Exception as e:                               # noqa: BLE001
                say("  %s fetch FAILED %s" % (pmcid, type(e).__name__)); continue
            if len(text) < 5000 or not title:
                skipped += 1; continue
            p = os.path.join(cache, "oa_%s.txt" % pmcid)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("Title: %s\nSource: https://europepmc.org/article/PMC/%s\nLicence: %s\nJournal: %s (%s)\nCited: %s\n\n%s\n"
                         % (title, pmcid, r.get("license"), r.get("journalTitle", ""), r.get("pubYear", ""), r.get("citedByCount", ""), text))
            with open(registry, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "pmcid": pmcid, "title": title, "tradition": tradition,
                                     "licence": r.get("license"), "url": "https://europepmc.org/article/PMC/%s" % pmcid,
                                     "chars": len(text), "cited": r.get("citedByCount")}, ensure_ascii=False) + "\n")
            have.add(pmcid); new += 1; got += 1
            say("  %-40s %s %5dk  %s" % (tradition, pmcid, len(text) // 1000, title[:60]))
        say("  %-40s %d of %d hits cached this pass" % (tradition, got, hits))
    return new, skipped



def oa_sources(registry=None):
    """[(pmcid, title, tradition)] from the registry, in order cached."""
    out = []
    try:
        with open(registry or OA_REGISTRY, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line); out.append((r["pmcid"], r["title"], r["tradition"]))
                except (ValueError, KeyError):
                    pass
    except OSError:
        pass
    return out


def book_path(gid):
    return os.path.join(CACHE, "pg%d.txt" % gid)


def fetch(gid, title, say=print):
    p = book_path(gid)
    if os.path.exists(p) and os.path.getsize(p) > 20000:
        return "cached"
    for url in ("https://www.gutenberg.org/cache/epub/%d/pg%d.txt" % (gid, gid),
                "https://www.gutenberg.org/files/%d/%d-0.txt" % (gid, gid)):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if len(data) < 20000:
                continue
            os.makedirs(CACHE, exist_ok=True)
            with open(p, "wb") as fh:
                fh.write(data)
            return "fetched %.1f MB" % (len(data) / 1048576.0)
        except Exception as e:                                   # noqa: BLE001
            last = "%s: %s" % (type(e).__name__, str(e)[:60])
    return "FAILED (%s)" % last


def declared_title(gid):
    """What the file itself says it is. Gutenberg ids are easy to get wrong and
    a wrong one is silent: id 11800 was on this list as Utilitarianism and is
    in fact 'U.S. Copyright Renewals 1950-1977', 31 MB of catalogue that
    produced 12 'precepts' reading 'What every expectant mother should know'.
    A source that cannot be checked is not a source."""
    try:
        with open(book_path(gid), encoding="utf-8", errors="replace") as fh:
            head = fh.read(4000)
    except OSError:
        return None
    m = re.search(r"^\s*Title:\s*(.+)$", head, re.M)
    if m:
        return m.group(1).strip()
    m = re.search(r"Project Gutenberg eBook of ([^\n\r]+)", head)
    return m.group(1).strip() if m else None


def title_matches(claimed, declared):
    if not declared:
        return False
    a = set(re.findall(r"[a-z]{4,}", claimed.lower()))
    b = set(re.findall(r"[a-z]{4,}", declared.lower()))
    return bool(a & b)


def verify(say=print):
    ok, bad = [], []
    for gid, title, tradition in BOOKS:
        d = declared_title(gid)
        if d is None:
            say("  %-6d %-46s NOT FETCHED" % (gid, title[:46])); continue
        if title_matches(title, d):
            ok.append(gid)
        else:
            bad.append((gid, title, d))
            say("  %-6d %-46s MISMATCH -- the file says %r" % (gid, title[:46], d[:60]))
    say("%d of %d cached file(s) are the book claimed; %d mismatch(es)"
        % (len(ok), len(ok) + len(bad), len(bad)))
    return ok, bad


def strip_boilerplate(text):
    """Gutenberg's licence header and footer are not the book."""
    a = text.find("*** START OF")
    if a >= 0:
        text = text[text.find("\n", a) + 1:]
    b = text.find("*** END OF")
    if b >= 0:
        text = text[:b]
    return text


def precepts_in(text, max_len=240, min_len=40):
    """Sentences that state a RULE about value moving between people."""
    text = re.sub(r"\s+", " ", strip_boilerplate(text))
    out = []
    for s in _SENT.split(text):
        s = VERSE.sub("", s.strip())
        if not (min_len <= len(s) <= max_len):
            continue
        if not TRANSFER.search(s) or ARGUMENT.search(s) or RITUAL.search(s):
            continue
        if PROHIBIT.search(s):
            out.append((s, "prohibition"))
        elif OBLIGE.search(s):
            out.append((s, "obligation"))
    return out


def extract(limit_per_book=400, say=print):
    os.makedirs(OUT, exist_ok=True)
    _ok, bad = verify(say=lambda *_a, **_k: None)
    skip = {gid for gid, _t, _d in bad}
    if skip:
        say("  skipping %d file(s) whose content is not the book claimed: %s"
            % (len(skip), sorted(skip)))
    seen = set()
    if os.path.exists(PRECEPTS):
        with open(PRECEPTS, encoding="utf-8") as fh:
            for line in fh:
                try:
                    seen.add(json.loads(line)["text"])
                except (ValueError, KeyError):
                    pass
    total, per = 0, []
    with open(PRECEPTS, "a", encoding="utf-8") as fh:
        for gid, title, tradition in BOOKS:
            p = book_path(gid)
            if gid in skip or not os.path.exists(p):
                per.append((title, "skipped" if gid in skip else "not fetched", 0)); continue
            with open(p, encoding="utf-8", errors="replace") as bf:
                found = precepts_in(bf.read())
            n = 0
            for s, kind in found:
                if s in seen or n >= limit_per_book:
                    continue
                seen.add(s); n += 1
                fh.write(json.dumps({"text": s, "kind": kind, "book": title,
                                     "tradition": tradition, "gutenberg": gid},
                                    ensure_ascii=False) + "\n")
            per.append((title, tradition, n)); total += n
            say("  %-52s %-16s %4d precept(s)" % (title[:52], tradition, n))
        for pmcid, title, tradition in oa_sources():                   # A208: the open-access articles
            p = os.path.join(CACHE, "oa_%s.txt" % pmcid)
            if not os.path.exists(p):
                per.append((title, "not fetched", 0)); continue
            with open(p, encoding="utf-8", errors="replace") as bf:
                found = precepts_in(bf.read())
            n = 0
            for s_, kind in found:
                if s_ in seen or n >= limit_per_book:
                    continue
                seen.add(s_); n += 1
                fh.write(json.dumps({"text": s_, "kind": kind, "book": title, "tradition": tradition, "pmcid": pmcid},
                                    ensure_ascii=False) + "\n")
            per.append((title, tradition, n)); total += n
            if n:
                say("  %-52s %-16s %4d precept(s)" % (title[:52], tradition[:16], n))
    say("%d new precept(s) -> %s" % (total, PRECEPTS))
    return total, per


def extract_own(say=print):
    """Precepts from the covenant's own documents. Same local extractor, same
    filter, so a sentence of argument in CONSTITUTION.md is dropped exactly as
    one in Leviathan is."""
    os.makedirs(OUT, exist_ok=True)
    seen = {p["text"] for p in load_precepts()}
    total = 0
    with open(PRECEPTS, "a", encoding="utf-8") as fh:
        for rel, tradition in OWN_DOCS:
            p = os.path.join(HERE, rel)
            if not os.path.exists(p):
                say("  %-32s missing" % rel); continue
            with open(p, encoding="utf-8", errors="replace") as df:
                found = precepts_in(df.read())
            n = 0
            for text, kind in found:
                if text in seen:
                    continue
                seen.add(text); n += 1
                fh.write(json.dumps({"text": text, "kind": kind, "book": rel,
                                     "tradition": tradition, "gutenberg": None},
                                    ensure_ascii=False) + "\n")
            say("  %-32s %-10s %3d precept(s)" % (rel, tradition, n))
            total += n
    say("%d precept(s) from the covenant's own documents" % total)
    return total


def load_precepts(path=PRECEPTS):
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def report(say=print):
    ps = load_precepts()
    by_t, by_k = {}, {}
    for p in ps:
        by_t[p.get("tradition", "?")] = by_t.get(p.get("tradition", "?"), 0) + 1
        by_k[p.get("kind", "?")] = by_k.get(p.get("kind", "?"), 0) + 1
    lines = ["# What the covenant has read", "",
             "Public-domain moral texts, read locally: the extraction uses no model and no",
             "network. A precept is a sentence stating a rule about conduct toward another",
             "person; argument is not a rule and is not kept. The texts themselves are never",
             "trained on -- only the transactions generated from these precepts and judged",
             "blind (covenant_distill.py) reach the ledger.", "",
             "%d precept(s) from %d book(s), %s" % (len(ps), len({p.get("book") for p in ps}),
                                                    time.strftime("%Y-%m-%d")), "",
             "| tradition | precepts |", "|---|---|"]
    for t, n in sorted(by_t.items(), key=lambda x: -x[1]):
        lines.append("| %s | %d |" % (t, n))
    lines += ["", "| kind | count |", "|---|---|"]
    for k, n in sorted(by_k.items(), key=lambda x: -x[1]):
        lines.append("| %s | %d |" % (k, n))
    os.makedirs(OUT, exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    say("\n".join(lines[6:]))
    say("\nwritten to %s" % REPORT)
    return len(ps)


# ---------------------------------------------------------------- generation
# A precept becomes two transactions: one that breaks it and one that keeps it.
# The teacher writes them, then judges them BLIND in a separate call, and only
# the pair whose blind verdict matches the intent is kept. That is the same
# discipline covenant_distill.py uses, and it is what makes a noisy extractor
# safe: a sentence that was never really a rule produces a pair the judge will
# not confirm, and it lands in ops/distill_rejected.jsonl with both answers.
# A161 (2026-09-20): MEASURED, the gate was refusing the writer's memos for
# their INFLECTIONS, not their content. "repaying a 20-unit loan", "refunding
# 15 units", "donating 12 units", "i transferred 300 from the shared account",
# "I seize control of the funds", "used the deposit money meant for sarah" all
# failed: repaying/refunding/donating/transferred/seize/used were not in the
# verb list, and "units", "$50", "300" were not money. Five nights of the study
# step read "12 precepts -> 0 kept" while 19-20 of every 24 lines were thrown
# away unread and the precepts retired. On the stored corpus the widened
# patterns pass 765 of 1,347 generated memos instead of 391, 174 of 776 study
# rows instead of 124, 997 of 1,609 seeds instead of 666 -- and still refuse
# every self-report the docstring below was written against ("I held a
# grudge", "I compared my wealth to others"), which test_f2 T3 pins both ways.
# Deception, coercion and injection memos carry no money word by nature and
# stay outside this gate; the generator path supplies those.
_MONEY = re.compile(
    r"\b(?:money|coin|coins|silver|gold|cash|fund|funds|payment|payments|pay|pays|paid|paying"
    r"|wage|wages|price|cost|debt|debts|loan|loans|deposit|account|accounts|balance|sum"
    r"|share|shares|alms|tithe|tithes|donation|donations|gift|gifts|inheritance|estate|rent"
    r"|fee|fees|tax|taxes|profit|profits|earnings|salary|stake|purse|treasure|wealth"
    r"|property|goods|land|grain|harvest|amount|owed|owe|owes|interest|usury"
    r"|ransom|dowry|bribe|escrow|invoice|receipt|ledger"
    r"|units?|dollars?|bucks|euros?|pounds|usd|eur|gbp|xrp|btc|eth|hbar|tokens?|crypto"
    r"|paycheck|payout|allowance|tips?|bills?|fare|refunds?|overpayment|savings|pension"
    r"|bonus|budget|capital|revenue|proceeds|wallet|transfer|transfers)\b"
    r"|[$€£]\s?\d"
    r"|\b\d+(?:[.,]\d+)?\s?(?:k|m)?\s?(?:units?|dollars?|bucks|euros?|usd|eur|xrp|btc|eth|coins?|tokens?)\b")
_ACT = re.compile(
    r"\b(?:re)?pa(?:y|ys|id|ying)\b|\bgiv(?:e|es|ing)\b|\bgave\b|\bsen(?:d|ds|ding|t)\b"
    r"|\btransfer(?:s|red|ring)?\b|\btak(?:e|es|ing)\b|\btook\b|\btaken\b"
    r"|\bst(?:eal|eals|ealing|ole|olen)\b|\bkeep(?:s|ing)?\b|\bkept\b|\breturn(?:s|ed|ing)?\b"
    r"|\bwithh(?:old|olds|eld|olding)\b|\blen(?:d|ds|ding|t)\b|\bborrow(?:s|ed|ing)?\b"
    r"|\bow(?:e|es|ed|ing)\b|\bbuy(?:s|ing)?\b|\bbought\b|\bsell(?:s|ing)?\b|\bsold\b"
    r"|\bcharg(?:e|es|ed|ing)\b|\brefund(?:s|ed|ing)?\b|\bcollect(?:s|ed|ing)?\b"
    r"|\bspen(?:d|ds|ding|t)\b|\bmov(?:e|es|ed|ing)\b|\bhand(?:s|ed|ing)?\b"
    r"|\bsettl(?:e|es|ed|ing)\b|\bdonat(?:e|es|ed|ing)\b|\bsplit(?:s|ting)?\b"
    r"|\bshar(?:e|es|ed|ing)\b|\bseiz(?:e|es|ed|ing)\b|\bdrain(?:s|ed|ing)?\b"
    r"|\bskim(?:s|med|ming)?\b|\bpocket(?:s|ed|ing)?\b|\bdivert(?:s|ed|ing)?\b"
    r"|\bembezzl(?:e|es|ed|ing)\b|\bus(?:e|es|ed|ing)\b|\bcover(?:s|ed|ing)?\b"
    r"|\bdeposit(?:s|ed|ing)?\b|\bwithdr(?:aw|aws|ew|awn|awing)\b|\bwir(?:e|es|ed|ing)\b"
    r"|\bremit(?:s|ted|ting)?\b|\breimburs(?:e|es|ed|ing)\b|\bcontribut(?:e|es|ed|ing)\b"
    r"|\btip(?:s|ped|ping)?\b|\bfund(?:s|ed|ing)?\b|\bcompensat(?:e|es|ed|ing)\b"
    r"|\breceiv(?:e|es|ed|ing)\b|\bearn(?:s|ed|ing)?\b|\bcash(?:ed|ing)?\b"
    r"|\bpurchas(?:e|es|ed|ing)\b")


def describes_a_transfer(message):
    """Does this line describe a transfer of value?

    MEASURED 2026-09-04, after an audit of all 716 study rows in the ledger.
    159 of them had labels that could not be defended against the gate's own
    doctrine: 97 called a violation were clean (most of them GIVING, which the
    gate says is never taking) and 62 were not transactions at all. That is 22%
    of the study corpus, which was itself half the training set, and it was
    teaching the judge that generosity is suspicious.

    The rows that failed look like this: "I ignored the economic impact of my
    decisions", "I held a grudge and refused to forgive", "I compared my wealth
    to others, feeling superior". They are first-person moral SELF-REPORTS. The
    covenant judges transfers; nobody attaches a character assessment to a
    ledger entry, so these are out of distribution for every real payload, and
    asking any judge to rule violates/clean on one produces noise whatever the
    judge.

    Two narrower filters were tried first and both were measured and dropped: a
    victim/belief/omission pattern set caught 9 of the 160 bad rows, and this
    same money-plus-act test applied to the STORED corpus separates it only
    82% to 75% -- because most of the surviving rows are not transfers either;
    they were kept because their labels were defensible, not because they were
    in distribution.

    So this is not a repair of the existing corpus. It is a gate on new intake,
    and it will cut the study path's volume hard. That is the point: volume of
    the wrong thing is how the corpus got here."""
    t = (message or "").lower()
    return bool(_MONEY.search(t)) and bool(_ACT.search(t))


def generate(limit, say=print):
    """Turn `limit` unused precepts into blind-judged transaction pairs.
    The header of this function was lost in a refactor (KNOWN_ISSUES A55); the
    body below is unchanged and the nightly's study step calls it."""
    import covenant_distill as X
    import covenant_unified_v8 as cov
    import covenant_judge_fallback as FB
    done = set()
    try:
        with open(X.VERDICTS, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                    if d.get("precept"):
                        done.add(d["precept"])
                except ValueError:
                    pass
    except OSError:
        pass
    # Prohibitions first. An obligation ("thou shalt pay him his hire") turns
    # into two honest-looking memos and the blind judge clears both, so the
    # pair adds a clean case and no violation. A prohibition is the precept
    # that actually teaches the judge what a violation looks like, and they
    # are the scarcer kind: 210 of the first 1180 extracted.
    unused = [p for p in load_precepts() if p["text"] not in done]
    # RETIRE WHAT KEEPS FAILING (2026-09-08). A precept enters `done` above only
    # when its pair was KEPT, so a precept whose pair is rejected returns to
    # this queue every night, for ever. Measured before this was written: of
    # 104 precepts ever rejected, 65 had been rejected MORE THAN ONCE and the
    # worst were on their TENTH attempt. Every one of the top offenders is
    # abstract prose -- "This principle makes the unity of experience possible
    # and borrows nothing from reason" -- which cannot become a judgeable
    # transaction memo at all, so no number of retries will ever bank it.
    #
    # It compounded because prohibitions sort first inside each tradition
    # below, so the same permanent failures sat at the HEAD of the round robin
    # and were re-served ahead of 788 precepts that had never been tried once.
    # The loop was running nightly and advancing on a shrinking fraction of its
    # own work.
    #
    # Nothing is retired on a first failure, and nothing is hidden: the count is
    # reported through `say`, because a queue that quietly shrinks is a silent
    # cap, and this file's own standard is that a dropped input gets said out
    # loud rather than discovered later.
    attempts = {}
    try:
        with open(X.REJECTED, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                t = d.get("precept")
                if t:
                    attempts[t] = attempts.get(t, 0) + 1
    except OSError:
        pass
    retired = [p for p in unused if attempts.get(p["text"], 0) >= RETIRE_AFTER]
    if retired:
        unused = [p for p in unused if attempts.get(p["text"], 0) < RETIRE_AFTER]
        say("retired %d precept(s) rejected %d+ times; %d untried precept(s) remain"
            % (len(retired), RETIRE_AFTER, len(unused)))
    # ROUND-ROBIN ACROSS TRADITIONS. In file order the first 400 precepts are
    # all from one book, so a batch -- and then a night of batches -- would be
    # one tradition's household law and nothing else. Taking one from each
    # tradition in turn means every batch is a contrast between them, which is
    # the whole reason for reading more than one. Prohibitions still come
    # first inside each tradition: an obligation yields two honest memos and
    # teaches the judge nothing about what a violation looks like.
    by_tradition = {}
    for p in unused:
        by_tradition.setdefault(p.get("tradition", "?"), []).append(p)
    # A161 (2026-09-20): and, inside each kind, precepts that NAME VALUE first.
    # 726 of the 1,184 precepts mention money, wages, alms, debt or goods; the
    # round robin was serving narrative verses ("Then thou shalt say, They be
    # thy servant Jacob's") ahead of them, and the writer answered those with
    # fragments no gate could keep. Same rule, same order between kinds; the
    # queue is only re-ordered by what a transaction memo can be written from.
    for group in by_tradition.values():
        group.sort(key=lambda p: (0 if p.get("kind") == "prohibition" else 1,
                                  0 if _MONEY.search((p.get("text") or "").lower()) else 1))
    todo, order = [], sorted(by_tradition)
    while len(todo) < limit and any(by_tradition[t] for t in order):
        for t in order:
            if by_tradition[t] and len(todo) < limit:
                todo.append(by_tradition[t].pop(0))
    if not todo:
        say("no unused precepts"); return 0, 0
    listing = "\n".join("%d. [%s, %s] %s" % (i, p["tradition"], p["kind"], p["text"])
                         for i, p in enumerate(todo))
    # A161 (2026-09-20): the intake rule below (describes_a_transfer) was
    # refusing 20 of every 24 lines the writer sent -- five nights running, 12
    # precepts became 0 kept cases and the precepts were retired unlearned.
    # The writer was never TOLD the rule. Now the prompt states exactly what
    # the filter measures, in the filter's own words.
    prompt = ("Below are %d precepts taken from public-domain moral texts. For EACH, write two "
              "first-person transaction memos for a small value-transfer ledger, 8-30 words each, "
              "concrete and modern: one that VIOLATES the precept and one that HONOURS it. If a "
              "numbered line is not really a rule about value moving between people, return null "
              "for that number instead of inventing one.\n"
              "RULE FOR EVERY MEMO, or it is discarded unread: it must name the value that moves "
              "(an amount, or a word such as money, cash, payment, wages, rent, loan, deposit, fee, "
              "debt, gift, donation, share, goods) AND the act that moves it (pay, send, give, "
              "transfer, keep, take, return, refund, lend, borrow, charge, withhold, collect). "
              "A memo about attitude, effort, time or feelings is not a transfer and will be thrown away.\n%s\n"
              "Answer ONLY JSON: {\"pairs\": [{\"n\": <number>, \"violating\": \"...\", "
              "\"honouring\": \"...\"}, ...]}" % (len(todo), listing))
    # 2026-09-12: the runner is the only teacher (no local model server).
    import covenant_github_judge as gh
    import covenant_teacher_panel as P
    writer = P.writer_for()                                   # today's writer; the PANEL judges below
    ans = gh.ask(prompt, "You write test cases for an ethics judge. JSON only.",
                 model=writer, json_only=True, timeout=900)
    raw, who = ans.get("content", ""), "github-actions/%s" % ans.get("model")
    try:
        pairs = json.loads(raw).get("pairs", [])
    except (ValueError, AttributeError):
        say("teacher (%s) returned no usable JSON" % who); return 0, 0
    cases = []
    shapeless, refused = 0, []
    for pr in pairs:
        try:
            i = int(pr.get("n"))
        except (TypeError, ValueError):
            continue
        if not (0 <= i < len(todo)):
            continue
        for key, expect in (("violating", True), ("honouring", False)):
            m = str(pr.get(key) or "").strip()
            if 3 <= len(m.split()) <= 60 and describes_a_transfer(m):
                cases.append({"message": m, "expect": expect, "precept": todo[i]})
            elif 3 <= len(m.split()) <= 60:
                shapeless += 1
                refused.append(m)
    if shapeless:
        # A161: a count nobody could act on for five nights. Show the lines.
        say("    %d line(s) refused: no transfer in them" % shapeless)
        for m in refused[:8]:
            say("      refused: %s" % m[:110])
    if not cases:
        say("teacher (%s) produced no usable pairs" % who); return 0, 0
    principles = list(cov.DIVINE_PRINCIPLES)
    rows = X.panel_rows([{"message": c["message"], "expect": c["expect"]} for c in cases], principles, writer=writer, say=say)
    verdicts = {i: (r["violates"], r["reason"]) for i, r in rows.items() if r["admitted"]}   # admitted == the intended label
    judge = "panel"
    # A PAIR IS KEPT OR DROPPED WHOLE. Measured on the first pass: 24 kept and
    # 24 rejected, and the split was not random -- the honouring half of nearly
    # every pair was confirmed and the violating half was not, because a
    # teacher asked for "a memo that violates 'pay the labourer his hire'"
    # writes something like "I will not include you in the bonus pool", which
    # an honest judge correctly calls clean. Keeping the confirmed halves alone
    # fed the ledger almost pure CLEAN, and the next candidate decided 9 of 37
    # where the model in use decided 24, so the promotion rule refused it as
    # vaguer. The rule caught the drift; this stops causing it.
    #
    # A precept teaches by CONTRAST. If the teacher cannot produce a violation
    # this judge recognises, the precept taught nothing, and its honest half is
    # not free -- it is a thumb on the scale. So both halves go in together or
    # neither does, and the ledger cannot drift toward clean by construction.
    by_precept = {}
    for i, c in enumerate(cases):
        by_precept.setdefault(c["precept"]["text"], []).append((i, c))
    kept = rejected = 0
    os.makedirs(os.path.dirname(X.VERDICTS), exist_ok=True)
    for ptext, group in by_precept.items():
        confirmed = [(i, c) for i, c in group
                     if i in verdicts and verdicts[i][0] == c["expect"]]
        whole = (len(group) == 2 and len(confirmed) == 2)
        for i, c in group:
            v, why = verdicts.get(i, (None, "the judge did not answer for this one"))
            rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "text": FB._payload_text({"message": c["message"], "origin": "organic"}),
                   "judge": judge, "precept": ptext,
                   "tradition": c["precept"]["tradition"], "book": c["precept"]["book"],
                   "reason": why}
            rec["judge"], rec["panel"] = rows[i]["judge"], rows[i]["panel"]   # the panel's provenance, kept or dropped
            if whole:
                rec["violates"] = bool(v)
                rec["source"] = "study"
                with open(X.VERDICTS, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                kept += 1
            else:
                rec["written_as"] = c["expect"]
                rec["judged"] = v
                rec["held"] = False
                rec["dropped_with_its_pair"] = True
                with open(X.REJECTED, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                rejected += 1
        say("    %s [%s] %s" % ("PAIR KEPT " if whole else "pair dropped",
                                group[0][1]["precept"]["tradition"], ptext[:88]))
    say("study: %d precept(s) -> %d case(s) kept as whole pairs, %d dropped (teacher %s)"
        % (len(todo), kept, rejected, judge))
    return kept, rejected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--fetch-oa", type=int, metavar="PER_TOPIC", default=None, help="cache open-access articles, N per topic (A208)")
    ap.add_argument("--extract", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--own", action="store_true", help="extract precepts from the covenant's own documents")
    ap.add_argument("--generate", type=int, metavar="N", help="turn N unused precepts into judged transactions")
    ap.add_argument("--limit", type=int, default=len(BOOKS))
    a = ap.parse_args()
    if a.list or not (a.fetch or a.extract or a.report or a.verify or a.generate or a.own or a.fetch_oa is not None):
        print("%d books on the reading list:" % len(BOOKS))
        for gid, title, tradition in BOOKS:
            state = "cached" if os.path.exists(book_path(gid)) else "-"
            print("  %-6d %-52s %-16s %s" % (gid, title[:52], tradition, state))
        return 0
    if a.verify:
        verify()
    if a.fetch_oa is not None:
        new, sk = fetch_oa(per_query=a.fetch_oa)
        print("open access: %d new article(s) cached, %d skipped; registry %s" % (new, sk, OA_REGISTRY))

    if a.fetch:
        for gid, title, tradition in BOOKS[:a.limit]:
            print("  %-52s %s" % (title[:52], fetch(gid, title)))
            time.sleep(1.0)                                      # be a good guest
    if a.extract:
        extract()
    if a.own:
        extract_own()
    if a.generate:
        generate(a.generate)
    if a.report:
        report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
