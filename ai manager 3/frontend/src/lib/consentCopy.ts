/**
 * Multilingual configuration for security and data privacy consent screens.
 * Structured for English, Hindi, and Marathi with original, plain-English copy.
 */

export interface ConsentContent {
  title: string;
  subtitle: string;
  whatWeAccessTitle: string;
  whatWeAccessPoints: string[];
  whatWeUseItForTitle: string;
  whatWeUseItForPoints: string[];
  whatWeWillNotDoTitle: string;
  whatWeWillNotDoPoints: string[];
  yourControlTitle: string;
  yourControlPoints: string[];
  privacyPolicyText: string;
  termsText: string;
  allowButtonText: string;
  notNowButtonText: string;
}

export interface ConsentTranslations {
  sms_import: ConsentContent;
  statement_upload: ConsentContent;
}

export const CONSENT_COPY: Record<"en" | "hi" | "mr", ConsentTranslations> = {
  en: {
    sms_import: {
      title: "FinTrack AI wants to access your financial messages",
      subtitle:
        "We ask for explicit permission before analyzing any financial alerts. Your privacy and financial control always come first.",
      whatWeAccessTitle: "What we will access",
      whatWeAccessPoints: [
        "Only bank, card, and UPI transaction alerts pasted or imported for your account.",
        "Nothing else: we never access personal messages, WhatsApp chats, photos, or contact lists.",
      ],
      whatWeUseItForTitle: "What we use it for",
      whatWeUseItForPoints: [
        "Extracting transaction dates, amounts, and merchant names for automated expense tracking.",
        "Smart categorization of purchases and generating monthly spending predictions.",
      ],
      whatWeWillNotDoTitle: "What we will NOT do",
      whatWeWillNotDoPoints: [
        "We never perform transactions, move money, or make payments on your behalf.",
        "We never read or store One-Time Passwords (OTPs), authentication codes, or personal messages.",
        "We never sell, rent, or share your financial information with third-party advertisers.",
        "We never store raw statement documents on server disks after in-memory parsing.",
      ],
      yourControlTitle: "Your control",
      yourControlPoints: [
        "You can decline and still use the app with manual entry or statement uploads.",
        "You can withdraw or revoke permission anytime directly from Privacy Settings.",
        "You can export or permanently delete your financial records at any time.",
      ],
      privacyPolicyText: "Privacy Policy",
      termsText: "Terms of Service",
      allowButtonText: "Allow",
      notNowButtonText: "Not now",
    },
    statement_upload: {
      title: "FinTrack AI wants to read the statement you upload",
      subtitle:
        "We ask for explicit permission before parsing your bank statements. Statements are processed strictly in-memory.",
      whatWeAccessTitle: "What we will access",
      whatWeAccessPoints: [
        "Only the specific CSV or PDF statement document you choose to upload.",
        "Nothing else on your computer, phone, or local file storage.",
      ],
      whatWeUseItForTitle: "What we use it for",
      whatWeUseItForPoints: [
        "Extracting transaction line items (dates, merchants, amounts) for your ledger.",
        "Classifying expenses into spending categories and predicting end-of-month balances.",
      ],
      whatWeWillNotDoTitle: "What we will NOT do",
      whatWeWillNotDoPoints: [
        "We never store the original raw statement file on disk after processing.",
        "We never initiate money movement or connect directly to your net-banking credentials.",
        "We never share or commercialize your transaction history with external parties.",
      ],
      yourControlTitle: "Your control",
      yourControlPoints: [
        "You can decline and choose manual transaction entry instead.",
        "You can revoke upload authorization and wipe previously uploaded records anytime.",
        "Your data remains completely isolated under your user account only.",
      ],
      privacyPolicyText: "Privacy Policy",
      termsText: "Terms of Service",
      allowButtonText: "Allow",
      notNowButtonText: "Not now",
    },
  },
  hi: {
    sms_import: {
      title: "FinTrack AI आपके वित्तीय संदेशों तक पहुंच का अनुरोध करता है",
      subtitle:
        "वित्तीय अलर्ट पढ़ने से पहले हम आपकी स्पष्ट अनुमति मांगते हैं। आपकी गोपनीयता हमेशा सर्वोपरि है।",
      whatWeAccessTitle: "हम क्या एक्सेस करेंगे",
      whatWeAccessPoints: [
        "केवल बैंक, कार्ड और यूपीआई लेनदेन अलर्ट जो आप पेस्ट या आयात करते हैं।",
        "कुछ भी अतिरिक्त नहीं: हम व्यक्तिगत संदेश, चैट या संपर्क कभी नहीं पढ़ते।",
      ],
      whatWeUseItForTitle: "हम इसका उपयोग किस लिए करते हैं",
      whatWeUseItForPoints: [
        "लेनदेन की तारीख, राशि और व्यापारी नाम निकालकर स्वचालित खर्च ट्रैकिंग के लिए।",
        "खर्चों का वर्गीकरण और मासिक खर्च का पूर्वानुमान लगाने के लिए।",
      ],
      whatWeWillNotDoTitle: "हम क्या कभी नहीं करेंगे",
      whatWeWillNotDoPoints: [
        "हम कभी भी आपके खाते से पैसे ट्रांसफर या भुगतान नहीं करेंगे।",
        "हम कभी भी ओटीपी (OTP) या व्यक्तिगत संदेश नहीं पढ़ेंगे।",
        "हम कभी भी आपका डेटा तीसरे पक्ष या विज्ञापनदाताओं को नहीं बेचेंगे।",
      ],
      yourControlTitle: "आपका नियंत्रण",
      yourControlPoints: [
        "आप अस्वीकार कर सकते हैं और मैन्युअल रूप से लेनदेन जोड़ सकते हैं।",
        "आप गोपनीयता सेटिंग्स से कभी भी अनुमति वापस ले सकते हैं।",
        "आप कभी भी अपना सारा डेटा हटा सकते हैं।",
      ],
      privacyPolicyText: "गोपनीयता नीति",
      termsText: "सेवा की शर्तें",
      allowButtonText: "अनुमति दें",
      notNowButtonText: "अभी नहीं",
    },
    statement_upload: {
      title: "FinTrack AI आपके अपलोड किए गए स्टेटमेंट को पढ़ना चाहता है",
      subtitle:
        "स्टेटमेंट प्रोसेस करने से पहले हम आपकी अनुमति लेते हैं। फ़ाइल केवल मेमोरी में प्रोसेस होती है।",
      whatWeAccessTitle: "हम क्या एक्सेस करेंगे",
      whatWeAccessPoints: [
        "केवल वही CSV या PDF फ़ाइल जिसे आप अपलोड करने के लिए चुनते हैं।",
        "आपकी डिवाइस पर मौजूद किसी अन्य फ़ाइल को नहीं।",
      ],
      whatWeUseItForTitle: "हम इसका उपयोग किस लिए करते हैं",
      whatWeUseItForPoints: [
        "लेनदेन विवरण निकालकर खर्चों की सूची तैयार करने के लिए।",
        "खर्चों को श्रेणियों में छांटने और मासिक विश्लेषण के लिए।",
      ],
      whatWeWillNotDoTitle: "हम क्या कभी नहीं करेंगे",
      whatWeWillNotDoPoints: [
        "प्रोसेसिंग के बाद हम मूल फ़ाइल सर्वर डिस्क पर कभी स्टोर नहीं करते।",
        "हम कभी भी आपके बैंक खाते में लेन-देन शुरू नहीं करते।",
      ],
      yourControlTitle: "आपका नियंत्रण",
      yourControlPoints: [
        "आप कभी भी अनुमति वापस ले सकते हैं और डेटा मिटा सकते हैं।",
        "आपका वित्तीय डेटा केवल आपके खाते तक ही सीमित रहता है।",
      ],
      privacyPolicyText: "गोपनीयता नीति",
      termsText: "सेवा की शर्तें",
      allowButtonText: "अनुमति दें",
      notNowButtonText: "अभी नहीं",
    },
  },
  mr: {
    sms_import: {
      title: "FinTrack AI आपल्या आर्थिक संदेशांमध्ये प्रवेश करण्याची परवानगी मागत आहे",
      subtitle:
        "आर्थिक संदेश वाचण्यापूर्वी आम्ही आपली स्पष्ट संमती घेतो. आपली गोपनीयता सर्वोच्च प्राधान्य आहे.",
      whatWeAccessTitle: "आम्ही कशात प्रवेश करू",
      whatWeAccessPoints: [
        "केवळ बँक, कार्ड आणि यूपीआय व्यवहार संदेश जे आपण आयात करता.",
        "इतर काहीही नाही: वैयक्तिक चॅट्स, संपर्क किंवा फोटोंमध्ये प्रवेश नाही.",
      ],
      whatWeUseItForTitle: "आम्ही कशासाठी वापरतो",
      whatWeUseItForPoints: [
        "खर्च ट्रॅकिंग आणि मासिक अंदाज तयार करण्यासाठी व्यवहारांचे तपशील मिळवणे.",
        "खर्चांचे अचूक वर्गीकरण करण्यासाठी.",
      ],
      whatWeWillNotDoTitle: "आम्ही काय कधीही करणार नाही",
      whatWeWillNotDoPoints: [
        "आम्ही आपल्या खात्यातून कधीही पैसे पाठवणार किंवा व्यवहार करणार नाही.",
        "आम्ही कधीही ओटीपी (OTP) किंवा वैयक्तिक संदेश वाचणार नाही.",
        "आम्ही आपला डेटा कोणालाही विकणार नाही.",
      ],
      yourControlTitle: "आपले नियंत्रण",
      yourControlPoints: [
        "आपण नकार देऊ शकता आणि मॅन्युअली खर्च नोंदवू शकता.",
        "गोपनीयता सेटिंग्जमधून आपण केव्हाही परवानगी मागे घेऊ शकता.",
      ],
      privacyPolicyText: "गोपनीयता धोरण",
      termsText: "अटी व शर्ती",
      allowButtonText: "परवानगी द्या",
      notNowButtonText: "आता नाही",
    },
    statement_upload: {
      title: "FinTrack AI आपण अपलोड केलेले स्टेटमेंट वाचू इच्छित आहे",
      subtitle:
        "बँक स्टेटमेंट तपासण्यापूर्वी आम्ही आपली परवानगी घेतो. मूळ फाईल डिस्कवर साठवली जात नाही.",
      whatWeAccessTitle: "आम्ही कशात प्रवेश करू",
      whatWeAccessPoints: [
        "केवळ आपण अपलोड केलेली विशिष्ट CSV किंवा PDF फाईल.",
        "आपल्या उपकरणावरील इतर कोणत्याही फायलींमध्ये प्रवेश नाही.",
      ],
      whatWeUseItForTitle: "आम्ही कशासाठी वापरतो",
      whatWeUseItForPoints: [
        "व्यवहारांचे तपशील मिळवून खर्चाची नोंद ठेवण्यासाठी.",
        "खर्चांचे विश्लेषण आणि अंदाज वर्तवण्यासाठी.",
      ],
      whatWeWillNotDoTitle: "आम्ही काय कधीही करणार नाही",
      whatWeWillNotDoPoints: [
        "प्रोसेसिंग पूर्ण झाल्यावर आम्ही मूळ फाईल सर्व्हरवर कधीही साठवून ठेवत नाही.",
        "आम्ही कधीही थेट बँक खात्यातून पैसे हलवणार नाही.",
      ],
      yourControlTitle: "आपले नियंत्रण",
      yourControlPoints: [
        "आपण केव्हाही परवानगी मागे घेऊ शकता आणि डेटा नष्ट करू शकता.",
      ],
      privacyPolicyText: "गोपनीयता धोरण",
      termsText: "अटी व शर्ती",
      allowButtonText: "परवानगी द्या",
      notNowButtonText: "आता नाही",
    },
  },
};

