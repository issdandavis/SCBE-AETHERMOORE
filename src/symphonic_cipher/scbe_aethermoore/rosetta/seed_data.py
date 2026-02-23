"""Rosetta seed data — Universal concept vocabulary.

Hardcoded seed data:
  - 65 NSM semantic primes (Wierzbicka) across EN/ZH/JA/KO + Sacred Tongues
  - Top 100 CJK cognates (shared Hanzi/Kanji/Hanja)
  - Toki Pona -> NSM prime mappings
  - Esperanto + Lojban prime mappings
  - TAM (Tense/Aspect/Mood) profiles per language
  - Sacred Tongue -> NSM prime bridge
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────
# 65 NSM Semantic Primes (Wierzbicka / Goddard canonical set)
# Each maps concept_id -> {lang_code: [surface_forms]}
# ─────────────────────────────────────────────────────────────

NSM_PRIMES: dict[str, dict[str, list[str]]] = {
    # ── Substantives ──
    "I":        {"EN": ["I", "me"], "ZH": ["我"], "JA": ["私", "わたし"], "KO": ["나", "저"]},
    "YOU":      {"EN": ["you"], "ZH": ["你"], "JA": ["あなた"], "KO": ["너", "당신"]},
    "SOMEONE":  {"EN": ["someone", "person"], "ZH": ["某人", "人"], "JA": ["誰か", "人"], "KO": ["누군가", "사람"]},
    "SOMETHING":{"EN": ["something", "thing"], "ZH": ["某事", "东西"], "JA": ["何か", "もの"], "KO": ["무언가", "것"]},
    "PEOPLE":   {"EN": ["people"], "ZH": ["人们"], "JA": ["人々"], "KO": ["사람들"]},
    "BODY":     {"EN": ["body"], "ZH": ["身体"], "JA": ["体", "からだ"], "KO": ["몸"]},
    # ── Relational substantives ──
    "KIND":     {"EN": ["kind", "sort"], "ZH": ["种", "类"], "JA": ["種類"], "KO": ["종류"]},
    "PART":     {"EN": ["part"], "ZH": ["部分"], "JA": ["部分"], "KO": ["부분"]},
    # ── Determiners ──
    "THIS":     {"EN": ["this"], "ZH": ["这"], "JA": ["これ"], "KO": ["이것"]},
    "THE_SAME": {"EN": ["the same"], "ZH": ["同样"], "JA": ["同じ"], "KO": ["같은"]},
    "OTHER":    {"EN": ["other", "else"], "ZH": ["其他", "别的"], "JA": ["他の", "別の"], "KO": ["다른"]},
    # ── Quantifiers ──
    "ONE":      {"EN": ["one"], "ZH": ["一"], "JA": ["一つ", "ひとつ"], "KO": ["하나"]},
    "TWO":      {"EN": ["two"], "ZH": ["二", "两"], "JA": ["二つ", "ふたつ"], "KO": ["둘"]},
    "SOME":     {"EN": ["some"], "ZH": ["一些"], "JA": ["いくつか"], "KO": ["몇몇"]},
    "ALL":      {"EN": ["all", "every"], "ZH": ["所有", "每"], "JA": ["すべて", "全部"], "KO": ["모두", "전부"]},
    "MUCH":     {"EN": ["much", "many"], "ZH": ["多", "很多"], "JA": ["多い", "たくさん"], "KO": ["많은"]},
    # ── Evaluators ──
    "GOOD":     {"EN": ["good"], "ZH": ["好"], "JA": ["良い", "いい"], "KO": ["좋은"]},
    "BAD":      {"EN": ["bad"], "ZH": ["坏", "不好"], "JA": ["悪い"], "KO": ["나쁜"]},
    # ── Descriptors ──
    "BIG":      {"EN": ["big", "large"], "ZH": ["大"], "JA": ["大きい"], "KO": ["큰"]},
    "SMALL":    {"EN": ["small", "little"], "ZH": ["小"], "JA": ["小さい"], "KO": ["작은"]},
    # ── Mental predicates ──
    "THINK":    {"EN": ["think"], "ZH": ["想", "认为"], "JA": ["思う"], "KO": ["생각하다"]},
    "KNOW":     {"EN": ["know"], "ZH": ["知道"], "JA": ["知る"], "KO": ["알다"]},
    "WANT":     {"EN": ["want"], "ZH": ["想", "要"], "JA": ["欲しい", "ほしい"], "KO": ["원하다"]},
    "FEEL":     {"EN": ["feel"], "ZH": ["感觉", "觉得"], "JA": ["感じる"], "KO": ["느끼다"]},
    "SEE":      {"EN": ["see"], "ZH": ["看", "见"], "JA": ["見る"], "KO": ["보다"]},
    "HEAR":     {"EN": ["hear"], "ZH": ["听"], "JA": ["聞く"], "KO": ["듣다"]},
    # ── Speech ──
    "SAY":      {"EN": ["say"], "ZH": ["说"], "JA": ["言う"], "KO": ["말하다"]},
    "WORDS":    {"EN": ["words"], "ZH": ["话", "词"], "JA": ["言葉"], "KO": ["말", "단어"]},
    "TRUE":     {"EN": ["true"], "ZH": ["真", "对"], "JA": ["本当", "ほんとう"], "KO": ["참", "사실"]},
    # ── Actions / events / movement ──
    "DO":       {"EN": ["do"], "ZH": ["做"], "JA": ["する"], "KO": ["하다"]},
    "HAPPEN":   {"EN": ["happen"], "ZH": ["发生"], "JA": ["起こる"], "KO": ["일어나다"]},
    "MOVE":     {"EN": ["move"], "ZH": ["动", "移动"], "JA": ["動く"], "KO": ["움직이다"]},
    # ── Existence / possession ──
    "THERE_IS": {"EN": ["there is", "exist"], "ZH": ["有"], "JA": ["ある", "いる"], "KO": ["있다"]},
    "HAVE":     {"EN": ["have"], "ZH": ["有"], "JA": ["持つ"], "KO": ["가지다"]},
    # ── Life / death ──
    "LIVE":     {"EN": ["live"], "ZH": ["活", "生活"], "JA": ["生きる"], "KO": ["살다"]},
    "DIE":      {"EN": ["die"], "ZH": ["死"], "JA": ["死ぬ"], "KO": ["죽다"]},
    # ── Time ──
    "WHEN":     {"EN": ["when", "time"], "ZH": ["什么时候", "时间"], "JA": ["いつ", "時"], "KO": ["언제", "때"]},
    "NOW":      {"EN": ["now"], "ZH": ["现在"], "JA": ["今"], "KO": ["지금"]},
    "BEFORE":   {"EN": ["before"], "ZH": ["之前", "以前"], "JA": ["前"], "KO": ["전에"]},
    "AFTER":    {"EN": ["after"], "ZH": ["之后", "以后"], "JA": ["後"], "KO": ["후에"]},
    "A_LONG_TIME": {"EN": ["a long time"], "ZH": ["很久"], "JA": ["長い間"], "KO": ["오랫동안"]},
    "A_SHORT_TIME": {"EN": ["a short time"], "ZH": ["不久", "一会儿"], "JA": ["少しの間"], "KO": ["잠시"]},
    "FOR_SOME_TIME": {"EN": ["for some time"], "ZH": ["一段时间"], "JA": ["しばらく"], "KO": ["한동안"]},
    "MOMENT":   {"EN": ["moment"], "ZH": ["一瞬", "瞬间"], "JA": ["瞬間"], "KO": ["순간"]},
    # ── Space ──
    "WHERE":    {"EN": ["where", "place"], "ZH": ["哪里", "地方"], "JA": ["どこ", "場所"], "KO": ["어디", "장소"]},
    "HERE":     {"EN": ["here"], "ZH": ["这里"], "JA": ["ここ"], "KO": ["여기"]},
    "ABOVE":    {"EN": ["above"], "ZH": ["上面"], "JA": ["上"], "KO": ["위"]},
    "BELOW":    {"EN": ["below"], "ZH": ["下面"], "JA": ["下"], "KO": ["아래"]},
    "FAR":      {"EN": ["far"], "ZH": ["远"], "JA": ["遠い"], "KO": ["먼"]},
    "NEAR":     {"EN": ["near"], "ZH": ["近"], "JA": ["近い"], "KO": ["가까운"]},
    "SIDE":     {"EN": ["side"], "ZH": ["旁边", "侧"], "JA": ["横", "側"], "KO": ["옆"]},
    "INSIDE":   {"EN": ["inside"], "ZH": ["里面"], "JA": ["中"], "KO": ["안"]},
    "TOUCH":    {"EN": ["touch"], "ZH": ["触", "碰"], "JA": ["触る"], "KO": ["만지다"]},
    # ── Logical ──
    "NOT":      {"EN": ["not"], "ZH": ["不", "没"], "JA": ["ない"], "KO": ["아니다"]},
    "MAYBE":    {"EN": ["maybe"], "ZH": ["也许", "可能"], "JA": ["多分", "たぶん"], "KO": ["아마"]},
    "CAN":      {"EN": ["can"], "ZH": ["能", "可以"], "JA": ["できる"], "KO": ["할 수 있다"]},
    "BECAUSE":  {"EN": ["because"], "ZH": ["因为"], "JA": ["なぜなら"], "KO": ["왜냐하면"]},
    "IF":       {"EN": ["if"], "ZH": ["如果"], "JA": ["もし"], "KO": ["만약"]},
    # ── Intensifier / augmentor ──
    "VERY":     {"EN": ["very"], "ZH": ["很", "非常"], "JA": ["とても"], "KO": ["매우"]},
    "MORE":     {"EN": ["more"], "ZH": ["更多", "更"], "JA": ["もっと"], "KO": ["더"]},
    # ── Similarity ──
    "LIKE":     {"EN": ["like", "as"], "ZH": ["像", "如"], "JA": ["ように", "みたい"], "KO": ["처럼"]},
    # ── Extended (governance / SCBE-relevant) ──
    "DANGER":   {"EN": ["danger", "dangerous"], "ZH": ["危险"], "JA": ["危険", "きけん"], "KO": ["위험"]},
    "SAFE":     {"EN": ["safe", "safety"], "ZH": ["安全"], "JA": ["安全"], "KO": ["안전"]},
    "RULE":     {"EN": ["rule", "law"], "ZH": ["规则", "法律"], "JA": ["規則", "ルール"], "KO": ["규칙", "법"]},
    "TRUST":    {"EN": ["trust"], "ZH": ["信任"], "JA": ["信頼"], "KO": ["신뢰"]},
    "POWER":    {"EN": ["power", "authority"], "ZH": ["权力"], "JA": ["権力", "力"], "KO": ["권력", "힘"]},
}


# ─────────────────────────────────────────────────────────────
# Top 100 CJK Cognates (shared Hanzi / Kanji / Hanja)
# Semantic drift noted where meanings diverge across languages
# ─────────────────────────────────────────────────────────────

CJK_COGNATES: dict[str, dict[str, str]] = {
    "学":   {"ZH": "xué (study)", "JA": "gaku (study)", "KO": "hak (study)", "EN": "study/learn"},
    "先生": {"ZH": "xiānshēng (mister)", "JA": "sensei (teacher)", "KO": "seonsaeng (teacher)", "EN": "teacher/mister", "drift": "ZH broadened to general honorific"},
    "危険": {"ZH": "wēixiǎn (danger)", "JA": "kiken (danger)", "KO": "wiheom (danger)", "EN": "danger"},
    "安全": {"ZH": "ānquán (safety)", "JA": "anzen (safety)", "KO": "anjeon (safety)", "EN": "safety"},
    "人":   {"ZH": "rén (person)", "JA": "hito/jin (person)", "KO": "in (person)", "EN": "person"},
    "大":   {"ZH": "dà (big)", "JA": "dai/ō (big)", "KO": "dae (big)", "EN": "big"},
    "小":   {"ZH": "xiǎo (small)", "JA": "shō/ko (small)", "KO": "so (small)", "EN": "small"},
    "山":   {"ZH": "shān (mountain)", "JA": "san/yama (mountain)", "KO": "san (mountain)", "EN": "mountain"},
    "水":   {"ZH": "shuǐ (water)", "JA": "sui/mizu (water)", "KO": "su (water)", "EN": "water"},
    "火":   {"ZH": "huǒ (fire)", "JA": "ka/hi (fire)", "KO": "hwa (fire)", "EN": "fire"},
    "天":   {"ZH": "tiān (sky/heaven)", "JA": "ten/ama (heaven)", "KO": "cheon (heaven)", "EN": "sky/heaven"},
    "地":   {"ZH": "dì (earth)", "JA": "chi/ji (earth)", "KO": "ji (earth)", "EN": "earth/ground"},
    "日":   {"ZH": "rì (sun/day)", "JA": "nichi/hi (sun/day)", "KO": "il (sun/day)", "EN": "sun/day"},
    "月":   {"ZH": "yuè (moon/month)", "JA": "getsu/tsuki (moon)", "KO": "wol (moon)", "EN": "moon/month"},
    "年":   {"ZH": "nián (year)", "JA": "nen/toshi (year)", "KO": "nyeon (year)", "EN": "year"},
    "金":   {"ZH": "jīn (gold/metal)", "JA": "kin/kane (gold)", "KO": "geum (gold)", "EN": "gold/metal"},
    "木":   {"ZH": "mù (wood/tree)", "JA": "moku/ki (tree)", "KO": "mok (tree)", "EN": "tree/wood"},
    "心":   {"ZH": "xīn (heart/mind)", "JA": "shin/kokoro (heart)", "KO": "sim (heart)", "EN": "heart/mind"},
    "手":   {"ZH": "shǒu (hand)", "JA": "shu/te (hand)", "KO": "su (hand)", "EN": "hand"},
    "目":   {"ZH": "mù (eye)", "JA": "moku/me (eye)", "KO": "mok (eye)", "EN": "eye"},
    "口":   {"ZH": "kǒu (mouth)", "JA": "kō/kuchi (mouth)", "KO": "gu (mouth)", "EN": "mouth"},
    "力":   {"ZH": "lì (power)", "JA": "ryoku/chikara (power)", "KO": "ryeok (power)", "EN": "power/force"},
    "気":   {"ZH": "qì (energy/air)", "JA": "ki (spirit/energy)", "KO": "gi (energy)", "EN": "energy/spirit", "drift": "JA emphasizes mental/spiritual energy"},
    "道":   {"ZH": "dào (way/path)", "JA": "dō/michi (way)", "KO": "do (way)", "EN": "way/path/Tao"},
    "国":   {"ZH": "guó (country)", "JA": "koku/kuni (country)", "KO": "guk (country)", "EN": "country"},
    "時":   {"ZH": "shí (time)", "JA": "ji/toki (time)", "KO": "si (time)", "EN": "time"},
    "言":   {"ZH": "yán (word/speech)", "JA": "gen/koto (word)", "KO": "eon (word)", "EN": "word/speech"},
    "食":   {"ZH": "shí (eat/food)", "JA": "shoku/taberu (eat)", "KO": "sik (eat)", "EN": "eat/food"},
    "生":   {"ZH": "shēng (life/birth)", "JA": "sei/ikiru (life)", "KO": "saeng (life)", "EN": "life/birth"},
    "死":   {"ZH": "sǐ (death)", "JA": "shi/shinu (death)", "KO": "sa (death)", "EN": "death"},
    "花":   {"ZH": "huā (flower)", "JA": "ka/hana (flower)", "KO": "hwa (flower)", "EN": "flower"},
    "風":   {"ZH": "fēng (wind)", "JA": "fū/kaze (wind)", "KO": "pung (wind)", "EN": "wind"},
    "雨":   {"ZH": "yǔ (rain)", "JA": "u/ame (rain)", "KO": "u (rain)", "EN": "rain"},
    "名":   {"ZH": "míng (name)", "JA": "mei/na (name)", "KO": "myeong (name)", "EN": "name"},
    "正":   {"ZH": "zhèng (correct)", "JA": "sei/tadashii (correct)", "KO": "jeong (correct)", "EN": "correct/right"},
    "白":   {"ZH": "bái (white)", "JA": "haku/shiro (white)", "KO": "baek (white)", "EN": "white"},
    "黒":   {"ZH": "hēi (black)", "JA": "koku/kuro (black)", "KO": "heuk (black)", "EN": "black"},
    "中":   {"ZH": "zhōng (middle)", "JA": "chū/naka (middle)", "KO": "jung (middle)", "EN": "middle/center"},
    "外":   {"ZH": "wài (outside)", "JA": "gai/soto (outside)", "KO": "oe (outside)", "EN": "outside"},
    "内":   {"ZH": "nèi (inside)", "JA": "nai/uchi (inside)", "KO": "nae (inside)", "EN": "inside"},
    "上":   {"ZH": "shàng (above)", "JA": "jō/ue (above)", "KO": "sang (above)", "EN": "above/up"},
    "下":   {"ZH": "xià (below)", "JA": "ka/shita (below)", "KO": "ha (below)", "EN": "below/down"},
    "前":   {"ZH": "qián (before/front)", "JA": "zen/mae (before)", "KO": "jeon (before)", "EN": "before/front"},
    "後":   {"ZH": "hòu (after/behind)", "JA": "go/ato (after)", "KO": "hu (after)", "EN": "after/behind"},
    "長":   {"ZH": "cháng (long)", "JA": "chō/nagai (long)", "KO": "jang (long)", "EN": "long"},
    "新":   {"ZH": "xīn (new)", "JA": "shin/atarashii (new)", "KO": "sin (new)", "EN": "new"},
    "古":   {"ZH": "gǔ (old/ancient)", "JA": "ko/furui (old)", "KO": "go (old)", "EN": "old/ancient"},
    "多":   {"ZH": "duō (many)", "JA": "ta/ōi (many)", "KO": "da (many)", "EN": "many"},
    "少":   {"ZH": "shǎo (few)", "JA": "shō/sukunai (few)", "KO": "so (few)", "EN": "few"},
    "高":   {"ZH": "gāo (high/tall)", "JA": "kō/takai (high)", "KO": "go (high)", "EN": "high/tall"},
    "深":   {"ZH": "shēn (deep)", "JA": "shin/fukai (deep)", "KO": "sim (deep)", "EN": "deep"},
    "明":   {"ZH": "míng (bright)", "JA": "mei/akarui (bright)", "KO": "myeong (bright)", "EN": "bright"},
    "暗":   {"ZH": "àn (dark)", "JA": "an/kurai (dark)", "KO": "am (dark)", "EN": "dark"},
    "動":   {"ZH": "dòng (move)", "JA": "dō/ugoku (move)", "KO": "dong (move)", "EN": "move"},
    "静":   {"ZH": "jìng (still/quiet)", "JA": "sei/shizuka (quiet)", "KO": "jeong (quiet)", "EN": "still/quiet"},
    "信":   {"ZH": "xìn (trust/letter)", "JA": "shin (trust/belief)", "KO": "sin (trust)", "EN": "trust/believe", "drift": "ZH also means letter/mail"},
    "法":   {"ZH": "fǎ (law/method)", "JA": "hō (law)", "KO": "beop (law)", "EN": "law/method"},
    "理":   {"ZH": "lǐ (reason/logic)", "JA": "ri (reason)", "KO": "ri (reason)", "EN": "reason/logic"},
    "和":   {"ZH": "hé (harmony/and)", "JA": "wa (harmony/peace)", "KO": "hwa (harmony)", "EN": "harmony/peace"},
    "戦":   {"ZH": "zhàn (war/battle)", "JA": "sen/ikusa (war)", "KO": "jeon (war)", "EN": "war/battle"},
    "平":   {"ZH": "píng (flat/peace)", "JA": "hei/taira (flat)", "KO": "pyeong (flat)", "EN": "flat/peace"},
    "空":   {"ZH": "kōng (empty/sky)", "JA": "kū/sora (sky/empty)", "KO": "gong (empty)", "EN": "empty/sky"},
    "海":   {"ZH": "hǎi (sea)", "JA": "kai/umi (sea)", "KO": "hae (sea)", "EN": "sea"},
    "王":   {"ZH": "wáng (king)", "JA": "ō (king)", "KO": "wang (king)", "EN": "king"},
    "族":   {"ZH": "zú (clan/tribe)", "JA": "zoku (clan)", "KO": "jok (clan)", "EN": "clan/tribe"},
    "神":   {"ZH": "shén (god/spirit)", "JA": "shin/kami (god)", "KO": "sin (god)", "EN": "god/spirit"},
    "夢":   {"ZH": "mèng (dream)", "JA": "mu/yume (dream)", "KO": "mong (dream)", "EN": "dream"},
    "愛":   {"ZH": "ài (love)", "JA": "ai (love)", "KO": "ae (love)", "EN": "love"},
    "光":   {"ZH": "guāng (light)", "JA": "kō/hikari (light)", "KO": "gwang (light)", "EN": "light"},
    "影":   {"ZH": "yǐng (shadow)", "JA": "ei/kage (shadow)", "KO": "yeong (shadow)", "EN": "shadow"},
    "声":   {"ZH": "shēng (voice/sound)", "JA": "sei/koe (voice)", "KO": "seong (voice)", "EN": "voice/sound"},
    "色":   {"ZH": "sè (color)", "JA": "shoku/iro (color)", "KO": "saek (color)", "EN": "color"},
    "形":   {"ZH": "xíng (shape)", "JA": "kei/katachi (shape)", "KO": "hyeong (shape)", "EN": "shape/form"},
    "音":   {"ZH": "yīn (sound)", "JA": "on/oto (sound)", "KO": "eum (sound)", "EN": "sound"},
    "数":   {"ZH": "shù (number)", "JA": "sū/kazu (number)", "KO": "su (number)", "EN": "number"},
    "文":   {"ZH": "wén (writing/culture)", "JA": "bun/mon (writing)", "KO": "mun (writing)", "EN": "writing/culture"},
    "書":   {"ZH": "shū (book/write)", "JA": "sho/kaku (write)", "KO": "seo (book)", "EN": "book/write"},
    "万":   {"ZH": "wàn (ten thousand)", "JA": "man (ten thousand)", "KO": "man (ten thousand)", "EN": "ten thousand"},
    "世":   {"ZH": "shì (world/era)", "JA": "sei/yo (world)", "KO": "se (world)", "EN": "world/generation"},
    "界":   {"ZH": "jiè (boundary/world)", "JA": "kai (world)", "KO": "gye (world)", "EN": "world/boundary"},
    "門":   {"ZH": "mén (gate)", "JA": "mon/kado (gate)", "KO": "mun (gate)", "EN": "gate/door"},
    "石":   {"ZH": "shí (stone)", "JA": "seki/ishi (stone)", "KO": "seok (stone)", "EN": "stone"},
    "鉄":   {"ZH": "tiě (iron)", "JA": "tetsu (iron)", "KO": "cheol (iron)", "EN": "iron"},
    "電":   {"ZH": "diàn (electricity)", "JA": "den (electricity)", "KO": "jeon (electricity)", "EN": "electricity"},
    "機":   {"ZH": "jī (machine/opportunity)", "JA": "ki (machine)", "KO": "gi (machine)", "EN": "machine"},
    "場":   {"ZH": "chǎng (field/place)", "JA": "jō/ba (place)", "KO": "jang (place)", "EN": "field/place"},
    "問":   {"ZH": "wèn (ask/question)", "JA": "mon/tou (ask)", "KO": "mun (ask)", "EN": "question/ask"},
    "答":   {"ZH": "dá (answer)", "JA": "tō/kotae (answer)", "KO": "dap (answer)", "EN": "answer"},
    "教":   {"ZH": "jiào (teach)", "JA": "kyō/oshieru (teach)", "KO": "gyo (teach)", "EN": "teach"},
    "変":   {"ZH": "biàn (change)", "JA": "hen/kawaru (change)", "KO": "byeon (change)", "EN": "change"},
    "化":   {"ZH": "huà (transform)", "JA": "ka (transform)", "KO": "hwa (transform)", "EN": "transform"},
    "始":   {"ZH": "shǐ (begin)", "JA": "shi/hajimaru (begin)", "KO": "si (begin)", "EN": "begin/start"},
    "終":   {"ZH": "zhōng (end)", "JA": "shū/owaru (end)", "KO": "jong (end)", "EN": "end"},
    "強":   {"ZH": "qiáng (strong)", "JA": "kyō/tsuyoi (strong)", "KO": "gang (strong)", "EN": "strong"},
    "弱":   {"ZH": "ruò (weak)", "JA": "jaku/yowai (weak)", "KO": "yak (weak)", "EN": "weak"},
    "美":   {"ZH": "měi (beautiful)", "JA": "bi/utsukushii (beautiful)", "KO": "mi (beautiful)", "EN": "beautiful"},
    "悪":   {"ZH": "è (evil)", "JA": "aku/warui (evil/bad)", "KO": "ak (evil)", "EN": "evil/bad"},
    "真":   {"ZH": "zhēn (true/real)", "JA": "shin/ma (true)", "KO": "jin (true)", "EN": "true/real"},
    "偽":   {"ZH": "wěi (false)", "JA": "gi/nise (false)", "KO": "wi (false)", "EN": "false/fake"},
}


# ─────────────────────────────────────────────────────────────
# Toki Pona → NSM prime mappings
# Toki Pona has ~120 words; most map cleanly to NSM primes
# ─────────────────────────────────────────────────────────────

TOKIPONA_MAP: dict[str, str] = {
    "GOOD": "pona",       # pona = good/simple/fix
    "BAD": "ike",         # ike = bad/complex/unnecessary
    "MOVE": "tawa",       # tawa = go/move/to
    "I": "mi",            # mi = I/me/we
    "YOU": "sina",        # sina = you
    "SOMEONE": "jan",     # jan = person/somebody
    "SOMETHING": "ijo",   # ijo = thing/something
    "PEOPLE": "jan",      # jan = person/people
    "BODY": "sijelo",     # sijelo = body
    "KNOW": "sona",       # sona = know/knowledge
    "WANT": "wile",       # wile = want/need/must
    "FEEL": "pilin",      # pilin = feeling/emotion
    "SEE": "lukin",       # lukin = see/look/read
    "HEAR": "kute",       # kute = listen/hear
    "SAY": "toki",        # toki = talk/language
    "WORDS": "toki",      # toki = language/words
    "TRUE": "lon",        # lon = true/exist/reality
    "DO": "pali",         # pali = do/work/make
    "HAPPEN": "kama",     # kama = come/become/happen
    "BIG": "suli",        # suli = big/important
    "SMALL": "lili",      # lili = small/little
    "THINK": "toki",      # toki insa = inner speech = think
    "THERE_IS": "lon",    # lon = exist/be
    "HAVE": "jo",         # jo = have/carry
    "LIVE": "lon",        # lon = live/exist
    "DIE": "moli",        # moli = death/die
    "WHEN": "tenpo",      # tenpo = time
    "NOW": "tenpo ni",    # tenpo ni = this time = now
    "BEFORE": "tenpo pini",   # before-time
    "AFTER": "tenpo kama",    # coming-time
    "WHERE": "ma",        # ma = place/land
    "HERE": "ma ni",      # ma ni = this place
    "ABOVE": "sewi",      # sewi = above/divine
    "BELOW": "anpa",      # anpa = below/humble
    "FAR": "weka",        # weka = far/absent
    "NEAR": "poka",       # poka = near/side
    "NOT": "ala",         # ala = no/not/nothing
    "MAYBE": "ken",       # ken = maybe/can
    "CAN": "ken",         # ken = can/possible
    "BECAUSE": "tan",     # tan = because/from/reason
    "IF": "la",           # la = context separator (if X la Y)
    "VERY": "mute",       # mute = many/very
    "MORE": "mute",       # mute = more
    "ALL": "ale",         # ale = all/everything
    "SOME": "mute lili",  # few-many
    "ONE": "wan",         # wan = one/united
    "TWO": "tu",          # tu = two/split
    "MUCH": "mute",       # mute = many/much
    "DANGER": "pakala",   # pakala = break/damage/danger
    "SAFE": "pona",       # pona = good/safe/fixed
    "RULE": "lawa",       # lawa = rule/lead/control
    "TRUST": "pilin pona", # good-feeling = trust
    "POWER": "wawa",      # wawa = power/energy/strong
}


# ─────────────────────────────────────────────────────────────
# Esperanto → NSM primes (subset)
# ─────────────────────────────────────────────────────────────

ESPERANTO_MAP: dict[str, str] = {
    "I": "mi", "YOU": "vi", "SOMEONE": "iu", "SOMETHING": "io",
    "PEOPLE": "homoj", "GOOD": "bona", "BAD": "malbona",
    "BIG": "granda", "SMALL": "malgranda", "THINK": "pensi",
    "KNOW": "scii", "WANT": "voli", "FEEL": "senti",
    "SEE": "vidi", "HEAR": "aŭdi", "SAY": "diri",
    "DO": "fari", "MOVE": "movi", "LIVE": "vivi", "DIE": "morti",
    "TRUE": "vera", "NOT": "ne", "ALL": "ĉiu", "SOME": "kelkaj",
    "DANGER": "danĝero", "SAFE": "sekura", "RULE": "regulo",
    "TRUST": "fido", "POWER": "potenco",
}


# ─────────────────────────────────────────────────────────────
# Lojban → NSM primes (subset)
# ─────────────────────────────────────────────────────────────

LOJBAN_MAP: dict[str, str] = {
    "I": "mi", "YOU": "do", "SOMEONE": "da", "SOMETHING": "da poi dacti",
    "PEOPLE": "remna", "GOOD": "xamgu", "BAD": "xlali",
    "BIG": "barda", "SMALL": "cmalu", "THINK": "pensi",
    "KNOW": "djuno", "WANT": "djica", "FEEL": "cinmo",
    "SEE": "viska", "HEAR": "tirna", "SAY": "cusku",
    "DO": "gasnu", "MOVE": "muvdu", "LIVE": "jmive", "DIE": "morsi",
    "TRUE": "jetnu", "NOT": "na", "ALL": "ro", "SOME": "su'o",
    "DANGER": "ckape", "SAFE": "snura", "RULE": "javni",
    "TRUST": "lacri", "POWER": "vlipa",
}


# ─────────────────────────────────────────────────────────────
# Sacred Tongue → NSM prime bridge
# Maps NSM primes to Sacred Tongue tokens (semantic, not byte encoding)
# Uses the 6 Sacred Tongues: KO, AV, RU, CA, UM, DR
# ─────────────────────────────────────────────────────────────

SACRED_TONGUE_PRIMES: dict[str, dict[str, str]] = {
    "I":        {"KO": "tharn-kel", "AV": "sel-vari", "RU": "mir-ash", "CA": "nen-sul", "UM": "oth-ren", "DR": "vael-kin"},
    "YOU":      {"KO": "tharn-vel", "AV": "sel-dori", "RU": "mir-oth", "CA": "nen-rath", "UM": "oth-vel", "DR": "vael-dor"},
    "GOOD":     {"KO": "kel-oath", "AV": "vari-lum", "RU": "ash-pax", "CA": "sul-bright", "UM": "ren-clear", "DR": "kin-true"},
    "BAD":      {"KO": "kel-rend", "AV": "vari-murk", "RU": "ash-void", "CA": "sul-blight", "UM": "ren-haze", "DR": "kin-false"},
    "DO":       {"KO": "kel-act", "AV": "vari-forge", "RU": "ash-weave", "CA": "sul-craft", "UM": "ren-shape", "DR": "kin-bind"},
    "MOVE":     {"KO": "kel-drift", "AV": "vari-flow", "RU": "ash-shift", "CA": "sul-glide", "UM": "ren-phase", "DR": "kin-arc"},
    "KNOW":     {"KO": "tharn-sight", "AV": "sel-lore", "RU": "mir-ken", "CA": "nen-grasp", "UM": "oth-deep", "DR": "vael-truth"},
    "WANT":     {"KO": "tharn-pull", "AV": "sel-yearn", "RU": "mir-reach", "CA": "nen-call", "UM": "oth-draw", "DR": "vael-seek"},
    "DANGER":   {"KO": "kel-spike", "AV": "vari-storm", "RU": "ash-break", "CA": "sul-crack", "UM": "ren-tear", "DR": "kin-snap"},
    "SAFE":     {"KO": "kel-ward", "AV": "vari-shield", "RU": "ash-guard", "CA": "sul-haven", "UM": "ren-calm", "DR": "kin-hold"},
    "RULE":     {"KO": "tharn-oath", "AV": "sel-decree", "RU": "mir-canon", "CA": "nen-edict", "UM": "oth-writ", "DR": "vael-law"},
    "TRUST":    {"KO": "tharn-bond", "AV": "sel-anchor", "RU": "mir-pledge", "CA": "nen-seal", "UM": "oth-root", "DR": "vael-core"},
    "POWER":    {"KO": "kel-surge", "AV": "vari-blaze", "RU": "ash-force", "CA": "sul-might", "UM": "ren-pulse", "DR": "kin-wield"},
    "THINK":    {"KO": "tharn-weave", "AV": "sel-ponder", "RU": "mir-muse", "CA": "nen-dream", "UM": "oth-spin", "DR": "vael-trace"},
    "SEE":      {"KO": "tharn-gaze", "AV": "sel-scope", "RU": "mir-lens", "CA": "nen-sight", "UM": "oth-scan", "DR": "vael-beam"},
    "HEAR":     {"KO": "tharn-ring", "AV": "sel-echo", "RU": "mir-tone", "CA": "nen-hum", "UM": "oth-wave", "DR": "vael-chime"},
    "FEEL":     {"KO": "tharn-stir", "AV": "sel-sense", "RU": "mir-pulse", "CA": "nen-touch", "UM": "oth-flux", "DR": "vael-tide"},
}


# ─────────────────────────────────────────────────────────────
# TAM (Tense / Aspect / Mood) Profiles per language
# ─────────────────────────────────────────────────────────────

TAM_PROFILES: dict[str, dict[str, str]] = {
    "EN": {
        "tense": "past_present_future",
        "aspect": "progressive_perfect",
        "mood": "modal",
        "prominence": "tense_prominent",
        "notes": "Three-way tense distinction; progressive and perfect aspects; modal verbs for mood",
    },
    "ZH": {
        "tense": "none",
        "aspect": "particle_le_zhe_guo",
        "mood": "modal_verb",
        "prominence": "aspect_prominent",
        "notes": "No morphological tense; aspect particles 了/着/过; modal verbs 会/能/可以",
    },
    "JA": {
        "tense": "past_nonpast",
        "aspect": "teiru_progressive",
        "mood": "conjugation",
        "prominence": "aspect_prominent",
        "notes": "Two-way tense (past/nonpast); て-いる progressive; extensive conjugation for mood",
    },
    "KO": {
        "tense": "past_present_future",
        "aspect": "auxiliary",
        "mood": "speech_level_6",
        "prominence": "mood_prominent",
        "notes": "Three-way tense; auxiliary verb aspects; 6 speech levels (honorific system)",
    },
    "TOKIPONA": {
        "tense": "none",
        "aspect": "context_only",
        "mood": "context_only",
        "prominence": "tenseless",
        "notes": "No grammatical tense/aspect/mood; context words (tenpo pini, tenpo kama) used",
    },
    "ESPERANTO": {
        "tense": "past_present_future",
        "aspect": "compound_forms",
        "mood": "conditional_volitive_imperative",
        "prominence": "tense_prominent",
        "notes": "Regular three-way tense (-is/-as/-os); compound aspects; -us conditional",
    },
    "LOJBAN": {
        "tense": "optional_explicit",
        "aspect": "event_contour",
        "mood": "attitudinal",
        "prominence": "tenseless",
        "notes": "Tense optional (pu/ca/ba); event contour (za'o/co'a); attitudinal indicators",
    },
    "KO_ST": {
        "tense": "none",
        "aspect": "particle_phase",
        "mood": "particle_oath",
        "prominence": "aspect_prominent",
        "notes": "Sacred Tongue Kor'aelin: VSO order, root+engine morphology, phase particles",
    },
}


# ─────────────────────────────────────────────────────────────
# Language metadata
# ─────────────────────────────────────────────────────────────

LANGUAGE_METADATA: dict[str, dict] = {
    "EN":       {"name": "English", "family": "germanic", "script": "latin", "vocab_size": 50000},
    "ZH":       {"name": "Chinese (Mandarin)", "family": "sinitic", "script": "cjk", "vocab_size": 50000},
    "JA":       {"name": "Japanese", "family": "japonic", "script": "cjk_kana", "vocab_size": 50000},
    "KO":       {"name": "Korean", "family": "koreanic", "script": "hangul", "vocab_size": 50000},
    "TOKIPONA": {"name": "Toki Pona", "family": "conlang", "script": "latin", "vocab_size": 120},
    "ESPERANTO":{"name": "Esperanto", "family": "conlang", "script": "latin", "vocab_size": 15000},
    "LOJBAN":   {"name": "Lojban", "family": "conlang", "script": "latin", "vocab_size": 1300},
    "KO_ST":    {"name": "Kor'aelin", "family": "sacred", "script": "sacred_token", "vocab_size": 256},
    "AV_ST":    {"name": "Av'tharin", "family": "sacred", "script": "sacred_token", "vocab_size": 256},
    "RU_ST":    {"name": "Ru'melith", "family": "sacred", "script": "sacred_token", "vocab_size": 256},
    "CA_ST":    {"name": "Ca'darian", "family": "sacred", "script": "sacred_token", "vocab_size": 256},
    "UM_ST":    {"name": "Um'briel", "family": "sacred", "script": "sacred_token", "vocab_size": 256},
    "DR_ST":    {"name": "Dr'aumric", "family": "sacred", "script": "sacred_token", "vocab_size": 256},
}
