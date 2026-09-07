from tk_runtime import prepare_tk

prepare_tk()

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import json
import os
import hashlib
import hmac
import math
import re
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import speech_recognition as sr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
KB_FILE = os.path.join(BASE_DIR, "knowledge_base.json")
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.json")
HISTORY_DIR = os.path.join(BASE_DIR, "histories")
BG_IMAGE = os.getenv("MEDICAL_APP_BG", os.path.join(BASE_DIR, "aibg.jpg"))

# Extended knowledge base with all rules including new vitals-based diagnoses
default_kb = [
    (("fever", "cough"), "flu", 0.8),
    (("fever", "cough", "shortness_of_breath"), "pneumonia", 0.9),
    (("headache", "nausea"), "migraine", 0.7),
    (("fever", "rash"), "measles", 0.85),
    (("sore_throat", "cough"), "common_cold", 0.6),
    (("fever", "chills", "sweating"), "malaria", 0.9),
    (("abdominal_pain", "diarrhea"), "food_poisoning", 0.75),
    (("fatigue", "weight_loss"), "diabetes", 0.6),
    (("chest_pain", "shortness_of_breath"), "heart_attack", 0.85),
    (("high_sugar", "frequent_urination"), "diabetes", 0.7),
    (("high_bp", "chest_pain"), "hypertension", 0.75),
    (("high_temp",), "infection", 0.6),
    (("loss_of_smell", "loss_of_taste"), "covid_19", 0.85),
    (("tachycardia",), "arrhythmia", 0.7),
    (("bradycardia",), "heart_block", 0.65),
    (("low_oxygen",), "hypoxemia", 0.8),
    (("low_oxygen", "shortness_of_breath"), "respiratory_failure", 0.9),
]

# NLP patterns for symptom extraction
NLP_PATTERNS = {
    'positive_indicators': [
        r'\bi\s+have\b', r'\bi\s+feel\b', r'\bi\s+am\s+experiencing\b', 
        r'\bi\s+suffer\s+from\b', r'\bi\s+get\b', r'\bthere\s+is\b',
        r'\bi\s+experience\b', r'\bi\s+notice\b', r'\bi\s+developed\b'
    ],
    'negative_indicators': [
        r'\bi\s+can\'?t\b', r'\bi\s+don\'?t\s+have\b', r'\bi\s+can\'?t\s+\w+\b', 
        r'\bi\s+cannot\b', r'\bno\s+', r'\bnot\s+', r'\bwithout\s+', 
        r'\bi\s+don\'?t\s+feel\b', r'\bi\s+lack\b'
    ],
    'symptom_modifiers': [
        r'\bsevere\b', r'\bmoderate\b', r'\bmild\b', r'\bchronic\b', 
        r'\bacute\b', r'\bintense\b', r'\bsharp\b', r'\bdull\b', 
        r'\bpersistent\b'
    ]
}

# Symptom synonyms and related terms, including verb forms and negated phrases
SYMPTOM_SYNONYMS = {
    'fever': ['temperature', 'hot', 'burning', 'feverish', 'hyperthermia'],
    'headache': ['head pain', 'migraine', 'head ache', 'cranial pain'],
    'cough': ['coughing', 'hack', 'throat clearing'],
    'nausea': ['sick', 'queasy', 'nauseated', 'stomach upset'],
    'fatigue': ['tired', 'exhausted', 'weakness', 'lethargy', 'drowsy'],
    'chest_pain': ['chest ache', 'heart pain', 'thoracic pain'],
    'shortness_of_breath': ['breathing difficulty', 'breathless', 'dyspnea', 'cant breathe'],
    'abdominal_pain': ['stomach pain', 'belly ache', 'tummy ache', 'gut pain'],
    'diarrhea': ['loose stool', 'watery stool', 'stomach runs'],
    'sore_throat': ['throat pain', 'throat ache', 'painful swallowing'],
    'weight_loss': ['losing weight', 'getting thin', 'weight reduction'],
    'frequent_urination': ['urinating often', 'peeing frequently', 'bathroom trips'],
    'loss_of_smell': ['cant smell', 'cannot smell', 'no smell', 'lost sense of smell', 'smell loss', 'smelling nothing'],
    'loss_of_taste': ['cant taste', 'cannot taste', 'no taste', 'lost sense of taste', 'taste loss', 'tasteless', 'tasting nothing'],
    'tachycardia': ['fast heart', 'rapid pulse', 'racing heart'],
    'bradycardia': ['slow heart', 'low pulse'],
    'low_oxygen': ['low oxygen levels', 'poor oxygenation', 'hypoxia']
}

common_symptoms = sorted(set(s for rule in default_kb for s in rule[0] if not s.startswith("high_")))
users = json.load(open(USERS_FILE)) if os.path.exists(USERS_FILE) else {}
knowledge_base = json.load(open(KB_FILE)) if os.path.exists(KB_FILE) else default_kb
feedback = json.load(open(FEEDBACK_FILE)) if os.path.exists(FEEDBACK_FILE) else {}

os.makedirs(HISTORY_DIR, exist_ok=True)

def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
PBKDF2_ITERATIONS = 600_000


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, encoded):
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(candidate, bytes.fromhex(digest_hex))
    except (AttributeError, TypeError, ValueError):
        return False

def advanced_nlp_symptom_extraction(text):
    """Advanced NLP processing for symptom extraction with severity and negation support"""
    text = text.lower().strip()
    
    # Get all symptoms from knowledge base
    all_symptoms = set()
    for rule in knowledge_base:
        all_symptoms.update(rule[0])
    all_symptoms.update(common_symptoms)
    
    # Include severity-based symptoms
    searchable_symptoms = [s for s in all_symptoms if not s.startswith("high_")]
    severity_prefixes = ['mild_', 'moderate_', 'severe_']
    
    extracted_symptoms = []
    negative_symptoms = []
    
    # Split text into sentences
    sentences = re.split(r'[.!?;]', text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Check for negative indicators
        is_negative = any(re.search(pattern, sentence, re.IGNORECASE) 
                         for pattern in NLP_PATTERNS['negative_indicators'])
        
        # Check for severity modifiers
        severity = None
        for modifier in NLP_PATTERNS['symptom_modifiers']:
            if re.search(r'\b' + modifier + r'\b', sentence, re.IGNORECASE):
                if modifier in ['severe', 'intense', 'sharp']:
                    severity = 'severe_'
                elif modifier in ['moderate', 'persistent']:
                    severity = 'moderate_'
                elif modifier in ['mild', 'dull']:
                    severity = 'mild_'
                break
        
        # Direct symptom matching
        for symptom in searchable_symptoms:
            symptom_words = symptom.replace('_', ' ')
            # Check with and without severity prefix
            for prefix in [severity or '', '']:
                check_symptom = f"{prefix}{symptom}"
                check_words = check_symptom.replace('_', ' ')
                if check_words in sentence or re.search(r'\b' + re.escape(check_words) + r'\b', sentence):
                    if is_negative:
                        negative_symptoms.append(check_symptom)
                    else:
                        extracted_symptoms.append(check_symptom)
                    break
        
        # Synonym matching with verb-based negation handling
        for base_symptom, synonyms in SYMPTOM_SYNONYMS.items():
            if base_symptom not in extracted_symptoms and base_symptom not in negative_symptoms:
                for synonym in synonyms:
                    for prefix in [severity or '', '']:
                        check_symptom = f"{prefix}{base_symptom}"
                        # Handle verb forms like "can't smell" or "can't taste"
                        if re.search(r'\bcan\'?t\s+' + re.escape(synonym.split()[0]) + r'\b', sentence) or \
                           re.search(r'\bcannot\s+' + re.escape(synonym.split()[0]) + r'\b', sentence) or \
                           re.search(r'\b' + re.escape(synonym) + r'\b', sentence):
                            if is_negative or 'cant' in synonym or 'cannot' in synonym or 'no' in synonym:
                                negative_symptoms.append(check_symptom)
                            else:
                                extracted_symptoms.append(check_symptom)
                            break
        
        # Pattern-based extraction for common phrases
        patterns = [
            (r'\bpain\s+in\s+(?:my\s+)?(\w+)', lambda m: f"{m.group(1)}_pain"),
            (r'\b(\w+)\s+pain\b', lambda m: f"{m.group(1)}_pain"),
            (r'\bdifficulty\s+(\w+)', lambda m: f"difficulty_{m.group(1)}"),
            (r'\bhigh\s+(\w+)', lambda m: f"high_{m.group(1)}"),
            (r'\blow\s+(\w+)', lambda m: f"low_{m.group(1)}"),
            (r'\bcan\'?t\s+(\w+)', lambda m: f"loss_of_{m.group(1)}"),
            (r'\bcannot\s+(\w+)', lambda m: f"loss_of_{m.group(1)}"),
            (r'\bno\s+(\w+)', lambda m: f"loss_of_{m.group(1)}"),
        ]
        
        for pattern, transform in patterns:
            matches = re.finditer(pattern, sentence)
            for match in matches:
                symptom = transform(match)
                if any(symptom.replace('_', ' ') in s or s in symptom for s in searchable_symptoms):
                    for prefix in [severity or '', '']:
                        check_symptom = f"{prefix}{symptom}"
                        if is_negative or re.search(r'\bcan\'?t\b|\bcannot\b|\bno\b', sentence):
                            negative_symptoms.append(check_symptom)
                        else:
                            extracted_symptoms.append(check_symptom)
    
    # Remove negated symptoms
    final_symptoms = [s for s in extracted_symptoms if s not in negative_symptoms]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_symptoms = []
    for symptom in final_symptoms:
        if symptom not in seen:
            seen.add(symptom)
            unique_symptoms.append(symptom)
    
    return unique_symptoms

def extract_symptoms_from_text(text):
    """Enhanced symptom extraction with advanced NLP"""
    # Use advanced NLP first
    nlp_symptoms = advanced_nlp_symptom_extraction(text)
    
    # Fallback to basic keyword matching
    text_lower = text.lower()
    keywords = re.findall(r'\b\w+\b', text_lower)
    
    # Get all possible symptoms
    all_symptoms = set()
    for rule in knowledge_base:
        all_symptoms.update(rule[0])
    all_symptoms.update(common_symptoms)
    
    basic_symptoms = []
    for symptom in all_symptoms:
        if not symptom.startswith("high_"):
            symptom_words = symptom.replace('_', ' ').split()
            if all(word in keywords for word in symptom_words):
                basic_symptoms.append(symptom)
    
    # Combine and deduplicate
    combined_symptoms = list(set(nlp_symptoms + basic_symptoms))
    
    return combined_symptoms

def generate_vitals_symptoms(vitals):
    """Generate nuanced symptoms based on vital signs with severity levels"""
    derived = []
    
    # Temperature-based symptoms
    temp = vitals.get("temperature", 0)
    if temp >= 104:
        derived.append("severe_fever")
    elif temp >= 102:
        derived.append("moderate_fever")
    elif temp >= 100.4:
        derived.append("mild_fever")
    
    # Include fever field if provided
    fever = vitals.get("fever", 0)
    if fever >= 104:
        derived.append("severe_fever")
    elif fever >= 102:
        derived.append("moderate_fever")
    elif fever >= 100.4:
        derived.append("mild_fever")
    
    # Blood sugar-based symptoms
    sugar = vitals.get("sugar", 0)
    if sugar >= 200:
        derived.append("severe_high_sugar")
    elif sugar >= 140:
        derived.append("moderate_high_sugar")
    elif sugar >= 100:
        derived.append("mild_high_sugar")
    
    # Blood pressure-based symptoms
    bp = vitals.get("bloodpressure", "0/0").split("/")
    try:
        systolic, diastolic = map(int, bp)
        if systolic >= 180 or diastolic >= 120:
            derived.append("severe_high_bp")
        elif systolic >= 140 or diastolic >= 90:
            derived.append("moderate_high_bp")
        elif systolic >= 130 or diastolic >= 80:
            derived.append("mild_high_bp")
    except (ValueError, IndexError):
        pass
    
    # Age-based considerations
    age = vitals.get("age", 0)
    if age >= 65:
        derived.append("elderly_age")
    elif age <= 12:
        derived.append("pediatric_age")
    
    # Heart rate-based symptoms
    heart_rate = vitals.get("heart_rate", 0)
    if heart_rate > 100:
        derived.append("tachycardia")
    elif heart_rate < 60:
        derived.append("bradycardia")
    
    # Oxygen level-based symptoms
    oxygen = vitals.get("oxygen_level", 0)
    if oxygen < 90:
        derived.append("low_oxygen")

    # Remove duplicates while preserving order
    return list(dict.fromkeys(derived))

def infer_diseases(symptoms, vitals):
    """Advanced disease inference with partial matching and feedback integration"""
    symptoms = symptoms[:]
    symptoms += generate_vitals_symptoms(vitals)
    results = []
    symptom_set = set(symptoms)
    
    for rule_symptoms, disease, base_conf in knowledge_base:
        rule_set = set(rule_symptoms)
        matched = symptom_set & rule_set
        ratio = len(matched) / len(rule_set) if rule_set else 0
        conf = base_conf * ratio
        
        # Give partial credit for vitals-only matches
        if not matched and any(vitals.values()):
            conf = 0.3 * base_conf

        # Apply feedback learning
        if disease in feedback:
            fb_count = sum(feedback[disease].values())
            conf += 0.05 * math.tanh(fb_count / 3)

        conf = min(conf, 1.0)
        
        if matched or any(vitals.values()):
            results.append((disease, conf, matched, rule_set))

    return sorted(results, key=lambda x: x[1], reverse=True)[:3]

def record_feedback(disease, symptoms, correct):
    """Record user feedback for learning"""
    key = ", ".join(sorted(symptoms))
    if disease not in feedback:
        feedback[disease] = {}
    if key not in feedback[disease]:
        feedback[disease][key] = 0
    feedback[disease][key] += 1 if correct else -1
    
    # Remove entries with too much negative feedback
    if feedback[disease][key] <= -3:
        del feedback[disease][key]
    
    save_json(feedback, FEEDBACK_FILE)

class DiagnosisApp:
    def __init__(self, root, username):
        self.root = root
        self.username = username
        self.root.title("AI Medical Diagnosis System")
        self.root.state('zoomed')
        self.current_symptoms = []
        self.current_diagnosis = ""

        # Window dimensions
        self.width = self.root.winfo_screenwidth()
        self.height = self.root.winfo_screenheight()

        # Load holographic background image
        try:
            bg_image = Image.open(BG_IMAGE).resize((self.width, self.height))
            self.bg = ImageTk.PhotoImage(bg_image)
        except:
            bg_image = Image.new('RGB', (self.width, self.height), color='#1a2a44')  # Dark blue fallback
            self.bg = ImageTk.PhotoImage(bg_image)

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, bg='#1a2a44')
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.bg, anchor="nw")

        # Title
        self.canvas.create_text(self.width // 2, 30, text="AI Medical Diagnosis System", 
                               font=("Helvetica", 22, "bold"), fill="white")

        # Main frame for centered content
        main_frame = tk.Frame(root, bg='#1a2a44', padx=20, pady=20)
        main_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Symptoms Section
        symptoms_frame = tk.LabelFrame(main_frame, text="Symptoms", font=("Segoe UI", 12, "bold"), 
                                      fg="white", bg='#1a2a44', labelanchor="n", padx=10, pady=10)
        symptoms_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.symptom_text = tk.Entry(symptoms_frame, width=50, font=("Segoe UI", 10), bg='#ecf0f1', fg='black')
        self.symptom_text.grid(row=0, column=0, pady=5, sticky="ew")

        self.suggestion_var = tk.StringVar()
        all_kb_symptoms = set()
        for rule in knowledge_base:
            all_kb_symptoms.update(rule[0])
        all_symptoms_list = sorted([s for s in all_kb_symptoms if not s.startswith("high_")])
        
        self.suggestion_dropdown = ttk.Combobox(symptoms_frame, textvariable=self.suggestion_var, 
                                              values=all_symptoms_list, width=30, state="readonly")
        self.suggestion_dropdown.grid(row=1, column=0, pady=5, sticky="ew")
        
        tk.Button(symptoms_frame, text="Add Symptom", command=self.add_symptom, 
                  bg="purple", fg="white", font=("Segoe UI", 10), width=12).grid(row=1, column=1, padx=5, pady=5, sticky="e")
        tk.Button(symptoms_frame, text="Record Voice", command=self.record_voice, 
                  bg="orange", fg="white", font=("Segoe UI", 10), width=12).grid(row=1, column=2, padx=5, pady=5, sticky="e")

        # Vitals Section
        vitals_frame = tk.LabelFrame(main_frame, text="Vitals", font=("Segoe UI", 12, "bold"), 
                                    fg="white", bg='#1a2a44', labelanchor="n", padx=10, pady=10)
        vitals_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.vital_vars = {}
        vital_labels = [("Fever (°F)", 0), ("Sugar (mg/dL)", 1), ("Bloodpressure", 2), 
                        ("Heart Rate (bpm)", 3), ("Oxygen Level (%)", 4)]
        
        for idx, (label_text, row) in enumerate(vital_labels):
            tk.Label(vitals_frame, text=label_text, font=("Segoe UI", 10), fg="white", bg='#1a2a44').grid(row=row, column=0, pady=5, sticky="e")
            var = tk.DoubleVar() if "Bloodpressure" not in label_text else tk.StringVar()
            entry = tk.Entry(vitals_frame, textvariable=var, width=20, bg='#ecf0f1', fg='black')
            entry.grid(row=row, column=1, pady=5, sticky="w")
            self.vital_vars[label_text.replace(" (°F)", "").replace(" (mg/dL)", "").replace(" (bpm)", "").replace(" (%)", "").replace(" ", "_").lower()] = var

        # Diagnosis Section
        diagnosis_frame = tk.LabelFrame(main_frame, text="Possible Diagnosis", font=("Segoe UI", 12, "bold"), 
                                       fg="white", bg='#1a2a44', labelanchor="n", padx=10, pady=10)
        diagnosis_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.output_text = scrolledtext.ScrolledText(diagnosis_frame, width=50, height=5, 
                                                    font=("Consolas", 10), bg='#ecf0f1', fg='black')
        self.output_text.grid(row=0, column=0, pady=5, sticky="nsew")

        # Action Buttons Frame
        action_frame = tk.Frame(main_frame, bg='#1a2a44')
        action_frame.grid(row=3, column=0, padx=10, pady=10, sticky="e")

        tk.Button(action_frame, text="Add Rule", command=self.add_rule, 
                  bg="white", fg="black", font=("Segoe UI", 10), width=10).grid(row=0, column=0, padx=5)
        tk.Button(action_frame, text="Visualize", command=self.visualize_feedback, 
                  bg="white", fg="black", font=("Segoe UI", 10), width=10).grid(row=0, column=1, padx=5)
        tk.Button(action_frame, text="History", command=self.view_history, 
                  bg="white", fg="black", font=("Segoe UI", 10), width=10).grid(row=0, column=2, padx=5)
        tk.Button(action_frame, text="Diagnose", command=self.diagnose, 
                  bg="blue", fg="white", font=("Segoe UI", 10), width=10).grid(row=0, column=3, padx=5)
        tk.Button(action_frame, text="New Diagnosis", command=self.reset_for_new_diagnosis, 
                  bg="orange", fg="white", font=("Segoe UI", 10), width=15).grid(row=0, column=4, padx=5)

        # Feedback Section
        feedback_frame = tk.LabelFrame(main_frame, text="Diagnosis Correct?", font=("Segoe UI", 12, "bold"), 
                                      fg="white", bg='#1a2a44', labelanchor="n", padx=10, pady=10)
        feedback_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

        tk.Button(feedback_frame, text="Yes", command=self.feedback_yes, 
                  bg="limegreen", fg="white", font=("Segoe UI", 10), width=10).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(feedback_frame, text="No", command=self.feedback_no, 
                  bg="red", fg="white", font=("Segoe UI", 10), width=10).grid(row=0, column=1, padx=5, pady=5)

        # Configure grid weights for responsiveness
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)
        main_frame.grid_rowconfigure(4, weight=1)
        for frame in [symptoms_frame, vitals_frame, diagnosis_frame, feedback_frame]:
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(0, weight=1)

    def add_symptom(self):
        """Add selected symptom to the symptoms text area"""
        selected = self.suggestion_var.get().strip()
        if not selected:
            return
        
        current = self.symptom_text.get().strip()
        if current:
            if selected.replace('_', ' ') not in current.lower():
                self.symptom_text.insert(tk.END, f", {selected.replace('_', ' ')}")
        else:
            self.symptom_text.insert(tk.END, selected.replace('_', ' '))
        
        self.suggestion_var.set("")

    def record_voice(self):
        """Record voice input, extract symptoms, and prompt for vitals"""
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            messagebox.showinfo("Voice Input", "Please speak your symptoms now...")
            try:
                audio = recognizer.listen(source, timeout=5)
                text = recognizer.recognize_google(audio).lower()
                self.symptom_text.delete(0, tk.END)
                self.symptom_text.insert(0, text)
                messagebox.showinfo("Success", f"Recognized: {text}")

                # Extract symptoms
                symptoms = extract_symptoms_from_text(text)
                if symptoms:
                    self.collect_vitals()
                else:
                    messagebox.showinfo("Info", "No symptoms detected. Please try again or add manually.")
            except sr.UnknownValueError:
                messagebox.showerror("Error", "Could not understand audio")
            except sr.RequestError as e:
                messagebox.showerror("Error", f"Could not request results; {str(e)}")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def collect_vitals(self):
        """Interactively collect vitals via voice input with enhanced diagnostics"""
        recognizer = sr.Recognizer()
        # Optimize recognizer settings
        recognizer.energy_threshold = 3000  # Adjust sensitivity to ambient noise
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8  # Allow slight pauses between words

        vital_questions = [
            "What's your temperature in Fahrenheit?",
            "What's your sugar level in mg/dL?",
            "What's your blood pressure? Please say it as systolic/diastolic, e.g., 120/80.",
            "What's your heart rate in beats per minute?",
            "What's your oxygen level in percentage?"
        ]
        vital_keys = ["temperature", "sugar", "bloodpressure", "heart_rate", "oxygen_level"]

        # Enhanced dictionary to map number words to digits
        number_words = {
            'zero': 0, 'oh': 0, 'o': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
            'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
            'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
            'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60,
            'seventy': 70, 'eighty': 80, 'ninety': 90,
            'hundred': 100
        }

        def parse_number(text):
            """Enhanced number parsing with detailed logging and fallback"""
            print(f"Parsing text: '{text}'")  # Log the input text
            try:
                # First, try direct digit extraction
                num_match = re.search(r'\d+\.?\d*', text)
                if num_match:
                    result = float(num_match.group())
                    print(f"Parsed result (digit match): {result}")
                    return result
                
                # Then try spelled-out numbers
                text = text.lower().replace(' and ', ' ').replace('-', ' ').split()
                total = 0
                current = 0
                i = 0
                while i < len(text):
                    word = text[i]
                    if word in number_words:
                        value = number_words[word]
                        if value >= 100:  # Handle 'hundred'
                            if i + 1 < len(text) and text[i + 1] in number_words and number_words[text[i + 1]] < 100:
                                current += value * number_words[text[i + 1]]
                                i += 2
                                continue
                            total += current * value
                            current = 0
                        else:
                            current += value
                    i += 1
                result = total + current if total + current > 0 else None
                print(f"Parsed result (spelled): {result}")
                return result
            except Exception as e:
                print(f"Parse error: {str(e)}")
                return None

        attempt_count = 0
        max_attempts = 3  # Increased retries

        with sr.Microphone() as source:
            for question, key in zip(vital_questions, vital_keys):
                while attempt_count < max_attempts:
                    messagebox.showinfo("Voice Input", question)
                    try:
                        # Adjust for ambient noise before listening
                        recognizer.adjust_for_ambient_noise(source, duration=1)
                        audio = recognizer.listen(source, timeout=8)
                        value = recognizer.recognize_google(audio).lower()
                        print(f"Raw recognized text for {question}: '{value}'")  # Detailed debugging
                        if key == "bloodpressure":
                            # Expect format like "120/80"
                            self.vital_vars[key].set(value)
                        else:
                            # Try to extract number
                            num_value = parse_number(value)
                            if num_value is None:
                                raise ValueError(f"Could not parse '{value}' as a number")
                            # Ensure GUI update happens on main thread
                            self.root.after(0, lambda v=num_value, k=key: self.vital_vars[k].set(v))
                        break  # Exit loop if successful
                    except sr.UnknownValueError:
                        messagebox.showerror("Error", f"Could not understand audio for {question}. Attempt {attempt_count + 1} of {max_attempts}. Please speak clearly.")
                    except sr.RequestError as e:
                        messagebox.showerror("Error", f"Could not request results for {question}; {str(e)}")
                    except (ValueError, AttributeError, tk.TclError) as e:
                        messagebox.showerror("Error", f"An error occurred for {question}: {str(e)}. Attempt {attempt_count + 1} of {max_attempts}. Try saying '102', 'one zero two', or 'hundred and two'.")
                    attempt_count += 1
                else:
                    messagebox.showwarning("Fallback", f"Failed to recognize {question} after {max_attempts} attempts. Please enter manually.")
                    manual_value = tk.simpledialog.askstring("Manual Input", f"Enter {question.lower()}:")
                    if manual_value:
                        if key != "bloodpressure":
                            try:
                                self.vital_vars[key].set(float(manual_value))
                            except ValueError:
                                messagebox.showerror("Error", "Invalid number entered. Please use digits.")
                                return
                        else:
                            self.vital_vars[key].set(manual_value)
                    return  # Exit after manual input

                attempt_count = 0  # Reset for next vital

            # Automatically trigger diagnosis after collecting vitals
            self.diagnose()

    def diagnose(self):
        """Perform diagnosis based on symptoms and vitals with enhanced NLP"""
        # Get symptoms from text input using enhanced NLP
        user_input = self.symptom_text.get().strip()
        symptoms = extract_symptoms_from_text(user_input)
        
        # Get vitals
        vitals = {}
        for k, v in self.vital_vars.items():
            if k != "bloodpressure":
                vitals[k] = v.get()
            else:
                vitals[k] = v.get()
        
        # Generate vital signs
        vital_symptoms = generate_vitals_symptoms(vitals)
        
        # Perform inference
        results = infer_diseases(symptoms, vitals)
        
        # Store current diagnosis for feedback
        self.current_symptoms = symptoms
        self.current_diagnosis = results[0][0] if results else ""
        
        # Display results
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        
        # Show extracted symptoms
        self.output_text.insert(tk.END, "Symptoms Analyzed:\n")
        if symptoms:
            self.output_text.insert(tk.END, f"• From Description: {', '.join(s.replace('_', ' ').title() for s in symptoms)}\n")
        else:
            self.output_text.insert(tk.END, "• From Description: None\n")
        
        # Show vital-derived symptoms
        if vital_symptoms:
            self.output_text.insert(tk.END, f"• From Vital Signs: {', '.join(s.replace('_', ' ').title() for s in vital_symptoms)}\n")
        else:
            self.output_text.insert(tk.END, "• From Vital Signs: None\n")
        
        self.output_text.insert(tk.END, f"Original Input: {user_input[:100]}{'...' if len(user_input) > 100 else ''}\n\n")
        
        if not results:
            self.output_text.insert(tk.END, "No diagnosis found based on the provided symptoms and vitals.\n")
            self.output_text.insert(tk.END, "Try adding more specific symptoms or check vital signs.\n")
        else:
            self.output_text.insert(tk.END, "Possible Diagnoses:\n\n")
            for i, (disease, conf, matched, rule) in enumerate(results, 1):
                self.output_text.insert(tk.END, f"{i}. {disease.capitalize()}\n")
                self.output_text.insert(tk.END, f"   Confidence: {conf*100:.1f}%\n")
                self.output_text.insert(tk.END, f"   Matched symptoms: {', '.join(matched) if matched else 'None'}\n")
                self.output_text.insert(tk.END, f"   Rule symptoms: {', '.join(rule)}\n\n")
        
        self.output_text.config(state=tk.DISABLED)
        
        # Save to history
        if symptoms or any(vitals.values()):
            self.save_history(user_input, symptoms, results, vitals)

    def save_history(self, original_input, symptoms, results, vitals):
        """Save diagnosis to user's history with enhanced information"""
        path = os.path.join(HISTORY_DIR, f"{self.username}.json")
        try:
            history = json.load(open(path)) if os.path.exists(path) else []
            if not isinstance(history, list):
                history = []
        except json.JSONDecodeError:
            history = []  # Reset to empty list if file is corrupted
        
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "original_input": original_input,
            "extracted_symptoms": symptoms,
            "vitals": {k: v.get() if hasattr(v, 'get') else v for k, v in vitals.items()},
            "diagnosis": [(d, round(c, 3)) for d, c, *_ in results] if results else [],
            "top_diagnosis": results[0][0] if results else "No diagnosis"
        }
        
        history.append(entry)
        save_json(history, path)

    def feedback_yes(self):
        """Record positive feedback"""
        if self.current_diagnosis:
            record_feedback(self.current_diagnosis, self.current_symptoms, True)
            messagebox.showinfo("Feedback", "Positive feedback recorded. Thank you!")
            self.reset_for_new_diagnosis()

    def feedback_no(self):
        """Record negative feedback"""
        if self.current_diagnosis:
            record_feedback(self.current_diagnosis, self.current_symptoms, False)
            messagebox.showinfo("Feedback", "Negative feedback recorded. This helps improve the system.")
            self.reset_for_new_diagnosis()
    
    def reset_for_new_diagnosis(self):
        """Reset the interface for a new diagnosis"""
        # Clear symptom text area
        self.symptom_text.delete(0, tk.END)
        
        # Clear vital signs
        for var in self.vital_vars.values():
            if isinstance(var, tk.DoubleVar):
                var.set(0)
            else:
                var.set("")
        
        # Clear dropdown selection
        self.suggestion_var.set("")
        
        # Clear results
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "Ready for new diagnosis...\nTry describing your symptoms in natural language!\n")
        self.output_text.config(state=tk.DISABLED)
        
        # Reset current diagnosis variables
        self.current_symptoms = []
        self.current_diagnosis = ""

    def view_history(self):
        """Display user's diagnosis history with enhanced formatting and error handling"""
        path = os.path.join(HISTORY_DIR, f"{self.username}.json")
        win = tk.Toplevel(self.root)
        win.title(f"Diagnosis History - {self.username}")
        win.geometry("900x700")
        
        # Create frame with scrollbar
        main_frame = tk.Frame(win)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add search functionality
        search_frame = tk.Frame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(search_frame, text="Search:", font=("Segoe UI", 10)).pack(side="left")
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side="left", padx=5)
        
        def filter_history():
            display_history(search_var.get().lower())
        
        tk.Button(search_frame, text="Filter", command=filter_history).pack(side="left", padx=5)
        tk.Button(search_frame, text="Show All", command=lambda: display_history("")).pack(side="left")
        
        # Text area for history
        text = scrolledtext.ScrolledText(main_frame, width=100, height=35, font=("Consolas", 9))
        text.pack(fill="both", expand=True)
        
        def display_history(filter_text=""):
            text.config(state=tk.NORMAL)
            text.delete(1.0, tk.END)
            
            try:
                if not os.path.exists(path):
                    text.insert(tk.END, "No diagnosis history file found for this user.\n")
                    text.insert(tk.END, "Start by performing a diagnosis to create history records.")
                    text.config(state=tk.DISABLED)
                    return
                
                with open(path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                if not isinstance(history, list):
                    text.insert(tk.END, "Error: History file contains invalid data. Resetting history.\n")
                    history = []
                    save_json(history, path)
                    return
                
                if not history:
                    text.insert(tk.END, "No diagnosis history found. Perform a diagnosis to add records.")
                    text.config(state=tk.DISABLED)
                    return
                
                filtered_history = history
                if filter_text:
                    filtered_history = [
                        entry for entry in history 
                        if (filter_text in entry.get('original_input', '').lower() or
                            filter_text in str(entry.get('extracted_symptoms', [])).lower() or
                            filter_text in str(entry.get('diagnosis', [])).lower())
                    ]
                
                if not filtered_history:
                    text.insert(tk.END, f"No results found for '{filter_text}'")
                    text.config(state=tk.DISABLED)
                    return
                
                text.insert(tk.END, f"=== DIAGNOSIS HISTORY FOR {self.username.upper()} ===\n")
                text.insert(tk.END, f"Total Records: {len(filtered_history)}\n\n")
                
                for i, entry in enumerate(reversed(filtered_history), 1):  # Show newest first
                    timestamp = entry.get('timestamp', 'Unknown')
                    try:
                        # Validate and format timestamp
                        parsed_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        formatted_time = parsed_time.strftime("%B %d, %Y %I:%M %p")
                    except (ValueError, TypeError):
                        formatted_time = timestamp  # Fallback to raw timestamp if invalid
                    
                    text.insert(tk.END, f"{'='*80}\n")
                    text.insert(tk.END, f"RECORD #{i} - {formatted_time}\n")
                    text.insert(tk.END, f"{'-'*80}\n\n")
                    
                    # Original input
                    original = entry.get('original_input', 'N/A')
                    text.insert(tk.END, f"PATIENT DESCRIPTION:\n")
                    text.insert(tk.END, f'"{original}"\n\n')
                    
                    # Extracted symptoms
                    symptoms = entry.get('extracted_symptoms', [])
                    text.insert(tk.END, f"EXTRACTED SYMPTOMS:\n")
                    if symptoms:
                        for symptom in symptoms:
                            text.insert(tk.END, f"  • {symptom.replace('_', ' ').title()}\n")
                    else:
                        text.insert(tk.END, "  • No symptoms extracted\n")
                    text.insert(tk.END, "\n")
                    
                    # Vitals
                    vitals = entry.get('vitals', {})
                    text.insert(tk.END, f"VITAL SIGNS:\n")
                    if vitals:
                        for vital, value in vitals.items():
                            if value and value != "":
                                unit = ""
                                if vital == "temperature":
                                    unit = "°F"
                                elif vital == "sugar":
                                    unit = "mg/dL"
                                elif vital == "heart_rate":
                                    unit = "bpm"
                                elif vital == "oxygen_level":
                                    unit = "%"
                                text.insert(tk.END, f"  • {vital.replace('_', ' ').title()}: {value} {unit}\n")
                    else:
                        text.insert(tk.END, "  • No vital signs recorded\n")
                    text.insert(tk.END, "\n")
                    
                    # Diagnosis results
                    diagnoses = entry.get('diagnosis', [])
                    text.insert(tk.END, f"DIAGNOSIS RESULTS:\n")
                    if diagnoses:
                        for j, (disease, confidence) in enumerate(diagnoses, 1):
                            text.insert(tk.END, f"  {j}. {disease.replace('_', ' ').title()}\n")
                            text.insert(tk.END, f"     Confidence: {confidence*100:.1f}%\n")
                    else:
                        text.insert(tk.END, "  • No diagnosis available\n")
                    text.insert(tk.END, "\n")
                    
                    # Top diagnosis highlight
                    top_diagnosis = entry.get('top_diagnosis', 'Unknown')
                    text.insert(tk.END, f"PRIMARY DIAGNOSIS: {top_diagnosis.replace('_', ' ').title()}\n")
                    text.insert(tk.END, "\n")
                
            except json.JSONDecodeError:
                text.insert(tk.END, "Error: History file is corrupted or invalid. Please check the file format.")
            except Exception as e:
                text.insert(tk.END, f"Error loading history: {str(e)}")
            
            text.config(state=tk.DISABLED)
        
        # Initial display
        display_history()

    def visualize_feedback(self):
        """Visualize feedback trends"""
        if not feedback:
            messagebox.showinfo("No Data", "No feedback data available for visualization.")
            return
        
        try:
            # Create two plots: overall feedback and detailed trends
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Overall feedback scores
            diseases = list(feedback.keys())
            scores = [sum(entries.values()) for entries in feedback.values()]
            
            ax1.bar(diseases, scores, color='skyblue')
            ax1.set_title("Overall Feedback Scores by Disease")
            ax1.set_xlabel("Disease")
            ax1.set_ylabel("Feedback Score")
            ax1.tick_params(axis='x', rotation=45)
            
            # Detailed trends
            for disease, entries in feedback.items():
                if entries:
                    values = list(entries.values())
                    ax2.plot(range(len(values)), values, marker='o', label=disease.capitalize())
            
            ax2.set_title("Feedback Trends Over Time")
            ax2.set_xlabel("Feedback Instance")
            ax2.set_ylabel("Feedback Score")
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.show()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate visualization: {str(e)}")

    def add_rule(self):
        """Add new diagnosis rule to knowledge base"""
        win = tk.Toplevel(self.root)
        win.title("Add New Diagnosis Rule")
        win.geometry("500x400")
        
        # Main frame
        main_frame = tk.Frame(win, padx=20, pady=20, bg='#1a2a44')
        main_frame.pack(fill="both", expand=True)
        
        tk.Label(main_frame, text="Add New Diagnosis Rule", 
                font=("Segoe UI", 14, "bold"), fg="white", bg='#1a2a44').pack(pady=(0, 20))
        
        # Symptoms section
        tk.Label(main_frame, text="Symptoms (comma-separated):", 
                font=("Segoe UI", 10), fg="white", bg='#1a2a44').pack(anchor="w", pady=(0, 5))
        
        sym_frame = tk.Frame(main_frame, bg='#1a2a44')
        sym_frame.pack(fill="x", pady=(0, 10))
        
        sym_text = scrolledtext.ScrolledText(sym_frame, width=50, height=4, 
                                           font=("Segoe UI", 10), bg='#ecf0f1', fg='black')
        sym_text.pack(fill="x")
        
        tk.Label(main_frame, text="Example: fever, cough, headache", 
                font=("Segoe UI", 8), fg="lightgray", bg='#1a2a44').pack(anchor="w")
        
        # Disease section
        tk.Label(main_frame, text="Disease:", 
                font=("Segoe UI", 10), fg="white", bg='#1a2a44').pack(anchor="w", pady=(10, 5))
        dis_entry = tk.Entry(main_frame, width=50, font=("Segoe UI", 10), bg='#ecf0f1', fg='black')
        dis_entry.pack(fill="x", pady=(0, 5))
        
        # Confidence section
        tk.Label(main_frame, text="Confidence (0.0 - 1.0):", 
                font=("Segoe UI", 10), fg="white", bg='#1a2a44').pack(anchor="w", pady=(10, 5))
        conf_entry = tk.Entry(main_frame, width=50, font=("Segoe UI", 10), bg='#ecf0f1', fg='black')
        conf_entry.pack(fill="x", pady=(0, 5))
        
        tk.Label(main_frame, text="Example: 0.8 (80% confidence)", 
                font=("Segoe UI", 8), fg="lightgray", bg='#1a2a44').pack(anchor="w")
        
        def save_rule():
            try:
                symptoms_text = sym_text.get(1.0, tk.END).strip().lower()
                disease = dis_entry.get().strip().lower()
                confidence_text = conf_entry.get().strip()

                # Validate inputs
                if not symptoms_text:
                    messagebox.showerror("Error", "Please enter at least one symptom.")
                    return
                if not disease:
                    messagebox.showerror("Error", "Please enter a disease name.")
                    return
                if not confidence_text:
                    messagebox.showerror("Error", "Please enter a confidence value.")
                    return

                # Validate confidence
                try:
                    confidence = float(confidence_text)
                    if not (0.0 <= confidence <= 1.0):
                        messagebox.showerror("Error", "Confidence must be between 0.0 and 1.0.")
                        return
                except ValueError:
                    messagebox.showerror("Error", "Invalid confidence value. Please enter a number (e.g., 0.8).")
                    return

                # Parse symptoms
                symptoms = []
                for s in symptoms_text.replace('\n', ',').split(','):
                    s = s.strip()
                    if s:
                        symptom = s.replace(' ', '_')
                        if not symptom:
                            continue
                        symptoms.append(symptom)

                if not symptoms:
                    messagebox.showerror("Error", "No valid symptoms provided.")
                    return

                symptoms = tuple(sorted(set(symptoms)))  # Remove duplicates and sort

                # Check for duplicate rules
                for rule_symptoms, rule_disease, _ in knowledge_base:
                    if (set(symptoms) == set(rule_symptoms) and 
                        disease.lower() == rule_disease.lower()):
                        messagebox.showerror("Error", 
                            f"A rule with symptoms {', '.join(symptoms)} and disease '{disease}' already exists.")
                        return

                # Add new rule
                new_rule = (symptoms, disease, confidence)
                knowledge_base.append(new_rule)
                save_json(knowledge_base, KB_FILE)

                # Update symptom dropdown
                all_kb_symptoms = set()
                for rule in knowledge_base:
                    all_kb_symptoms.update(rule[0])
                all_symptoms_list = sorted([s for s in all_kb_symptoms if not s.startswith("high_")])
                self.suggestion_dropdown['values'] = all_symptoms_list

                messagebox.showinfo("Success", 
                    f"New rule added!\nSymptoms: {', '.join(symptoms)}\nDisease: {disease}\nConfidence: {confidence*100:.1f}%")
                win.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#1a2a44')
        button_frame.pack(fill="x", pady=20)
        
        tk.Button(button_frame, text="Save Rule", command=save_rule, 
                 bg="green", fg="white", font=("Segoe UI", 10, "bold"), 
                 width=15).pack(side="left", padx=(0, 10))
        
        tk.Button(button_frame, text="Cancel", command=win.destroy, 
                 bg="gray", fg="white", font=("Segoe UI", 10), 
                 width=15).pack(side="left")

class LoginApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Medical Diagnosis System - Login")
        self.root.geometry("400x300")
        
        # Load and create a semi-transparent background
        try:
            bg_image = Image.open(BG_IMAGE).convert("RGBA").resize((400, 300))
            overlay = Image.new('RGBA', bg_image.size, (52, 73, 94, 128))  # RGBA: (R, G, B, Alpha), Alpha=128 (50% opacity)
            bg_image = Image.blend(bg_image, overlay, 0.5)  # Blend with 50% overlay
            self.tk_bg = ImageTk.PhotoImage(bg_image)
        except:
            bg_image = Image.new('RGBA', (400, 300), (52, 73, 94, 255))  # Solid dark blue fallback
            self.tk_bg = ImageTk.PhotoImage(bg_image)
        
        self.canvas = tk.Canvas(self.root, width=400, height=300)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(200, 150, image=self.tk_bg)  # Centered image
        
        # Title
        self.canvas.create_text(200, 70, text="AI Medical Diagnosis System", 
                               font=("Helvetica", 14, "bold"), fill="white")
        self.canvas.create_text(200, 90, text="Login / Register", 
                               font=("Helvetica", 12), fill="white")

        # Username
        self.canvas.create_text(150, 120, text="Username:", fill="white", anchor="e")
        self.username_entry = tk.Entry(self.root, width=20, font=("Segoe UI", 10), bg='#ecf0f1', fg='black')
        self.canvas.create_window(200, 120, anchor="w", window=self.username_entry)

        # Password
        self.canvas.create_text(150, 150, text="Password:", fill="white", anchor="e")
        self.password_entry = tk.Entry(self.root, show="*", width=20, font=("Segoe UI", 10), bg='#ecf0f1', fg='black')
        self.canvas.create_window(200, 150, anchor="w", window=self.password_entry)

        # Buttons
        tk.Button(self.root, text="Login", command=self.login, 
                 bg="blue", fg="white", font=("Segoe UI", 10), width=10).place(x=150, y=190)
        tk.Button(self.root, text="Register", command=self.register, 
                 bg="green", fg="white", font=("Segoe UI", 10), width=10).place(x=240, y=190)
        
        # Bind Enter key to login
        self.root.bind('<Return>', lambda event: self.login())
        
        self.root.mainloop()

    def login(self):
        """Handle user login"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password.")
            return
        
        if username in users and verify_password(password, users[username]):
            messagebox.showinfo("Welcome", f"Welcome back, {username}!")
            self.root.destroy()
            root = tk.Tk()
            DiagnosisApp(root, username)
            root.mainloop()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    def register(self):
        """Handle user registration"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password.")
            return
        
        if not USERNAME_RE.fullmatch(username):
            messagebox.showerror(
                "Error",
                "Username must be 3-32 letters, numbers, underscores, or hyphens.",
            )
            return

        if len(password) < 10:
            messagebox.showerror("Error", "Password must be at least 10 characters long.")
            return
        
        if username in users:
            messagebox.showerror("Error", "Username already exists. Please choose a different username.")
            return
        
        users[username] = hash_password(password)
        save_json(users, USERS_FILE)
        messagebox.showinfo("Success", "Registration successful! Please log in with your new account.")

if __name__ == "__main__":
    LoginApp()
