// Interface text in Tamil, Hindi and English.
// Tamil and Hindi were written for the prototype; have a native speaker review before a field pilot.

export type Lang = "ta" | "hi" | "en";
export const LANGS: { id: Lang; name: string; speech: string }[] = [
  { id: "ta", name: "தமிழ்", speech: "ta-IN" },
  { id: "hi", name: "हिन्दी", speech: "hi-IN" },
  { id: "en", name: "English", speech: "en-IN" },
];

const S = {
  appName: { en: "SchemeSathi", ta: "திட்டச் சாதி", hi: "स्कीम साथी" },
  tagline: {
    en: "Find the government schemes you can get. Just speak.",
    ta: "உங்களுக்குக் கிடைக்கும் அரசுத் திட்டங்களைக் கண்டறியுங்கள். பேசினால் போதும்.",
    hi: "जानिए कौन सी सरकारी योजनाएँ आपको मिल सकती हैं। बस बोलिए।",
  },
  chooseLanguage: { en: "Choose your language", ta: "உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்", hi: "अपनी भाषा चुनें" },
  helperMode: { en: "I am helping others (Sahayak)", ta: "நான் மற்றவர்களுக்கு உதவுகிறேன் (சகாயக்)", hi: "मैं दूसरों की मदद करता/करती हूँ (सहायक)" },
  consentTitle: { en: "Before we start", ta: "தொடங்கும் முன்", hi: "शुरू करने से पहले" },
  consentBody: {
    en: "I will ask about your age, family, income and documents to find schemes for you. I keep only what you tell me, never your full Aadhaar number, and photos of documents are not saved. You can delete everything at any time from the menu. The final decision on any scheme is made by the government office.",
    ta: "உங்களுக்கான திட்டங்களைக் கண்டறிய உங்கள் வயது, குடும்பம், வருமானம், ஆவணங்கள் பற்றிக் கேட்பேன். நீங்கள் சொல்வதை மட்டுமே வைத்திருப்பேன்; முழு ஆதார் எண்ணை ஒருபோதும் சேமிக்க மாட்டேன்; ஆவணப் புகைப்படங்கள் சேமிக்கப்படாது. பட்டியலில் இருந்து எப்போது வேண்டுமானாலும் அனைத்தையும் நீக்கலாம். எந்தத் திட்டத்திலும் இறுதி முடிவை அரசு அலுவலகமே எடுக்கும்.",
    hi: "आपके लिए योजनाएँ खोजने हेतु मैं आपकी उम्र, परिवार, आय और दस्तावेज़ों के बारे में पूछूँगा। मैं केवल वही रखता हूँ जो आप बताते हैं, आपका पूरा आधार नंबर कभी नहीं, और दस्तावेज़ों की फ़ोटो सेव नहीं होती। आप मेनू से कभी भी सब कुछ मिटा सकते हैं। किसी भी योजना पर अंतिम निर्णय सरकारी कार्यालय करेगा।",
  },
  agree: { en: "I agree, let's start", ta: "ஒப்புக்கொள்கிறேன், தொடங்குவோம்", hi: "मैं सहमत हूँ, शुरू करें" },
  listen: { en: "Listen", ta: "கேட்க", hi: "सुनें" },
  tapToSpeak: { en: "Tap and speak", ta: "தொட்டுப் பேசுங்கள்", hi: "दबाएँ और बोलें" },
  listening: { en: "Listening… tap to stop", ta: "கேட்கிறேன்… நிறுத்தத் தொடவும்", hi: "सुन रहा हूँ… रोकने के लिए दबाएँ" },
  thinking: { en: "Thinking…", ta: "யோசிக்கிறேன்…", hi: "सोच रहा हूँ…" },
  typeInstead: { en: "Type instead", ta: "தட்டச்சு செய்ய", hi: "टाइप करें" },
  speakInstead: { en: "Speak instead", ta: "பேச", hi: "बोलें" },
  send: { en: "Send", ta: "அனுப்பு", hi: "भेजें" },
  typeHere: { en: "Type your answer", ta: "உங்கள் பதிலைத் தட்டச்சு செய்யவும்", hi: "अपना जवाब लिखें" },
  done: { en: "Done", ta: "முடிந்தது", hi: "हो गया" },
  seeSchemes: { en: "See my schemes", ta: "என் திட்டங்கள்", hi: "मेरी योजनाएँ" },
  seeSchemesSoFar: { en: "See schemes so far", ta: "இதுவரை உள்ள திட்டங்கள்", hi: "अब तक की योजनाएँ" },
  noMic: {
    en: "Voice is not available on this phone's browser. You can tap the answers or type.",
    ta: "இந்தக் கைபேசி உலாவியில் குரல் வசதி இல்லை. பதில்களைத் தொடலாம் அல்லது தட்டச்சு செய்யலாம்.",
    hi: "इस फ़ोन के ब्राउज़र में आवाज़ की सुविधा नहीं है। आप जवाब दबा सकते हैं या टाइप कर सकते हैं।",
  },
  micDenied: {
    en: "Microphone permission is off. Allow it in the browser settings, or type.",
    ta: "மைக் அனுமதி இல்லை. உலாவி அமைப்பில் அனுமதிக்கவும், அல்லது தட்டச்சு செய்யவும்.",
    hi: "माइक की अनुमति बंद है। ब्राउज़र सेटिंग में अनुमति दें, या टाइप करें।",
  },
  noVoiceOut: {
    en: "This phone has no voice for this language, so replies are shown as text.",
    ta: "இந்த மொழிக்கான குரல் இந்தக் கைபேசியில் இல்லை; பதில்கள் எழுத்தாகக் காட்டப்படும்.",
    hi: "इस फ़ोन में इस भाषा की आवाज़ नहीं है, इसलिए जवाब लिखकर दिखाए जाएँगे।",
  },
  heard: { en: "You said", ta: "நீங்கள் சொன்னது", hi: "आपने कहा" },
  noneOfThese: { en: "None of these", ta: "இவை எதுவும் இல்லை", hi: "इनमें से कोई नहीं" },
  // results
  yourSchemes: { en: "Schemes you may get", ta: "உங்களுக்குக் கிடைக்கக்கூடிய திட்டங்கள்", hi: "योजनाएँ जो आपको मिल सकती हैं" },
  likelyEligible: { en: "Likely eligible", ta: "தகுதி உண்டு", hi: "पात्र" },
  almost: { en: "Almost — one thing is missing", ta: "கிட்டத்தட்ட — ஒன்று மட்டும் குறைவு", hi: "लगभग — एक बात कम है" },
  needInfo: { en: "I need a little more information", ta: "இன்னும் கொஞ்சம் தகவல் தேவை", hi: "थोड़ी और जानकारी चाहिए" },
  answerMore: { en: "Answer a few more questions", ta: "இன்னும் சில கேள்விகளுக்குப் பதிலளிக்கவும்", hi: "कुछ और सवालों के जवाब दें" },
  why: { en: "Why", ta: "ஏன்", hi: "क्यों" },
  whyNot: { en: "What is missing", ta: "என்ன குறைவு", hi: "क्या कम है" },
  benefit: { en: "What you get", ta: "என்ன கிடைக்கும்", hi: "क्या मिलेगा" },
  whereToApply: { en: "Where to apply", ta: "எங்கே விண்ணப்பிப்பது", hi: "कहाँ आवेदन करें" },
  officeChecks: { en: "The office will also check", ta: "அலுவலகம் இவற்றையும் சரிபார்க்கும்", hi: "कार्यालय यह भी जाँचेगा" },
  source: { en: "Official rule", ta: "அதிகாரப்பூர்வ விதி", hi: "आधिकारिक नियम" },
  sourceSecondary: { en: "Summary of the rule", ta: "விதியின் சுருக்கம்", hi: "नियम का सारांश" },
  getPacket: { en: "Get my application packet", ta: "விண்ணப்பத் தொகுப்பைப் பெறுக", hi: "आवेदन पैकेट लें" },
  open: { en: "Open", ta: "திற", hi: "खोलें" },
  noneYet: {
    en: "No scheme fits yet with what you told me. The ones below are close.",
    ta: "நீங்கள் சொன்னவற்றின்படி இப்போது பொருந்தும் திட்டம் இல்லை. கீழே உள்ளவை நெருக்கமானவை.",
    hi: "आपकी बताई जानकारी से अभी कोई योजना नहीं बैठती। नीचे वाली करीब हैं।",
  },
  heads_up: { en: "Please note", ta: "கவனிக்கவும்", hi: "ध्यान दें" },
  comingUp: { en: "Coming up for you", ta: "விரைவில் உங்களுக்கு", hi: "जल्द आपके लिए" },
  inYears: { en: "at age {age}, in {n} years", ta: "{age} வயதில், {n} ஆண்டுகளில்", hi: "{age} वर्ष की आयु में, {n} साल बाद" },
  notEligibleAll: { en: "Other schemes I checked", ta: "நான் சரிபார்த்த பிற திட்டங்கள்", hi: "अन्य जाँची गई योजनाएँ" },
  // scheme page
  documents: { en: "Documents to carry", ta: "எடுத்துச் செல்ல வேண்டிய ஆவணங்கள்", hi: "साथ ले जाने वाले दस्तावेज़" },
  docOk: { en: "Checked", ta: "சரிபார்க்கப்பட்டது", hi: "जाँचा गया" },
  docProblem: { en: "Problem found", ta: "பிழை உள்ளது", hi: "समस्या मिली" },
  docMissing: { en: "Not added yet", ta: "இன்னும் சேர்க்கவில்லை", hi: "अभी नहीं जोड़ा" },
  checkPhoto: { en: "Check with a photo", ta: "புகைப்படம் மூலம் சரிபார்", hi: "फ़ोटो से जाँचें" },
  iHaveIt: { en: "I have it", ta: "என்னிடம் உள்ளது", hi: "मेरे पास है" },
  downloadPdf: { en: "Download PDF for the office", ta: "அலுவலகத்திற்கான PDF பதிவிறக்கு", hi: "कार्यालय के लिए PDF डाउनलोड करें" },
  print: { en: "Print this checklist", ta: "இந்தப் பட்டியலை அச்சிடு", hi: "यह सूची प्रिंट करें" },
  askQuestion: { en: "Ask about this scheme", ta: "இந்தத் திட்டம் பற்றிக் கேளுங்கள்", hi: "इस योजना के बारे में पूछें" },
  askPlaceholder: { en: "e.g. How much money will I get?", ta: "எ.கா. எவ்வளவு பணம் கிடைக்கும்?", hi: "जैसे: कितने पैसे मिलेंगे?" },
  ask: { en: "Ask", ta: "கேள்", hi: "पूछें" },
  basedOn: { en: "Based on", ta: "ஆதாரம்", hi: "आधार" },
  back: { en: "Back", ta: "பின்", hi: "वापस" },
  // documents
  docDoctor: { en: "Document Doctor", ta: "ஆவண மருத்துவர்", hi: "दस्तावेज़ डॉक्टर" },
  docDoctorIntro: {
    en: "Take a photo of a certificate. I will check the name, the dates and whether it can be read — before the office does.",
    ta: "சான்றிதழை புகைப்படம் எடுங்கள். பெயர், தேதிகள், படிக்கக்கூடியதா என்பதை அலுவலகத்திற்கு முன்பே சரிபார்க்கிறேன்.",
    hi: "प्रमाणपत्र की फ़ोटो लें। मैं नाम, तारीखें और पढ़ने लायक है या नहीं — कार्यालय से पहले जाँच लूँगा।",
  },
  docConsent: {
    en: "I agree that this photo is read once to check it, and then discarded. Only the name, dates and last 4 Aadhaar digits are kept for 24 hours.",
    ta: "இந்தப் புகைப்படம் சரிபார்க்க ஒருமுறை படிக்கப்பட்டு பின் நீக்கப்படும் என்பதை ஒப்புக்கொள்கிறேன். பெயர், தேதிகள், ஆதாரின் கடைசி 4 இலக்கங்கள் மட்டும் 24 மணி நேரம் வைக்கப்படும்.",
    hi: "मैं सहमत हूँ कि यह फ़ोटो एक बार जाँच के लिए पढ़ी जाएगी, फिर हटा दी जाएगी। केवल नाम, तारीखें और आधार के अंतिम 4 अंक 24 घंटे रखे जाएँगे।",
  },
  yourName: { en: "Your name, as on Aadhaar", ta: "ஆதாரில் உள்ளபடி உங்கள் பெயர்", hi: "आधार पर लिखा आपका नाम" },
  save: { en: "Save", ta: "சேமி", hi: "सहेजें" },
  takePhoto: { en: "Take or choose a photo", ta: "புகைப்படம் எடு அல்லது தேர்ந்தெடு", hi: "फ़ोटो लें या चुनें" },
  docType: { en: "Which document?", ta: "எந்த ஆவணம்?", hi: "कौन सा दस्तावेज़?" },
  detectAuto: { en: "Detect automatically", ta: "தானாகக் கண்டறி", hi: "अपने आप पहचानें" },
  checking: { en: "Checking the photo…", ta: "புகைப்படத்தைச் சரிபார்க்கிறேன்…", hi: "फ़ोटो जाँच रहा हूँ…" },
  allGood: { en: "Looks good. No problems found.", ta: "நன்றாக உள்ளது. பிழை எதுவும் இல்லை.", hi: "ठीक है। कोई समस्या नहीं मिली।" },
  enterByHand: { en: "Enter the details by hand", ta: "விவரங்களைக் கையால் உள்ளிடு", hi: "विवरण हाथ से भरें" },
  validUntil: { en: "Valid until (dd/mm/yyyy)", ta: "செல்லுபடி தேதி (dd/mm/yyyy)", hi: "वैध तिथि (dd/mm/yyyy)" },
  issueDate: { en: "Date of issue (dd/mm/yyyy)", ta: "வழங்கிய தேதி (dd/mm/yyyy)", hi: "जारी करने की तिथि (dd/mm/yyyy)" },
  nameOnDoc: { en: "Name on the document", ta: "ஆவணத்தில் உள்ள பெயர்", hi: "दस्तावेज़ पर नाम" },
  yourDocs: { en: "Checked documents", ta: "சரிபார்த்த ஆவணங்கள்", hi: "जाँचे गए दस्तावेज़" },
  deletesIn24: { en: "Deleted automatically in 24 hours", ta: "24 மணி நேரத்தில் தானாக நீக்கப்படும்", hi: "24 घंटे में अपने आप हट जाएगा" },
  keep: { en: "Keep it", ta: "வைத்திரு", hi: "रखें" },
  remove: { en: "Remove", ta: "நீக்கு", hi: "हटाएँ" },
  kept: { en: "Kept until you delete it", ta: "நீங்கள் நீக்கும் வரை வைக்கப்படும்", hi: "आपके हटाने तक रखा जाएगा" },
  // menu
  menu: { en: "Menu", ta: "பட்டியல்", hi: "मेनू" },
  talk: { en: "Talk to Sathi", ta: "சாதியுடன் பேசு", hi: "साथी से बात करें" },
  myAnswers: { en: "My answers", ta: "என் பதில்கள்", hi: "मेरे जवाब" },
  privacy: { en: "My data and privacy", ta: "என் தரவு மற்றும் தனியுரிமை", hi: "मेरा डेटा और गोपनीयता" },
  deleteAll: { en: "Delete all my data", ta: "என் தரவு அனைத்தையும் நீக்கு", hi: "मेरा सारा डेटा मिटाएँ" },
  deleteConfirm: {
    en: "This deletes your answers, documents and conversation from SchemeSathi. It cannot be undone.",
    ta: "இது உங்கள் பதில்கள், ஆவணங்கள், உரையாடலை நீக்கும். திரும்பப் பெற முடியாது.",
    hi: "यह आपके जवाब, दस्तावेज़ और बातचीत मिटा देगा। इसे वापस नहीं लाया जा सकता।",
  },
  deleteYes: { en: "Yes, delete everything", ta: "ஆம், அனைத்தையும் நீக்கு", hi: "हाँ, सब मिटाएँ" },
  cancel: { en: "Cancel", ta: "ரத்து", hi: "रद्द करें" },
  deleted: { en: "Your data has been deleted.", ta: "உங்கள் தரவு நீக்கப்பட்டது.", hi: "आपका डेटा मिटा दिया गया।" },
  startAgain: { en: "Start again", ta: "மீண்டும் தொடங்கு", hi: "फिर से शुरू करें" },
  // sahayak
  families: { en: "Families I am helping", ta: "நான் உதவும் குடும்பங்கள்", hi: "जिन परिवारों की मदद कर रहा/रही हूँ" },
  addFamily: { en: "Add a person", ta: "ஒருவரைச் சேர்", hi: "व्यक्ति जोड़ें" },
  personName: { en: "Name or label", ta: "பெயர் அல்லது குறிப்பு", hi: "नाम या पहचान" },
  helping: { en: "Now helping", ta: "இப்போது உதவுவது", hi: "अभी मदद" },
  switchTo: { en: "Switch", ta: "மாற்று", hi: "बदलें" },
  schemesFound: { en: "{n} schemes", ta: "{n} திட்டங்கள்", hi: "{n} योजनाएँ" },
  noFamilies: { en: "Add the first person you are helping today.", ta: "இன்று நீங்கள் உதவும் முதல் நபரைச் சேர்க்கவும்.", hi: "आज जिसकी मदद कर रहे हैं, उसे जोड़ें।" },
  quickEntry: { en: "Quick entry", ta: "விரைவுப் பதிவு", hi: "त्वरित प्रविष्टि" },
  // answers
  answersIntro: { en: "This is what you told me. Tap a value to change it.", ta: "நீங்கள் சொன்னவை இவை. மாற்ற தொடவும்.", hi: "आपने यह बताया है। बदलने के लिए दबाएँ।" },
  notAnswered: { en: "Not answered", ta: "பதில் இல்லை", hi: "जवाब नहीं" },
  clear: { en: "Clear", ta: "அழி", hi: "हटाएँ" },
  offline: { en: "No internet connection. Your answers are safe; try again when you are online.", ta: "இணைய இணைப்பு இல்லை. உங்கள் பதில்கள் பாதுகாப்பாக உள்ளன; இணைப்பு வந்ததும் முயலவும்.", hi: "इंटरनेट नहीं है। आपके जवाब सुरक्षित हैं; ऑनलाइन होने पर फिर कोशिश करें।" },
  error: { en: "Something went wrong", ta: "ஏதோ தவறு நடந்தது", hi: "कुछ गड़बड़ हुई" },
  finalDecision: { en: "This is guidance only. The final decision is made by the department.", ta: "இது வழிகாட்டுதல் மட்டுமே. இறுதி முடிவை அரசுத் துறையே எடுக்கும்.", hi: "यह केवल मार्गदर्शन है। अंतिम निर्णय विभाग करेगा।" },
  privacyBody: {
    en: "What SchemeSathi keeps: the answers you give (age, family, income and so on), your conversation, and for each checked document only the name, dates and last 4 Aadhaar digits. Document photos are read once and never saved. Checked documents are deleted after 24 hours unless you keep them. Inactive profiles are deleted after 90 days. Your phone keeps a private key so only you can open your profile.",
    ta: "திட்டச் சாதி வைத்திருப்பவை: நீங்கள் தரும் பதில்கள் (வயது, குடும்பம், வருமானம் போன்றவை), உரையாடல், ஒவ்வொரு ஆவணத்திற்கும் பெயர், தேதிகள், ஆதாரின் கடைசி 4 இலக்கங்கள் மட்டும். ஆவணப் புகைப்படங்கள் ஒருமுறை படிக்கப்பட்டு சேமிக்கப்படுவதில்லை. நீங்கள் வைத்திருக்கச் சொன்னால் தவிர, ஆவண விவரங்கள் 24 மணி நேரத்தில் நீக்கப்படும். 90 நாள் பயன்படுத்தாத சுயவிவரங்கள் நீக்கப்படும்.",
    hi: "स्कीम साथी क्या रखता है: आपके जवाब (उम्र, परिवार, आय आदि), आपकी बातचीत, और हर जाँचे गए दस्तावेज़ का केवल नाम, तारीखें और आधार के अंतिम 4 अंक। दस्तावेज़ों की फ़ोटो एक बार पढ़ी जाती हैं, कभी सेव नहीं होतीं। जाँचे गए दस्तावेज़ 24 घंटे बाद हट जाते हैं, जब तक आप उन्हें न रखें। 90 दिन निष्क्रिय प्रोफ़ाइल हटा दी जाती हैं।",
  },
} as const;

export type Key = keyof typeof S;

export function t(key: Key, lang: Lang, vars?: Record<string, string | number>): string {
  let s: string = S[key][lang] ?? S[key].en;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, String(v));
  return s;
}

export function speechLang(lang: Lang): string {
  return LANGS.find((l) => l.id === lang)?.speech ?? "en-IN";
}
