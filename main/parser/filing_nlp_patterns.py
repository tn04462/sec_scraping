SECU_DEBT_SECURITY_L1_MODIFIERS = [
    "subordinated",
    "senior"
]

SECU_GENERAL_PRE_MODIFIERS = [
    "convertible"
]
SECU_GENERAL_PRE_COMPOUND_MODIFIERS = [
    [
        {"LOWER": "non"},
        {"LOWER": "-"},
        {"LOWER": "convertible"}
    ],
    [
        {"LOWER": "pre"},
        {"LOWER": "-"},
        {"LOWER": "funded"}
    ],
]
SECU_GENERAL_AFFIXES = [
    "series",
    "tranche",
    "class"
]
SECU_PURCHASE_AFFIXES = [
    "stock",
    "shares"
]
SECU_PURCHASE_SUFFIXES = [
    "rights",
    "contracts",
    "units"
]


SECU_ENT_SPECIAL_PATTERNS = [
    [{"LOWER": "common"}, {"LOWER": "units"}, {"LOWER": "of"}, {"LOWER": "beneficial"}, {"LOWER": "interest"}],
    [{"TEXT": "Subsciption"}, {"TEXT": "Rights"}],
]
# exclude particles, conjunctions from regex match 
SECU_ENT_DEPOSITARY_PATTERNS = [
    [   {"LOWER": {"IN": SECU_GENERAL_AFFIXES}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": ["depository", "depositary"]}},
        {"LOWER": {"IN": ["shares"]}}
    ]
        ,
    [
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": ["preferred", "common", "depository", "depositary", "ordinary"]}},
        {"LOWER": {"IN": ["shares"]}}
    ]
        ,
    *[  
        [
            *general_pre_sec_compound_modifier,
            {"LOWER": {"IN": ["depository", "depositary"]}},
            {"LOWER": {"IN": ["shares"]}, "OP": "?"}
        ] for general_pre_sec_compound_modifier in SECU_GENERAL_PRE_COMPOUND_MODIFIERS
    ]
        ,
    
    [   {"LOWER": {"IN": SECU_GENERAL_AFFIXES}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": ["depository", "depositary"]}, "OP": "?"},
        {"LOWER": {"IN": ["shares", "stock"]}},
        {"LOWER": {"IN": ["options", "option"]}}
    ]
        ,
    [
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": ["depository", "depositary"]}, "OP": "?"},
        {"LOWER": {"IN": ["shares", "stock"]}},
        {"LOWER": {"IN": ["options", "option"]}}
    ]

]

SECU_ENT_REGULAR_PATTERNS = [
    [   {"LOWER": {"IN": SECU_GENERAL_AFFIXES}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": ["preferred", "common", "ordinary"]}},
        {"LOWER": {"IN": ["stock"]}}
    ]
        ,
    [
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": ["preferred", "common", "ordinary"]}},
        {"LOWER": {"IN": ["stock"]}}
    ]
        ,
    *[  
        [
            *general_pre_sec_compound_modifier,
            {"LOWER": {"IN": ["preferred", "common", "warrant", "warrants", "ordinary"]}},
            {"LOWER": {"IN": ["stock"]}, "OP": "?"}
        ] for general_pre_sec_compound_modifier in SECU_GENERAL_PRE_COMPOUND_MODIFIERS
    ]
        ,
    
    [   {"LOWER": {"IN": SECU_GENERAL_AFFIXES}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": ["preferred", "common", "ordinary"]}, "OP": "?"},
        {"LOWER": {"IN": ["stock"]}},
        {"LOWER": {"IN": ["options", "option"]}}
    ]
        ,
    [
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": ["preferred", "common", "ordinary"]}, "OP": "?"},
        {"LOWER": {"IN": ["stock"]}},
        {"LOWER": {"IN": ["options", "option"]}}
    ]

        ,
    
    [   {"LOWER": {"IN": SECU_GENERAL_AFFIXES}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": ["warrant", "warrants"]}}
    ]
        ,
    [
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": ["warrant", "warrants"]}},
        {"LOWER": {"IN": ["stock"]}, "OP": "?"}
    ]
        ,

    [   {"LOWER": {"IN": SECU_GENERAL_AFFIXES}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
        {"LOWER": {"IN": SECU_DEBT_SECURITY_L1_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": "debt"}, {"LOWER": "securities"}
    ]
        ,

    [   {"LOWER": {"IN": SECU_DEBT_SECURITY_L1_MODIFIERS}, "OP": "?"},
        {"LOWER": {"IN": SECU_GENERAL_PRE_MODIFIERS}, "OP": "?"},
        {"LOWER": "debt"}, {"LOWER": "securities"}
    ]
        ,

    [   {"LOWER": {"IN": SECU_PURCHASE_AFFIXES}, "OP": "?"}, {"TEXT": "Purchase"}, {"LOWER": {"IN": SECU_PURCHASE_SUFFIXES}}
    ]
        ,            
]



SECUQUANTITY_ENT_PATTERNS = [
    [
        {"ENT_TYPE": "CARDINAL", "OP": "+"},
        {"LOWER": {"IN": ["authorized", "outstanding"]}, "OP": "?"},
        {"LOWER": {"IN": ["share", "shares", "warrant shares"]}}
    ],
    [
        {"ENT_TYPE": {"IN": ["CARDINAL", "MONEY"]}, "OP": "+"},
        {"POS": "ADJ", "OP": "?"},
        {"LOWER": {"IN": ["shares"]}},
        {"POS": "ADJ", "OP": "?"},
    ],
    [   
        {"ENT_TYPE": {"IN": ["CARDINAL", "MONEY"]}, "OP": "+"},
        {"LOWER": "of", "OP": "?"},
        {"LOWER": "our", "OP": "?"},
        {"ENT_TYPE": {"IN": ["SECU", "SECUREF"]}}
    ],
    [
        {"ENT_TYPE": {"IN": ["CARDINAL", "MONEY"]}, "OP": "+"},
        {"LOWER": "shares"},
        {"OP": "*", "IS_SENT_START": False, "POS": {"NOT_IN": ["VERB"]}, "ENT_TYPE": {"NOT_IN": ["SECU", "SECUQUANTITY"]}},
        {"LOWER": "of", "OP": "?"},
        {"LOWER": "our", "OP": "?"},
        {"ENT_TYPE": {"IN": ["SECU"]}}
    ],
    [
        {"ENT_TYPE": {"IN": ["CARDINAL", "MONEY"]}, "OP": "+"},
        {"POS": "ADJ", "OP": "*"},
        {"LOWER": "shares"},
        {"LOWER": "of"},
        {"ENT_TYPE": {"IN": ["SECU", "SECUREF"]}}
    ]

]



SECU_EXPIRY_PATTERNS = [
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": "expire"}, 
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": ">",
            "RIGHT_ID": "prep1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "on"}, 
        },
        {
            "LEFT_ID": "prep1",
            "REL_OP": ">",
            "RIGHT_ID": "pobj1",
            "RIGHT_ATTRS": {"DEP": "pobj"}, 
        },
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}}, 
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": "<<",
            "RIGHT_ID": "verb2",
            "RIGHT_ATTRS": {"POS": "VERB"}, 
        },
        {
            "LEFT_ID": "verb2",
            "REL_OP": ">",
            "RIGHT_ID": "prep1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "on"}, 
        },
        {
            "LEFT_ID": "prep1",
            "REL_OP": ">",
            "RIGHT_ID": "pobj1",
            "RIGHT_ATTRS": {"DEP": "pobj", "ENT_TYPE": "DATE"}, 
        },
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}}, 
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": ">>",
            "RIGHT_ID": "verb2",
            "RIGHT_ATTRS": {"POS": "VERB"}, 
        },
        {
            "LEFT_ID": "verb2",
            "REL_OP": ">",
            "RIGHT_ID": "prep1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "on"}, 
        },
        {
            "LEFT_ID": "prep1",
            "REL_OP": ">",
            "RIGHT_ID": "pobj1",
            "RIGHT_ATTRS": {"DEP": "pobj", "ENT_TYPE": "DATE"}, 
        },
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<",
            "RIGHT_ID": "verb2",
            "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": "exercise"}, 
        },
        {
            "LEFT_ID": "verb2",
            "REL_OP": ">>",
            "RIGHT_ID": "prep1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "up"}, 
        },
        {
            "LEFT_ID": "prep1",
            "REL_OP": ">",
            "RIGHT_ID": "prep2",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "to"}, 
        },
        {
            "LEFT_ID": "prep2",
            "REL_OP": ".*",
            "RIGHT_ID": "prep3",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "on"}, 
        },
        {
            "LEFT_ID": "prep3",
            "REL_OP": ">",
            "RIGHT_ID": "pobj1",
            "RIGHT_ATTRS": {"DEP": "pobj", "LEMMA": "date"}, 
        },
        {
            "LEFT_ID": "pobj1",
            "REL_OP": ">",
            "RIGHT_ID": "verb3",
            "RIGHT_ATTRS": {"LEMMA": "be"}, 
        },
        {
            "LEFT_ID": "verb3",
            "REL_OP": ">",
            "RIGHT_ID": "attr1",
            "RIGHT_ATTRS": {"DEP": "attr"}, 
        },
        {
            "LEFT_ID": "attr1",
            "REL_OP": ">>",
            "RIGHT_ID": "issuance1",
            "RIGHT_ATTRS": {"ENT_TYPE": {"IN": ["ORDINAL", "CARDINAL"]}}, 
        },
    ]
]


SECU_EXERCISE_PRICE_PATTERNS = [
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": ">",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": "VERB", "LOWER": "purchase"}, 
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": ">>",
            "RIGHT_ID": "prepverb1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": {"IN": ["of", "at"]}}, 
        },
        {
            "LEFT_ID": "prepverb1",
            "REL_OP": ">",
            "RIGHT_ID": "price",
            "RIGHT_ATTRS": {"DEP": {"IN": ["nobj", "pobj", "dobj"]}, "LOWER": "price"}, 
        },
        {
            "LEFT_ID": "price",
            "REL_OP": ">",
            "RIGHT_ID": "compound",
            "RIGHT_ATTRS": {"DEP": "compound", "LOWER": "exercise"}
        },
        {
            "LEFT_ID": "price",
            "REL_OP": ">",
            "RIGHT_ID": "prep1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "of"}
        },
        {
            "LEFT_ID": "prep1",
            "REL_OP": ">",
            "RIGHT_ID": "pobj_CD",
            "RIGHT_ATTRS": {"DEP": "pobj", "TAG": "CD"}
        },
        {
            "LEFT_ID": "pobj_CD",
            "REL_OP": ">",
            "RIGHT_ID": "dollar",
            "RIGHT_ATTRS": {"DEP": "nmod", "TAG": "$"}
        } 
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": "VERB", "LOWER": "purchase"}, 
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": ">",
            "RIGHT_ID": "conj",
            "RIGHT_ATTRS": {"DEP": "conj", "LEMMA": {"IN": ["remain"]}},
        },
        {
            "LEFT_ID": "conj",
            "REL_OP": ">",
            "RIGHT_ID": "prepverb1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": {"IN": ["of", "at"]}}, 
        },
        {
            "LEFT_ID": "prepverb1",
            "REL_OP": ">",
            "RIGHT_ID": "price",
            "RIGHT_ATTRS": {"DEP": {"IN": ["nobj", "pobj", "dobj"]}, "LOWER": "price"}, 
        },
        {
            "LEFT_ID": "price",
            "REL_OP": ">",
            "RIGHT_ID": "compound",
            "RIGHT_ATTRS": {"DEP": "compound", "LOWER": "exercise"}
        },
        {
            "LEFT_ID": "price",
            "REL_OP": ">",
            "RIGHT_ID": "prep1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "of"}
        },
        {
            "LEFT_ID": "prep1",
            "REL_OP": ">",
            "RIGHT_ID": "pobj_CD",
            "RIGHT_ATTRS": {"DEP": "pobj", "TAG": "CD"}
        },
        {
            "LEFT_ID": "pobj_CD",
            "REL_OP": ">",
            "RIGHT_ID": "dollar",
            "RIGHT_ATTRS": {"DEP": "nmod", "TAG": "$"}
        } 
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": ">",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": "VERB", "LOWER": "purchase"}, 
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": ">",
            "RIGHT_ID": "prepverb1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": {"IN": ["of", "at"]}}, 
        },
        {
            "LEFT_ID": "prepverb1",
            "REL_OP": ">",
            "RIGHT_ID": "price",
            "RIGHT_ATTRS": {"DEP": {"IN": ["nobj", "pobj", "dobj"]}, "LOWER": "price"}, 
        },
        {
            "LEFT_ID": "price",
            "REL_OP": ">",
            "RIGHT_ID": "compound",
            "RIGHT_ATTRS": {"DEP": "compound", "LOWER": "exercise"}
        },
        {
            "LEFT_ID": "price",
            "REL_OP": ">",
            "RIGHT_ID": "prep1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "of"}
        },
        {
            "LEFT_ID": "prep1",
            "REL_OP": ">",
            "RIGHT_ID": "pobj_CD",
            "RIGHT_ATTRS": {"DEP": "pobj", "TAG": "CD"}
        },
        {
            "LEFT_ID": "pobj_CD",
            "REL_OP": ">",
            "RIGHT_ID": "dollar",
            "RIGHT_ATTRS": {"DEP": "nmod", "TAG": "$"}
        } 
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": "VERB", "LOWER": "purchase"}, 
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": ">",
            "RIGHT_ID": "prepverb1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": {"IN": ["of", "at"]}}, 
        },
        {
            "LEFT_ID": "prepverb1",
            "REL_OP": ">",
            "RIGHT_ID": "price",
            "RIGHT_ATTRS": {"DEP": {"IN": ["nobj", "pobj", "dobj"]}, "LOWER": "price"}, 
        },
        {
            "LEFT_ID": "price",
            "REL_OP": ">",
            "RIGHT_ID": "compound",
            "RIGHT_ATTRS": {"DEP": "compound", "LOWER": "exercise"}
        },
        {
            "LEFT_ID": "price",
            "REL_OP": ">",
            "RIGHT_ID": "prep1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "of"}
        },
        {
            "LEFT_ID": "prep1",
            "REL_OP": ">",
            "RIGHT_ID": "pobj_CD",
            "RIGHT_ATTRS": {"DEP": "pobj", "TAG": "CD"}
        },
        {
            "LEFT_ID": "pobj_CD",
            "REL_OP": ">",
            "RIGHT_ID": "dollar",
            "RIGHT_ATTRS": {"DEP": "nmod", "TAG": "$"}
        } 
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": "have"}, 
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": ">",
            "RIGHT_ID": "price",
            "RIGHT_ATTRS": {"DEP": {"IN": ["nobj", "pobj", "dobj"]}, "LOWER": "price"}, 
        },
        {
            "LEFT_ID": "price",
            "REL_OP": ">",
            "RIGHT_ID": "compound",
            "RIGHT_ATTRS": {"DEP": "compound", "LOWER": "exercise"}
        },
        {
            "LEFT_ID": "price",
            "REL_OP": ">",
            "RIGHT_ID": "prep1",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "of"}
        },
        {
            "LEFT_ID": "prep1",
            "REL_OP": ">",
            "RIGHT_ID": "pobj_CD",
            "RIGHT_ATTRS": {"DEP": "pobj", "TAG": "CD"}
        },
        {
            "LEFT_ID": "pobj_CD",
            "REL_OP": ">",
            "RIGHT_ID": "dollar",
            "RIGHT_ATTRS": {"DEP": "nmod", "TAG": "$"}
        }  
    ]
]

SECU_DATE_RELATION_PATTERNS_FROM_ROOT_VERB = [
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": ">",
            "RIGHT_ID": "prep_phrase_start",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER":  "as"}
        },
        {
            "LEFT_ID": "prep_phrase_start",
            "REL_OP": ">",
            "RIGHT_ID": "second_prep",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "of"}
        },
        {
            "LEFT_ID": "second_prep",
            "REL_OP": ">",
            "RIGHT_ID": "date_start",
            "RIGHT_ATTRS": {"DEP": "pobj", "ENT_TYPE": "DATE"}
        }
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": ">",
            "RIGHT_ID": "prep_phrase_start",
            "RIGHT_ATTRS": {"DEP": "prep", "LOWER":  "on"}
        },
        {
            "LEFT_ID": "prep_phrase_start",
            "REL_OP": ">",
            "RIGHT_ID": "date_start",
            "RIGHT_ATTRS": {"DEP": "pobj", "ENT_TYPE": "DATE"}
        }
    ],
    
]


SECU_SECUQUANTITY_PATTERNS = [
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<",
            "RIGHT_ID": "pobj",
            "RIGHT_ATTRS": {"DEP": "pobj", "LOWER": "of"}
        },
        {
            "LEFT_ID": "pobj",
            "REL_OP": "<",
            "RIGHT_ID": "prep",
            "RIGHT_ATTRS": {"DEP": "prep", "POS": {"IN": ["NOUN", "PROPN"]}, "LOWER": "shares"}
        },
        {
            "LEFT_ID": "prep",
            "REL_OP": ">",
            "RIGHT_ID": "secuquantity",
            "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
        }
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<",
            "RIGHT_ID": "prep",
            "RIGHT_ATTRS": {"DEP": "prep"}
        },
        {
            "LEFT_ID": "prep",
            "REL_OP": "<",
            "RIGHT_ID": "noun",
            "RIGHT_ATTRS": {"POS": "NOUN", "LOWER": {"IN": ["shares"]}}
        },
        {
            "LEFT_ID": "noun",
            "REL_OP": ">",
            "RIGHT_ID": "secuquantity",
            "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
        }

    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": ">",
            "RIGHT_ID": "secuquantity",
            "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
        }

    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<<",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": {"IN": ["relate"]}}, 
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": ">",
            "RIGHT_ID": "prep",
            "RIGHT_ATTRS": {"DEP": "prep"}, 
        },
        {
            "LEFT_ID": "prep",
            "REL_OP": ">",
            "RIGHT_ID": "noun_relation",
            "RIGHT_ATTRS": {"POS": "NOUN"}, 
        },
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<<",
            "RIGHT_ID": "any",
            "RIGHT_ATTRS": {"POS": "NOUN"}
        },
        {
            "LEFT_ID": "any",
            "REL_OP": ">",
            "RIGHT_ID": "secuquantity",
            "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
        }
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<<",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": {"IN": ["relate"]}}, 
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": ">",
            "RIGHT_ID": "prep",
            "RIGHT_ATTRS": {"DEP": "prep"}, 
        },
        {
            "LEFT_ID": "prep",
            "REL_OP": ">",
            "RIGHT_ID": "noun_relation",
            "RIGHT_ATTRS": {"POS": "NOUN"}, 
        },
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<<",
            "RIGHT_ID": "any",
            "RIGHT_ATTRS": {"POS": "NOUN"}
        },
        {
            "LEFT_ID": "any",
            "REL_OP": ">",
            "RIGHT_ID": "secuquantity",
            "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": "<",
            "RIGHT_ID": "source_secu",
            "RIGHT_ATTRS": {"ENT_TYPE": "SECU"}, 
        }
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": {"NOT_IN": ["purchase", "acquire"]}}, 
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": ">>",
            "RIGHT_ID": "secuquantity",
            "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
        }
    ],
    [
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<<",
            "RIGHT_ID": "verb1",
            "RIGHT_ATTRS": {"POS": "VERB"}
        },
        {
            "LEFT_ID": "anchor",
            "REL_OP": "<<",
            "RIGHT_ID": "any",
            "RIGHT_ATTRS": {}
        },
        {
            "LEFT_ID": "any",
            "REL_OP": ">",
            "RIGHT_ID": "secuquantity",
            "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
        },
        {
            "LEFT_ID": "verb1",
            "REL_OP": "<",
            "RIGHT_ID": "source_secu",
            "RIGHT_ATTRS": {"ENT_TYPE": "SECU"}, 
        },

    ]
]
        