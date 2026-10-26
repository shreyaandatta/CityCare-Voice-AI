"""
Build a training set by combining symptom phrases with everyday sentence
templates. The hand-written phrases in test_data.csv are kept separate
and used only for testing.
"""
import csv, random
from pathlib import Path

random.seed(7)
SYMPTOMS = {
    "Cardiology": ["chest pain", "chest tightness", "heart palpitations", "fast heartbeat", "irregular heartbeat",
                   "high blood pressure", "pain in the left arm", "breathlessness on climbing stairs",
                   "swollen feet and breathlessness", "heart problem", "angina", "high cholesterol",
                   "pressure in the chest", "heart attack symptoms", "seene mein dard", "dil ki dhadkan tez",
                   "a heart checkup and ecg", "bp problem"],
    "Orthopaedics": ["knee pain", "back pain", "a broken bone", "a fractured arm", "a sprained ankle", "joint pain",
                     "shoulder pain", "neck stiffness", "hip pain", "a slipped disc", "arthritis",
                     "a bone injury", "ligament injury", "heel pain", "wrist pain after a fall", "ghutne mein dard",
                     "kamar dard", "a plaster that needs removing"],
    "Paediatrics": ["fever", "cough", "diarrhoea", "a rash", "vomiting", "not eating", "crying all night",
                    "ear pain", "cold", "chickenpox", "jaundice", "a vaccination due", "growth concerns",
                    "weakness", "bukhar", "loose motions"],
    "General Medicine": ["fever and body ache", "a cold and cough", "weakness and tiredness", "stomach pain",
                         "acidity", "diabetes", "high sugar levels", "viral fever", "loose motions", "typhoid",
                         "dengue symptoms", "a thyroid problem", "loss of appetite", "a general health checkup",
                         "bukhar aur badan dard", "pet mein dard", "malaria symptoms", "body pain"],
    "Gynaecology": ["missed periods", "irregular periods", "period pain", "a pregnancy scan", "pregnancy checkup",
                    "white discharge", "pcos", "bleeding during pregnancy", "menopause symptoms",
                    "lower abdominal pain", "fertility issues", "family planning", "heavy periods",
                    "an antenatal visit", "morning sickness in pregnancy", "dizziness while pregnant", "pregnancy problems"],
    "Neurology": ["a severe headache", "migraine", "numbness in the hands", "a seizure", "fits", "face drooping",
                  "slurred speech", "memory loss", "tingling in the legs", "paralysis on one side",
                  "a head injury", "tremors", "fainting spells", "vertigo", "nerve pain", "sir mein dard",
                  "stroke symptoms", "loss of balance"],
    "ENT": ["ear pain", "hearing loss", "a sore throat", "a blocked nose", "sinus problems", "swollen tonsils",
            "a nose bleed", "ringing in the ears", "a hoarse voice", "something stuck in the throat",
            "ear wax", "snoring", "a throat infection", "difficulty swallowing", "kaan mein dard",
            "gale mein kharash", "ear discharge"],
    "Dermatology": ["a skin rash", "itching", "acne", "hair fall", "dandruff", "a skin allergy", "eczema",
                    "a fungal infection", "dark spots", "psoriasis", "a changing mole", "pimples",
                    "peeling skin", "a nail infection", "hives", "khujli", "skin burns", "dry patchy skin", "itchy red skin", "a rash on the arms"],
}
ADULT = ["I have {s}", "I've been having {s} for a few days", "my {who} has {s}", "need an appointment for {s}",
         "suffering from {s} since yesterday", "can I see a doctor about {s}", "{s}, what should I do",
         "I am calling about {s}", "mujhe {s} hai", "{s} for a week now", "doctor chahiye, {s} hai",
         "my {who} is having {s}"]
CHILD = ["my baby has {s}", "my child has {s}", "my {kid} has {s}", "my 2 year old has {s}", "bacche ko {s} hai",
         "my {kid} is having {s} since morning", "infant with {s}", "toddler has {s}", "my newborn has {s}",
         "my 5 year old {kid} has {s}", "need a paediatrician, my {kid} has {s}", "school kid with {s}"]
WHO = ["father", "mother", "wife", "husband", "grandfather", "sister", "brother", "friend"]
KID = ["son", "daughter", "kid", "child", "baby"]
WOMEN = ["wife", "mother", "sister"]

rows = []
for dept, symptoms in SYMPTOMS.items():
    templates = CHILD if dept == "Paediatrics" else ADULT
    for s in symptoms:
        for t in random.sample(templates, 8):
            who = random.choice(WOMEN if dept == "Gynaecology" else WHO)
            rows.append((t.format(s=s, who=who, kid=random.choice(KID)), dept))
random.shuffle(rows)
with open(Path(__file__).parent / "train_data.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["text", "department"]); w.writerows(rows)
print(len(rows), "training rows written")
