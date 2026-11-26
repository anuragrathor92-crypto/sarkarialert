"""Researched Hindi & English government job keyword metadata and schema helpers."""

# Structured keyword themes aligned with Indian government job & exam search intent
CATEGORY_SEO = {
    "latest-jobs": {
        "keywords_en": ["Latest Govt Jobs 2026", "Sarkari Naukri", "Online Form", "Direct Official Apply"],
        "keywords_hi": ["नवीनतम सरकारी नौकरी 2026", "सरकारी भर्ती ऑनलाइन आवेदन", "आधिकारिक नोटिफिकेशन"],
        "desc_template": "{title} — {dept} ({vac_phrase}). योग्यता: {qual}, अंतिम तिथि: {last_date}. आधिकारिक आवेदन लिंक व नोटिफिकेशन देखें।",
        "intro_hi": "सभी केंद्र व राज्य सरकार की सक्रिय भर्तियाँ — आधिकारिक नोटिफिकेशन, योग्यता, आयु सीमा और सीधे पोर्टल लिंक सहित।",
    },
    "results": {
        "keywords_en": ["Sarkari Result 2026", "Merit List", "Cut Off Marks", "Score Card"],
        "keywords_hi": ["सरकारी रिजल्ट 2026", "मेरिट सूची", "चयन परिणाम"],
        "desc_template": "{title} — {dept} आधिकारिक परीक्षा परिणाम, कट-ऑफ अंक और स्कोरकार्ड डाउनलोड लिंक Sarkari Alert पर देखें।",
        "intro_hi": "केंद्र और राज्य परीक्षाओं के सत्यापित आधिकारिक परिणाम, मेरिट लिस्ट और कट-ऑफ लिंक।",
    },
    "admit-card": {
        "keywords_en": ["Admit Card 2026", "Hall Ticket Download", "Exam City Slip"],
        "keywords_hi": ["प्रवेश पत्र 2026", "एडमिट कार्ड डाउनलोड", "परीक्षा शहर सूचना"],
        "desc_template": "{title} — {dept} एडमिट कार्ड डाउनलोड लिंक, परीक्षा तिथि व हॉल टिकट निर्देश यहाँ देखें।",
        "intro_hi": "आगामी परीक्षाओं के आधिकारिक एडमिट कार्ड, परीक्षा शहर स्लिप और कॉल लेटर डाउनलोड लिंक।",
    },
    "answer-key": {
        "keywords_en": ["Answer Key PDF 2026", "Response Sheet", "Objection Link"],
        "keywords_hi": ["उत्तर कुंजी 2026", "आंसर की PDF", "आपत्ति लिंक"],
        "desc_template": "{title} — {dept} आधिकारिक उत्तर कुंजी PDF, प्रश्न पत्र व आपत्ति दर्ज करने की पूरी जानकारी।",
        "intro_hi": "विभिन्न सरकारी भर्ती परीक्षाओं की आधिकारिक उत्तर कुंजी (Answer Key) व आपत्ति लिंक।",
    },
    "admission": {
        "keywords_en": ["Govt Admission 2026-27", "Entrance Exam Form", "UP RTE Admission"],
        "keywords_hi": ["सरकारी प्रवेश व नामांकन", "प्रवेश परीक्षा ऑनलाइन फॉर्म"],
        "desc_template": "{title} — {dept} ऑनलाइन आवेदन तिथियाँ, पात्रता व आधिकारिक नामांकन निर्देश देखें।",
        "intro_hi": "विश्वविद्यालय, पॉलिटेक्निक, विद्यालय और प्रवेश परीक्षाओं के सत्यापित नामांकन अपडेट।",
    },
    "yojana": {
        "keywords_en": ["Sarkari Yojana 2026", "Central & State Welfare Schemes"],
        "keywords_hi": ["सरकारी योजना 2026", "पात्रता व लाभ", "आधिकारिक योजना पोर्टल"],
        "desc_template": "{title_en} ({title_hi}) — {dept} योजना के लाभ, पात्रता, आवश्यक दस्तावेज व आधिकारिक सरकारी पोर्टल।",
        "intro_hi": "केंद्र व सभी 28 राज्यों और 8 केंद्र शासित प्रदेशों की सत्यापित जनकल्याणकारी योजनाओं की मार्गदर्शिका।",
    },
    "scholarship": {
        "keywords_en": ["Govt Scholarship 2026-27", "NSP Scholarship Form", "Student Aid"],
        "keywords_hi": ["छात्रवृत्ति योजना 2026-27", "स्कॉलरशिप ऑनलाइन आवेदन", "पात्रता व अंतिम तिथि"],
        "desc_template": "{title} — {dept} छात्रवृत्ति पात्रता, राशि, अंतिम तिथि व आधिकारिक पोर्टल निर्देश देखें।",
        "intro_hi": "मेधावी और पात्र विद्यार्थियों के लिए केंद्र व राज्य सरकार की सक्रिय छात्रवृत्ति योजनाएँ।",
    },
    "exam-date": {
        "keywords_en": ["Govt Exam Calendar 2026", "Exam Date Notice"],
        "keywords_hi": ["परीक्षा तिथि 2026", "आधिकारिक एग्जाम कैलेंडर"],
        "desc_template": "{title} — {dept} आधिकारिक परीक्षा कार्यक्रम, शिफ्ट विवरण और संशोधित परीक्षा तिथियाँ देखें।",
        "intro_hi": "प्रमुख सरकारी भर्ती व प्रवेश परीक्षाओं के आधिकारिक परीक्षा कैलेंडर और तिथि सूचनाएँ।",
    },
    "upcoming-jobs": {
        "keywords_en": ["Upcoming Govt Jobs 2027", "Exam Calendar", "Vacancy Alert"],
        "keywords_hi": ["आगामी सरकारी भर्ती 2026-27", "सरकारी जॉब कैलेंडर"],
        "desc_template": "{title} — {dept} की आगामी भर्ती सूचना, संभावित आवेदन व परीक्षा कैलेंडर तिथि देखें।",
        "intro_hi": "UPSC, SSC, रेलवे व राज्य आयोगों की आने वाली प्रमुख सरकारी भर्तियों का आधिकारिक कैलेंडर।",
    },
    "10th-iti": {
        "keywords_en": ["10th Pass Govt Jobs", "ITI Apprentice Recruitment 2026"],
        "keywords_hi": ["10वीं पास सरकारी नौकरी", "ITI अपरेंटिस भर्ती 2026"],
        "desc_template": "{title} — {dept} ({vac_phrase}). 10वीं / ITI योग्यता, अंतिम तिथि: {last_date} व आधिकारिक आवेदन लिंक।",
        "intro_hi": "10वीं, 12वीं और ITI योग्यता वाले युवाओं के लिए सत्यापित सरकारी व अपरेंटिस भर्तियाँ।",
    },
    "documents": {
        "keywords_en": ["Citizen Services", "Aadhaar PAN Voter Certificate Portal"],
        "keywords_hi": ["नागरिक सेवाएँ", "प्रमाणपत्र व दस्तावेज पोर्टल"],
        "desc_template": "{title} — {dept} की आधिकारिक ऑनलाइन नागरिक सेवा, प्रमाणपत्र व दस्तावेज सत्यापन जानकारी।",
        "intro_hi": "आधार, पैन, मतदाता पहचान व अन्य आवश्यक सरकारी दस्तावेजों के आधिकारिक लिंक व मार्गदर्शन।",
    },
    "syllabus": {
        "keywords_en": ["Exam Syllabus PDF 2026", "Exam Pattern"],
        "keywords_hi": ["भर्ती पाठ्यक्रम 2026", "परीक्षा पैटर्न व सिलेबस PDF"],
        "desc_template": "{title} — {dept} परीक्षा का आधिकारिक सिलेबस PDF, विषयवार अंक व चयन पैटर्न विवरण।",
        "intro_hi": "सरकारी परीक्षाओं का आधिकारिक पाठ्यक्रम (Syllabus) और परीक्षा पैटर्न PDF विवरण।",
    },
    "outsourcing": {
        "keywords_en": ["Contract Govt Jobs 2026", "Outsourcing Vacancy"],
        "keywords_hi": ["संविदा भर्ती 2026", "आउटसोर्सिंग सरकारी नौकरी"],
        "desc_template": "{title} — {dept} ({vac_phrase}). संविदा योग्यता: {qual}, अंतिम तिथि: {last_date} व आधिकारिक लिंक।",
        "intro_hi": "विभिन्न सरकारी विभागों व निगमों की सत्यापित संविदा एवं आउटसोर्सिंग भर्तियाँ।",
    },
}

REGION_HINTS = [
    ("pilibhit", ("Pilibhit", "Uttar Pradesh")),
    ("lucknow", ("Lucknow", "Uttar Pradesh")),
    ("ghazipur", ("Ghazipur", "Uttar Pradesh")),
    ("ballia", ("Ballia", "Uttar Pradesh")),
    ("uppsc", ("Prayagraj", "Uttar Pradesh")),
    ("upessc", ("Prayagraj", "Uttar Pradesh")),
    ("upsssc", ("Lucknow", "Uttar Pradesh")),
    ("up-icds", ("Lucknow", "Uttar Pradesh")),
    ("up-rte", ("Lucknow", "Uttar Pradesh")),
    ("up-police", ("Lucknow", "Uttar Pradesh")),
    ("uptet", ("Prayagraj", "Uttar Pradesh")),
    ("ukpsc", ("Haridwar", "Uttarakhand")),
    ("uksssc", ("Dehradun", "Uttarakhand")),
    ("bihar-vidhan", ("Patna", "Bihar")),
    ("bihar", ("Patna", "Bihar")),
    ("bpsc", ("Patna", "Bihar")),
    ("btsc", ("Patna", "Bihar")),
    ("ernakulam", ("Ernakulam", "Kerala")),
    ("thrissur", ("Thrissur", "Kerala")),
    ("kerala-psc", ("Thiruvananthapuram", "Kerala")),
    ("keralapsc", ("Thiruvananthapuram", "Kerala")),
    ("ossc", ("Bhubaneswar", "Odisha")),
    ("osssc", ("Bhubaneswar", "Odisha")),
    ("dsssb", ("New Delhi", "Delhi")),
    ("du-", ("New Delhi", "Delhi")),
    ("delhi", ("New Delhi", "Delhi")),
    ("manit", ("Bhopal", "Madhya Pradesh")),
    ("mp-", ("Bhopal", "Madhya Pradesh")),
    ("mpesb", ("Bhopal", "Madhya Pradesh")),
    ("assam", ("Shillong", "Meghalaya")),
    ("goa-shipyard", ("Vasco da Gama", "Goa")),
    ("niper-ahmedabad", ("Gandhinagar", "Gujarat")),
    ("iit-ism-dhanbad", ("Dhanbad", "Jharkhand")),
    ("dvc-", ("Kolkata", "West Bengal")),
    ("icmr-nirbi", ("Kolkata", "West Bengal")),
    ("kolkata", ("Kolkata", "West Bengal")),
    ("cpcl-", ("Chennai", "Tamil Nadu")),
    ("icmr-nie", ("Chennai", "Tamil Nadu")),
    ("nlc", ("Neyveli", "Tamil Nadu")),
    ("scl-", ("SAS Nagar (Mohali)", "Punjab")),
    ("bbmb", ("Chandigarh", "Punjab")),
    ("hpsbys", ("Shimla", "Himachal Pradesh")),
    ("bseh", ("Bhiwani", "Haryana")),
    ("htet", ("Bhiwani", "Haryana")),
    ("powergrid", ("Gurugram", "Haryana")),
    ("becil", ("Noida", "Uttar Pradesh")),
    ("aiims-bilaspur", ("Bilaspur", "Himachal Pradesh")),
    ("aiims-gorakhpur", ("Gorakhpur", "Uttar Pradesh")),
    ("rrc-cr", ("Mumbai", "Maharashtra")),
    ("sbi", ("Mumbai", "Maharashtra")),
    ("bpcl", ("Mumbai", "Maharashtra")),
    ("sidbi", ("Lucknow", "Uttar Pradesh")),
    ("exim", ("Mumbai", "Maharashtra")),
    ("ecil", ("Hyderabad", "Telangana")),
    ("isro-sdsc-shar", ("Sriharikota", "Andhra Pradesh")),
    ("rrc-nr", ("New Delhi", "Delhi")),
    ("upsc", ("New Delhi", "Delhi")),
    ("ssc", ("New Delhi", "Delhi")),
    ("csir", ("New Delhi", "Delhi")),
    ("nsic", ("New Delhi", "Delhi")),
    ("gail", ("New Delhi", "Delhi")),
    ("ncpul", ("New Delhi", "Delhi")),
    ("aees", ("Mumbai", "Maharashtra")),
    ("afcat", ("New Delhi", "Delhi")),
    ("asrb", ("New Delhi", "Delhi")),
    ("rrb", ("New Delhi", "Delhi")),
    ("bhel", ("New Delhi", "Delhi")),
    ("bel", ("Bengaluru", "Karnataka")),
    ("hal", ("Bengaluru", "Karnataka")),
    ("icmr", ("New Delhi", "Delhi")),
]


def infer_employment_type(post):
    """Return Schema.org employmentType without inventing unsupported terms."""
    blob = " ".join([
        post.get("category", ""),
        post.get("title", ""),
        post.get("summary", ""),
    ]).lower()
    if post.get("category") == "outsourcing" or any(k in blob for k in ("contract", "संविदा", "fixed term", "fixed-term")):
        return "CONTRACTOR"
    if "apprentice" in blob or "अपरेंटिस" in blob:
        return "INTERN"
    return "FULL_TIME"


def resolve_verified_location(post):
    """Return verified (addressLocality, addressRegion) tuple from post fields/authority HQ."""
    if post.get("locationLocality") and post.get("locationRegion"):
        return post["locationLocality"], post["locationRegion"]
    slug_dept = f"{post.get('id', '')} {post.get('department', '')} {post.get('title', '')}".lower()
    for needle, loc_pair in REGION_HINTS:
        if needle in slug_dept:
            return loc_pair
    return ("New Delhi", "Delhi")


def infer_region(post):
    """Infer Indian state/UT for JobPosting.jobLocation.address."""
    return resolve_verified_location(post)[1]
