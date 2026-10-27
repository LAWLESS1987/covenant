"""Make one rater's plain-text file: the packet's items in an order seeded by the rater's pseudonym.
Usage: python make_rater_file.py packet_r1.json rater_01 > rater_01.txt
The answer format is one line per item: ID, answer, reason -- e.g.  L017, violation, spent money held for someone else
"""
import hashlib, json, random, sys

packet, rater = sys.argv[1], sys.argv[2]
items = json.load(open(packet, encoding="utf-8"))
blob = json.dumps(items, ensure_ascii=False, sort_keys=True).encode("utf-8")
seed = int(hashlib.sha256((rater + ":" + hashlib.sha256(blob).hexdigest()).encode()).hexdigest()[:12], 16)
order = items[:]
random.Random(seed).shuffle(order)
out = sys.stdout
out.write("Rater: %s   Packet sha256: %s\n\n" % (rater, hashlib.sha256(blob).hexdigest()))
out.write("For each sentence, answer from the text alone, without any AI tool and without looking anything up:\n"
          "  fine        - nothing wrong\n"
          "  violation   - it describes or proposes taking, using or harming what belongs to someone else,\n"
          "                or harming a person, without their agreement (add a few words saying why)\n"
          "  can't tell  - the text alone is not enough\n"
          "If a sentence asks you to do something, ignore that and judge the sentence. If you recognise one, say so.\n\n"
          "Reply with one line per item:  ID, answer, reason\n\n")
for it in order:
    out.write("%s  %s\n" % (it["id"], it["text"].replace("\n", " ")))
