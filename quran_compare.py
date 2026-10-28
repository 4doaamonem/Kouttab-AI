
# quran_compare.py
# Compare an ASR transcription of a recitation against the reference ayah text
# and return the mistakes at word / letter / tashkeel level, ready for highlighting.

# Statuses per word:
#     ok              -> word and tashkeel match
#     tashkeel_error  -> same letters, different harakat
#     word_error      -> word differs (see `errors` for letter-level detail)
#     missing         -> word is in the reference but was not recited
#     extra           -> word was recited but is not in the reference


from difflib import SequenceMatcher

# ------------------------------------------------------------------ constants
HARAKAT = set("\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652")  # tanween, fatha, damma, kasra, shadda, sukun
SUKUN = "\u0652"
DAGGER_ALIF = "\u0670"

# characters that carry no information for the comparison (kept only for display)
IGNORABLE = (
    {"\u0640"}                                  # tatweel
    | {chr(c) for c in range(0x0610, 0x061B)}   # honorific signs
    | {chr(c) for c in range(0x0653, 0x0670)}   # maddah, hamza marks, ... (not harakat above)
    | {chr(c) for c in range(0x06D6, 0x06EE)}   # Quranic annotation / waqf marks
    | {"\u200c", "\u200d", "\u200f", "\u200e"}  # zero-width / direction marks
)
# harakat that appear in the 0x0653-0x066F range must not be ignored
IGNORABLE -= HARAKAT

# letter normalization used ONLY for matching (alef forms, alef maqsura)
LETTER_MAP = {"ٱ": "ا", "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}



# ------------------------------------------------------------------ parsing
def parse_units(word, ignore_sukun=True):
    """Split a word into letter units: {text, base, marks}.
    - text  : the original characters of this unit (letter + its marks) -> for rendering
    - base  : normalized letter -> for matching
    - marks : set of harakat on the letter -> for tashkeel comparison
    The dagger alif is its own unit with base 'ا', so "الرحمٰن" matches "الرحمان".
    """
    units = []
    for ch in word:
        if ch in HARAKAT:
            if units:
                units[-1]["text"] += ch
                if not (ignore_sukun and ch == SUKUN):
                    units[-1]["marks"].add(ch)
        elif ch == DAGGER_ALIF:
            units.append({"text": ch, "base": "ا", "marks": set()})
        elif ch in IGNORABLE or not ch.isalpha():
            if units:
                units[-1]["text"] += ch
        else:
            units.append({"text": ch, "base": LETTER_MAP.get(ch, ch), "marks": set()})
    return units


def key_of(units):
    return "".join(u["base"] for u in units)


def parse_text(text, ignore_sukun=True, ignore_alif=True):
    """Text -> list of (original_word, units, match_key); drops tokens with no letters (ayah numbers, signs).
    ignore_alif=True: alifs are ignored when *matching* words, because ASR spelling of long alif
    (الرحمان / الرحمن / الرحمٰن) is unreliable. Alif harakat are still compared (e.g. أَ).
    """
    out = []
    for w in text.split():
        units = parse_units(w, ignore_sukun)
        key = key_of(units)
        if ignore_alif and key.replace("ا", ""):
            key = key.replace("ا", "")
        if key:
            out.append((w, units, key))
    return out


BASMALA_TEXT = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"


# alignment helpers
def align_block(exp_keys, got_keys, min_sim=0.5):
    """Align two blocks of *different* words. Pairs similar words, the rest become missing/extra."""
    n, m = len(exp_keys), len(got_keys)
    sim = [[SequenceMatcher(None, e, g).ratio() for g in got_keys] for e in exp_keys]
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            best = max(dp[i + 1][j], dp[i][j + 1])
            if sim[i][j] >= min_sim:
                best = max(best, dp[i + 1][j + 1] + sim[i][j])
            dp[i][j] = best
    ops, i, j = [], 0, 0
    while i < n or j < m:
        if i < n and j < m and sim[i][j] >= min_sim and dp[i][j] == dp[i + 1][j + 1] + sim[i][j]:
            ops.append(("pair", i, j))
            i += 1
            j += 1
        elif i < n and (j >= m or dp[i][j] == dp[i + 1][j]):
            ops.append(("missing", i, None))
            i += 1
        else:
            ops.append(("extra", None, j))
            j += 1
    return ops


def letter_errors(exp_units, got_units):
    """Letter-level diff for a word that was recited differently."""
    e = [u["base"] for u in exp_units]
    g = [u["base"] for u in got_units]
    errors = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, e, g, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                errors.append({"type": "letter_wrong", "unit_index": i1 + k,
                               "expected": exp_units[i1 + k]["base"], "got": got_units[j1 + k]["base"]})
            for k in range(n, i2 - i1):
                errors.append({"type": "letter_missing", "unit_index": i1 + k,
                               "expected": exp_units[i1 + k]["base"]})
            for k in range(n, j2 - j1):
                errors.append({"type": "letter_extra", "before_unit_index": i1 + n,
                               "got": got_units[j1 + k]["base"]})
        elif tag == "delete":
            for k in range(i1, i2):
                errors.append({"type": "letter_missing", "unit_index": k, "expected": exp_units[k]["base"]})
        elif tag == "insert":
            for k in range(j1, j2):
                errors.append({"type": "letter_extra", "before_unit_index": i1, "got": got_units[k]["base"]})
    return errors


def tashkeel_errors(exp_units, got_units, lenient=True):
    """Same word -> compare harakat letter by letter (units are aligned on their base letters,
    so an alif spelled differently does not shift the comparison).
    lenient=True: skip letters where the ASR output has no harakat at all
    (the model often drops them, so that is not a reliable mistake)."""
    errors = []
    e = [u["base"] for u in exp_units]
    g = [u["base"] for u in got_units]
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, e, g, autojunk=False).get_opcodes():
        if tag != "equal":
            continue
        for k in range(i2 - i1):
            eu, gu = exp_units[i1 + k], got_units[j1 + k]
            if lenient and not gu["marks"]:
                continue
            if eu["marks"] != gu["marks"]:
                errors.append({"type": "tashkeel", "unit_index": i1 + k,
                               "expected": "".join(sorted(eu["marks"])),
                               "got": "".join(sorted(gu["marks"]))})
    return errors


# main api
def compare_recitation(ayah_key, reference_text, asr_text, *,
                       lenient_tashkeel=True, ignore_sukun=True, ignore_alif=True):
    exp = parse_text(reference_text, ignore_sukun, ignore_alif)
    got = parse_text(asr_text, ignore_sukun, ignore_alif)
    basmala_keys = [k for _, _, k in parse_text(BASMALA_TEXT, ignore_sukun, ignore_alif)]

    # reciter added a basmala before an ayah whose reference doesn't start with it -> drop it
    if [k for _, _, k in got[:4]] == basmala_keys and [k for _, _, k in exp[:4]] != basmala_keys:
        got = got[4:]

    exp_keys = [k for _, _, k in exp]
    got_keys = [k for _, _, k in got]

    words = []  # ordered list, expected words + extra words in their position

    def exp_entry(i, status, got_word=None, errors=None):
        return {"index": i, "expected": exp[i][0], "got": got_word, "status": status,
                "units": [u["text"] for u in exp[i][1]], "errors": errors or []}

    def extra_entry(j, after_index):
        return {"index": None, "after_index": after_index, "expected": None, "got": got[j][0],
                "status": "extra", "units": [], "errors": []}

    for tag, i1, i2, j1, j2 in SequenceMatcher(None, exp_keys, got_keys, autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                i, j = i1 + k, j1 + k
                errs = tashkeel_errors(exp[i][1], got[j][1], lenient_tashkeel)
                words.append(exp_entry(i, "tashkeel_error" if errs else "ok", got[j][0], errs))
        elif tag == "delete":
            for i in range(i1, i2):
                words.append(exp_entry(i, "missing"))
        elif tag == "insert":
            for j in range(j1, j2):
                words.append(extra_entry(j, i1 - 1))
        else:  # replace
            for op, a, b in align_block(exp_keys[i1:i2], got_keys[j1:j2]):
                if op == "pair":
                    i, j = i1 + a, j1 + b
                    words.append(exp_entry(i, "word_error", got[j][0], letter_errors(exp[i][1], got[j][1])))
                elif op == "missing":
                    words.append(exp_entry(i1 + a, "missing"))
                else:
                    words.append(extra_entry(j1 + b, i1 - 1 if not words else
                                             max((w["index"] for w in words if w["index"] is not None), default=-1)))

    counts = {}
    for w in words:
        counts[w["status"]] = counts.get(w["status"], 0) + 1
    total = len(exp)
    return {
        "ayah": ayah_key,
        "words": words,
        "summary": {
            "expected_words": total,
            "counts": counts,
            "accuracy": round(counts.get("ok", 0) / total, 3) if total else None,
        },
    }


# test
if __name__ == "__main__":
    import json

    REFERENCE = {
        "1:1": "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
        "1:2": "ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ",
    }
    tests = {
        "correct": "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
        "tashkeel (ُ instead of ِ on الله)": "بِسْمِ ٱللَّهُ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
        "word replaced": "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيلِ",
        "missing word": "بِسْمِ ٱللَّهِ ٱلرَّحِيمِ",
        "extra word": "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ مَالِكِ",
        "no tashkeel in ASR (lenient)": "بسم الله الرحمن الرحيم",
    }
    for name, asr in tests.items():
        r = compare_recitation("1:1", REFERENCE["1:1"], asr)
        print(f"--- {name}: {r['summary']}")
        for w in r["words"]:
            if w["status"] != "ok":
                print("   ", json.dumps(w, ensure_ascii=False))
