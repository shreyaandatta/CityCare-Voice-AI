"""Sample calls with the triage label a human receptionist would expect."""
SAMPLES = [
    ("Routine check-up", "Hi, I want to book a routine checkup with general medicine, any time next month.", "Routine"),
    ("Report collection", "I just want to know if my blood test report is ready, I can come next week.", "Routine"),
    ("Mild cold", "I have a cough and a sore throat, can I see a doctor next week?", "Routine"),
    ("Negated symptoms", "Follow-up visit for my knee. No pain, no swelling now. Anytime this month is fine, whenever.", "Routine"),
    ("Fever + worried", "I have had a fever for three days and I'm worried, please can I come this week?", "Urgent"),
    ("Child with fever", "My child is 4 years old and has high fever since morning, can we come tomorrow?", "Urgent"),
    ("Pregnant + dizzy", "I am pregnant and feeling dizzy with a headache, when can I see the gynaecologist?", "Urgent"),
    ("Fracture", "I fell and I think my wrist is broken, there is swelling and pain, can I come today?", "Urgent"),
    ("Chest pain elderly", "Please help! My father is 70 years old and has chest pain and is breathless!", "Emergency"),
    ("Stroke signs", "My mother's face drooping and she has slurred speech, what do I do?", "Emergency"),
    ("Unconscious", "Someone collapsed and is unconscious, please hurry!", "Emergency"),
    ("Hinglish emergency", "Jaldi madad karo, papa behosh ho gaye hain, saans nahi aa rahi!", "Emergency"),
]
