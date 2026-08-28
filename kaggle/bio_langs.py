"""bio_langs.py — the languages we read marriage descriptions in, and the words that mark one.

The twenty biggest Wikipedias that actually write biographies (the bot-built ones — Cebuano, Waray,
Egyptian Arabic — are excluded, they carry no personal prose), plus ARMENIAN by operator request.

Each language brings two things:
  · REL: the words that say a passage is about the marriage rather than the career;
  · HEAD: the section headings where private life is kept.
A person's NAME in that language comes from Wikidata's own label, so matching works across scripts —
"Աննա" is found in the Armenian article, not the Latin spelling.
"""

LANGS = ["en", "de", "fr", "es", "it", "ru", "pt", "nl", "pl", "sv",
         "ja", "zh", "ar", "fa", "tr", "uk", "cs", "he", "ko", "hu", "hy"]

REL = {
    "en": r"marri|wed|wife|husband|spouse|divorc|separat|widow|engage|couple|affair|mistress|son|"
          r"daughter|child|abus|violen|devoted|happy|unhappy|estranged|collaborat|together",
    "de": r"heirat|ehe|gatte|gattin|ehefrau|ehemann|scheid|witwe|witwer|verlob|paar|geliebte|"
          r"sohn|tochter|kind|gewalt|treu|untreu|getrennt|gemeinsam",
    "fr": r"mari|épous|femme|divorc|séparat|veuv|fianc|couple|maîtresse|amant|fils|fille|enfant|"
          r"violen|ensemble|infidél",
    "es": r"matrimoni|cas[óa]|espos|marido|divorci|separaci|viud|prometid|pareja|amante|hijo|hija|"
          r"hijos|violenc|junto|infidel",
    "it": r"matrimoni|spos|mogli|marito|divorzi|separazion|vedov|fidanz|coppia|amante|figli|"
          r"violenz|insieme|infedel",
    "ru": r"брак|жена|муж|супруг|развод|вдов|обручен|пара|любовниц|сын|дочь|дет|насили|вместе|измен",
    "pt": r"casament|casou|espos|marido|divórci|separaç|viúv|noiv|casal|amante|filho|filha|filhos|"
          r"violênc|junto|infidel",
    "nl": r"huwelijk|trouwde|echtgeno|vrouw|man|scheid|weduw|verloofd|paar|minnares|zoon|dochter|"
          r"kind|geweld|samen|ontrouw",
    "pl": r"małżeń|ożenił|poślubi|żona|mąż|rozwód|wdow|narzecz|para|kochank|syn|córk|dzieci|"
          r"przemoc|razem|zdrad",
    "sv": r"gift|äkten|make|maka|hustru|skilsm|änk|förlov|par|älskarinna|son|dotter|barn|våld|"
          r"tillsammans|otrohet",
    "ja": r"結婚|夫|妻|婚姻|離婚|死別|未亡人|婚約|夫妻|愛人|息子|娘|子供|子ども|暴力|不倫|共に",
    "zh": r"結婚|结婚|丈夫|妻子|婚姻|離婚|离婚|寡婦|寡妇|訂婚|订婚|夫婦|夫妇|情人|兒子|儿子|"
          r"女兒|女儿|孩子|暴力|外遇|一起",
    "ar": r"زواج|زوج|زوجة|تزوج|طلاق|أرمل|خطوبة|عشيق|ابن|ابنة|أطفال|عنف|معا|خيانة",
    "fa": r"ازدواج|همسر|شوهر|زن|طلاق|بیوه|نامزد|معشوق|پسر|دختر|فرزند|خشونت|باهم|خیانت",
    "tr": r"evlen|evlil|eş|karı|koca|boşan|dul|nişan|çift|sevgili|oğl|kız|çocuk|şiddet|birlikte|aldat",
    "uk": r"шлюб|дружин|чолові|розлуч|вдов|заручен|пара|коханк|син|дочк|діт|насил|разом|зрада",
    "cs": r"sňatek|manžel|žena|rozvod|vdov|zásnub|pár|milenk|syn|dcer|dět|násil|spolu|nevěr",
    "he": r"נישא|נישואי|אישה|בעל|גירוש|אלמנ|אירוס|זוג|מאהב|בן|בת|ילדים|אלימות|יחד|בגיד",
    "ko": r"결혼|남편|아내|부부|이혼|과부|약혼|연인|아들|딸|자녀|폭력|함께|불륜",
    "hu": r"házas|feleség|férj|elvál|özvegy|eljegyz|pár|szerető|fia|lánya|gyermek|erőszak|együtt|hűtlen",
    "hy": r"ամուսն|կին|ամուսին|ամուսնալուծ|այրի|նշանադր|զույգ|սիրուհ|որդ|դուստր|երեխա|"
          r"բռնություն|միասին|դավաճան",
}

HEAD = {
    "en": r"personal life|private life|marriage|marriages|family|family life|relationships?|divorce|children",
    "de": r"leben|privates|familie|ehe|ehen|privatleben|nachkommen",
    "fr": r"vie privée|famille|mariage|mariages|descendance|vie personnelle",
    "es": r"vida personal|vida privada|familia|matrimonio|matrimonios|descendencia",
    "it": r"vita privata|famiglia|matrimonio|matrimoni|discendenza|vita personale",
    "ru": r"личная жизнь|семья|брак|браки|дети|частная жизнь",
    "pt": r"vida pessoal|vida privada|família|casamento|casamentos|descendência",
    "nl": r"privéleven|familie|huwelijk|huwelijken|gezin|kinderen",
    "pl": r"życie prywatne|rodzina|małżeństwo|małżeństwa|dzieci|życie osobiste",
    "sv": r"privatliv|familj|äktenskap|barn|personligt",
    "ja": r"私生活|家族|結婚|人物|家庭",
    "zh": r"私生活|家庭|婚姻|家族|個人生活|个人生活",
    "ar": r"الحياة الشخصية|الحياة الخاصة|الأسرة|الزواج|العائلة",
    "fa": r"زندگی شخصی|خانواده|ازدواج|زندگی خصوصی",
    "tr": r"özel yaşamı|özel hayatı|aile|evlilik|evlilikleri|kişisel yaşam",
    "uk": r"особисте життя|родина|сім'я|шлюб|діти",
    "cs": r"osobní život|rodina|manželství|soukromý život|děti",
    "he": r"חיים אישיים|משפחה|נישואים|חיים פרטיים",
    "ko": r"사생활|가족|결혼|개인 생활",
    "hu": r"magánélete|család|házassága|házasságai|gyermekei",
    "hy": r"անձնական կյանք|ընտանիք|ամուսնություն|մասնավոր կյանք",
}

# Chinese, Japanese and Korean end sentences with their own stops; everything else uses Latin ones.
CJK = {"ja", "zh", "ko"}
