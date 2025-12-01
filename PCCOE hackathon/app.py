import uuid
import sqlite3
import datetime
import json
import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import requests

# --- FLASK APP SETUP ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)

# --- DATABASE CONFIGURATION ---
DB_NAME = 'database.db'

def get_db_connection():
    """Establishes and returns a new SQLite database connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database with expanded tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            age INTEGER,
            gender TEXT,
            weight REAL,
            city TEXT,
            vata_score INTEGER,
            pitta_score INTEGER,
            kapha_score INTEGER,
            prakruti TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Simple migration for 'weight' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN weight REAL")
    except sqlite3.OperationalError:
        pass # Column likely exists

    # History Table (Chat & Disease Logs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            type TEXT, -- 'chat', 'disease_check', 'symptom'
            content TEXT, -- JSON or text
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Diet Plans Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diet_plans (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            plan_json TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

# Initialize DB on startup
with app.app_context():
    init_db()

# --- HELPER FUNCTIONS ---



def calculate_dosha_scores(answers):
    """Calculates Vata, Pitta, Kapha scores (0-100)."""
    scores = {'Vata': 0, 'Pitta': 0, 'Kapha': 0}
    mapping = {'V': 'Vata', 'P': 'Pitta', 'K': 'Kapha'}
    
    for _, val in answers.items():
        if val in mapping:
            scores[mapping[val]] += 1
            
    total = sum(scores.values())
    if total > 0:
        for k in scores:
            scores[k] = round((scores[k] / total) * 100)
            
    return scores

def determine_prakruti(scores):
    """Determines dominant Dosha."""
    sorted_d = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    d1, s1 = sorted_d[0]
    d2, s2 = sorted_d[1]
    
    if s1 - s2 <= 10:
        return f"{d1}-{d2}"
    if s1 - s2 <= 10:
        return f"{d1}-{d2}"
    return d1

@app.before_request
def require_login():
    """Global login check for all routes."""
    # List of endpoints that do not require login
    allowed_routes = ['login', 'signup', 'api_login', 'api_signup', 'static', 'index', 'about', 'contact']
    
    # If the endpoint is not allowed and user is not logged in, redirect to login
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        # Allow static files to be served without login (double check)
        if request.endpoint == 'static':
            return
        return redirect(url_for('login'))

# --- FLASK ROUTES ---

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('dashboard.html', user=user)

@app.route('/questionnaire')
def questionnaire():
    return render_template('questionnaire.html')

@app.route('/result')
def result():
    user = None
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
    return render_template('result.html', user=user)

@app.route('/seasonal')
def seasonal():
    user_dosha = None
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        if user and user['prakruti']:
            user_dosha = user['prakruti']
            
    return render_template('seasonal.html', user_dosha=user_dosha)

@app.route('/diseases')
def diseases():
    return render_template('diseases.html')



@app.route('/history')
def history():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM history WHERE user_id = ? ORDER BY timestamp DESC', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('history.html', logs=logs)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/exercise')
def exercise():
    return render_template('exercise.html')

@app.route('/know-your-dosha')
def know_your_dosha():
    return render_template('know_your_dosha.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- API ENDPOINTS ---

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    try:
        hashed_pw = generate_password_hash(data['password'])
        user_id = str(uuid.uuid4())
        conn = get_db_connection()
        conn.execute('INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)',
                     (user_id, data['name'], data['email'], hashed_pw))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (data['email'],)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], data['password']):
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        return jsonify({"status": "success"})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/submit-quiz', methods=['POST'])
def submit_quiz():
    data = request.get_json()
    answers = data.get('answers', {})
    
    scores = calculate_dosha_scores(answers)
    prakruti = determine_prakruti(scores)
    
    # Only save to DB if user is logged in
    if 'user_id' in session:
        conn = get_db_connection()
        conn.execute('''
            UPDATE users 
            SET age = ?, gender = ?, weight = ?, city = ?, vata_score = ?, pitta_score = ?, kapha_score = ?, prakruti = ?
            WHERE id = ?
        ''', (data.get('age'), data.get('gender'), data.get('weight'), data.get('city'), 
              scores['Vata'], scores['Pitta'], scores['Kapha'], prakruti, session['user_id']))
        conn.commit()
        conn.close()
    
    return jsonify({"status": "success", "prakruti": prakruti, "scores": scores})

from huggingface_hub import InferenceClient

# --- LLM INITIALIZATION ---
# Initialize Hugging Face Inference Client
# Using a reliable model for chat. Qwen2.5-72B-Instruct is a good choice if available, 
# otherwise we can fall back to others.
# We try to get the token from environment or use the one that seemed to be intended.
HF_TOKEN = os.environ.get("HF_TOKEN") or "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" 
# Note: Ideally secrets should be in environment variables. 
# The string above appeared in the original code, assuming it's the intended token.

try:
    client = InferenceClient(api_key=HF_TOKEN)
    print("Hugging Face Inference Client initialized.")
except Exception as e:
    print(f"Error initializing Inference Client: {e}")
    client = None

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    guest_context = data.get('context', {}) # Context from frontend (for guests)
    
    user_id = session.get('user_id')
    user_context = ""

    # 1. Build User Context String
    if user_id:
        # Logged-in user: Fetch from DB
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        
        # Log user message (if logged in)
        conn.execute('INSERT INTO history (id, user_id, type, content) VALUES (?, ?, ?, ?)',
                     (str(uuid.uuid4()), user_id, 'chat_user', message))
        conn.commit()
        conn.close()

        if user:
            prakruti = user['prakruti'] or "Unknown"
            age = user['age'] or "Unknown"
            gender = user['gender'] or "Unknown"
            weight = user['weight'] or "Unknown"
            user_context = f"User Profile: Dosha={prakruti}, Age={age}, Gender={gender}, Weight={weight}kg."
    
    elif guest_context:
        # Guest user: Use context sent from frontend
        prakruti = guest_context.get('prakruti', 'Unknown')
        scores = guest_context.get('scores', {})
        user_context = f"User Profile (Guest): Dosha={prakruti}, Scores={scores}."

    # 2. Generate Response
    bot_reply = "I am having trouble connecting to my brain right now. Please try again later."
    
    if client:
        try:
            # System prompt with Context Injection
            system_content = """
    You are AyurBot, an AI expert in Ayurveda. Your goal is to provide personalized health advice based on Doshas (Vata, Pitta, Kapha).
    
    IMPORTANT FORMATTING RULES:
    1. **ALWAYS use bullet points** for your responses. Do not write long paragraphs.
    2. Break down complex advice into clear, actionable steps.
    3. Use **Bold** for headings and key terms.
    4. When asked for a routine, use a structured list format.
    5. Keep responses concise, easy to read, and to the point.
    6. Do not use Markdown headers (#), use **Bold** text for emphasis instead.
            """
            
            if user_context:
                system_content += f" {user_context} Tailor your advice to this profile."

            # --- CLIMATE CONTEXT INJECTION ---
            try:
                # Quick fetch for context (using default Pune if user city not available in session context yet)
                # In a real app, we'd optimize this to not fetch on every chat message or cache it.
                # For now, we'll assume a default or try to get it if we have user info.
                city_for_chat = "Pune"
                if user_id:
                    # We already fetched user above, let's use that city if available
                    if user and user['city']:
                        city_for_chat = user['city']
                
                lat, lon = get_lat_lon(city_for_chat)
                c_data = get_climate_data(lat, lon)
                
                if c_data and 'current' in c_data:
                    curr = c_data['current']
                    climate_str = f"Current Weather in {city_for_chat}: Temp {curr['temperature_2m']}C, Humidity {curr['relative_humidity_2m']}%, Wind {curr['wind_speed_10m']}km/h."
                    system_content += f"\n\nCONTEXT: {climate_str}\nAnalyze how this weather affects the user's Dosha and provide specific precautions or recommendations if relevant."
            except Exception as e:
                print(f"Chat Climate Context Error: {e}")
            # ---------------------------------

            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": message}
            ]
            
            # Using Qwen/Qwen2.5-72B-Instruct for high quality responses
            response = client.chat_completion(
                messages=messages,
                model="Qwen/Qwen2.5-72B-Instruct", 
                max_tokens=500,
                temperature=0.7,
            )
            
            bot_reply = response.choices[0].message.content
        except Exception as e:
            print(f"Error generating response: {e}")
            bot_reply = "Sorry, I encountered an error processing your request. Please check your internet connection or API token."
            
    # 3. Log Bot Response (only if logged in)
    if user_id:
        conn = get_db_connection()
        conn.execute('INSERT INTO history (id, user_id, type, content) VALUES (?, ?, ?, ?)',
                     (str(uuid.uuid4()), user_id, 'chat_bot', bot_reply))
        conn.commit()
        conn.close()
    
    return jsonify({"response": bot_reply})

@app.route('/api/diseases', methods=['GET'])
@app.route('/api/diseases', methods=['GET'])
def get_diseases():
    dosha = request.args.get('dosha', 'Vata')
    month = request.args.get('month', 'January')
    
    # --- 1. SEASONAL MAPPING ---
    month = month.lower()
    season_dosha = 'Vata' # Default
    
    # Season Logic:
    # Summer (June-Sept): High Pitta
    # Monsoon (June-Sept? - overlapping in user req, assuming late summer/monsoon): High Vata + Kapha
    # Autumn (Oct-Nov): Vata
    # Winter (Dec-Jan): Vata + Kapha
    # Spring (Feb-May): Kapha
    
    # Refined Mapping based on months:
    if month in ['february', 'march', 'april', 'may']:
        season_dosha = 'Kapha'
    elif month in ['june', 'july', 'august', 'september']:
        season_dosha = 'Pitta'
    elif month in ['october', 'november']:
        season_dosha = 'Vata'
    elif month in ['december', 'january']:
        season_dosha = 'Vata-Kapha' # Special case
        
    # --- 2. FULL DISEASE DATASET (30 Diseases) ---
    disease_db = {
        'Vata': [
            {'name': 'Arthritis (Osteoarthritis)', 'desc': 'Degeneration of joints due to Vata dryness.', 'prevention': 'Daily oil massage (Abhyanga) with sesame oil.', 'routine': 'Gentle yoga, warm baths.', 'food': 'Warm, cooked foods, ghee, nuts.'},
            {'name': 'Sciatica', 'desc': 'Nerve pain caused by Vata compression.', 'prevention': 'Avoid cold drafts, keep lower back warm.', 'routine': 'Stretching, rest.', 'food': 'Garlic milk, turmeric.'},
            {'name': 'Insomnia', 'desc': 'Racing mind and inability to sleep.', 'prevention': 'Regular sleep schedule, oil on feet.', 'routine': 'Meditation before bed.', 'food': 'Warm milk with nutmeg.'},
            {'name': 'Anxiety / Panic', 'desc': 'Unstable movement of thoughts.', 'prevention': 'Grounding practices, routine.', 'routine': 'Deep breathing (Pranayama).', 'food': 'Root vegetables, soups.'},
            {'name': 'Chronic Constipation', 'desc': 'Dryness in the colon.', 'prevention': 'Hydration, fiber-rich diet.', 'routine': 'Regular bowel habits.', 'food': 'Triphala, soaked raisins.'},
            {'name': 'Bloating & Gas', 'desc': 'Air accumulation in the gut.', 'prevention': 'Eat slowly, chew well.', 'routine': 'Vajrasana after meals.', 'food': 'Ginger tea, cumin.'},
            {'name': 'Dry Skin Disorders', 'desc': 'Lack of moisture in tissues.', 'prevention': 'Internal and external oleation.', 'routine': 'Avoid hot water showers.', 'food': 'Avocado, oils.'},
            {'name': 'Lower Back Pain', 'desc': 'Vata seat is in the pelvic region.', 'prevention': 'Correct posture, avoid heavy lifting.', 'routine': 'Back strengthening exercises.', 'food': 'Warm soups.'},
            {'name': 'Neuropathic Pain', 'desc': 'Weakness of the nervous system.', 'prevention': 'Stress management.', 'routine': 'Restorative yoga.', 'food': 'Ashwagandha.'},
            {'name': 'Migraine (Vata Type)', 'desc': 'Pulsating pain, sensitivity to sound.', 'prevention': 'Regular meals, avoid triggers.', 'routine': 'Head massage.', 'food': 'Sweet, grounding foods.'}
        ],
        'Pitta': [
            {'name': 'Gastritis / Acid Reflux', 'desc': 'Excess heat in the stomach.', 'prevention': 'Avoid spicy/fried foods.', 'routine': 'Eat on time, don\'t skip meals.', 'food': 'Coconut water, fennel.'},
            {'name': 'Ulcers (Mouth/Gut)', 'desc': 'Inflammation of mucous membranes.', 'prevention': 'Cooling diet, stress reduction.', 'routine': 'Avoid alcohol/smoking.', 'food': 'Aloe vera juice.'},
            {'name': 'Skin Rashes & Hives', 'desc': 'Heat manifesting on the skin.', 'prevention': 'Avoid direct sun.', 'routine': 'Cool water baths.', 'food': 'Coriander water.'},
            {'name': 'Acne (Inflammatory)', 'desc': 'Toxins and heat in blood.', 'prevention': 'Face hygiene, blood purification.', 'routine': 'Neem paste application.', 'food': 'Bitter greens.'},
            {'name': 'Liver Inflammation', 'desc': 'Pitta governs liver function.', 'prevention': 'Avoid alcohol, anger.', 'routine': 'Liver detox.', 'food': 'Turmeric, leafy greens.'},
            {'name': 'Loose Motions', 'desc': 'Fast digestion and heat.', 'prevention': 'Hydration, avoid heat.', 'routine': 'Rest.', 'food': 'Pomegranate, buttermilk.'},
            {'name': 'Hypertension (Pitta)', 'desc': 'High pressure due to heat/stress.', 'prevention': 'Relaxation, cooling breath.', 'routine': 'Moonlight walks.', 'food': 'Cucumber, melon.'},
            {'name': 'Excessive Sweating', 'desc': 'Body trying to release heat.', 'prevention': 'Wear cotton, stay cool.', 'routine': 'Sandalwood paste.', 'food': 'Mint tea.'},
            {'name': 'Inflammatory Headaches', 'desc': 'Burning sensation in head.', 'prevention': 'Wear sunglasses, hat.', 'routine': 'Cold compress.', 'food': 'Sweet fruits.'},
            {'name': 'Irritability / Anger', 'desc': 'Emotional manifestation of Pitta.', 'prevention': 'Meditation, patience.', 'routine': 'Cooling pranayama (Sheetali).', 'food': 'Sweet, cooling foods.'}
        ],
        'Kapha': [
            {'name': 'Obesity / Weight Gain', 'desc': 'Accumulation of heavy elements.', 'prevention': 'Active lifestyle, light diet.', 'routine': 'Vigorous exercise.', 'food': 'Spices, honey, barley.'},
            {'name': 'Hypothyroidism', 'desc': 'Slow metabolism.', 'prevention': 'Stimulating activities.', 'routine': 'Sun salutations.', 'food': 'Seaweed, iodine rich.'},
            {'name': 'Diabetes (Type-2)', 'desc': 'Excess sweetness/heaviness.', 'prevention': 'Sugar control, movement.', 'routine': 'Daily walking.', 'food': 'Bitter gourd, fenugreek.'},
            {'name': 'Sinus Congestion', 'desc': 'Mucus accumulation in head.', 'prevention': 'Keep head warm.', 'routine': 'Neti pot, steam.', 'food': 'Ginger, pepper.'},
            {'name': 'Chronic Cough', 'desc': 'Excess phlegm in lungs.', 'prevention': 'Avoid dairy/cold foods.', 'routine': 'Chest opening yoga.', 'food': 'Tulsi tea.'},
            {'name': 'Asthma (Kapha)', 'desc': 'Obstruction of airways.', 'prevention': 'Avoid damp places.', 'routine': 'Breathing exercises.', 'food': 'Mustard oil massage.'},
            {'name': 'Edema / Retention', 'desc': 'Water accumulation.', 'prevention': 'Reduce salt.', 'routine': 'Leg elevation.', 'food': 'Diuretic herbs (Punarnava).'},
            {'name': 'High Cholesterol', 'desc': 'Clogging of channels.', 'prevention': 'Low fat diet.', 'routine': 'Cardio.', 'food': 'Garlic, guggul.'},
            {'name': 'Lethargy / Fatigue', 'desc': 'Heaviness of mind/body.', 'prevention': 'Early rising.', 'routine': 'New experiences.', 'food': 'Light, spicy foods.'},
            {'name': 'Depression (Kapha)', 'desc': 'Stagnation and attachment.', 'prevention': 'Socializing, activity.', 'routine': 'Volunteer work.', 'food': 'Stimulating spices.'}
        ]
    }
    
    # --- 3. RISK CALCULATION LOGIC ---
    high_risk = []
    medium_risk = []
    low_risk = []
    
    # Helper to calculate risk for a single disease
    def calculate_risk(d_dosha, u_dosha, s_dosha):
        # High Risk: 
        # 1. Disease matches Season (Season aggravates disease)
        # 2. Disease matches User AND Season aggravates User (Double whammy)
        if d_dosha in s_dosha: # Season directly aggravates disease type
            return 'High'
        if d_dosha == u_dosha and u_dosha in s_dosha: # User is vulnerable and season makes it worse
            return 'High'
            
        # Medium Risk:
        # 1. Disease matches User (Constitutional tendency)
        # 2. Disease matches Season (but maybe User balances it?) - covered in High, so here just User match
        if d_dosha == u_dosha:
            return 'Medium'
        
        return 'Low'

    # Iterate through all diseases
    for d_type, diseases in disease_db.items():
        for d in diseases:
            risk = calculate_risk(d_type, dosha, season_dosha)
            
            # Personalization Note
            note = ""
            if risk == 'High':
                note = f"High Risk! {month} is a {season_dosha} season, which aggravates {d_type}. Since you are {dosha}, you are doubly susceptible."
            elif risk == 'Medium':
                note = f"Medium Risk. As a {dosha} type, you are naturally prone to {d['name']}, but the current season ({season_dosha}) is not the primary aggravator."
            else:
                note = f"Low Risk. Currently, environmental factors are not significantly increasing your risk for this."

            d_enriched = d.copy()
            d_enriched['risk_level'] = risk
            d_enriched['dosha_type'] = d_type
            d_enriched['note'] = note
            
            if risk == 'High':
                high_risk.append(d_enriched)
            elif risk == 'Medium':
                medium_risk.append(d_enriched)
            else:
                low_risk.append(d_enriched)
    
    return jsonify({
        "season_dosha": season_dosha,
        "user_dosha": dosha,
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk
    })

# --- CLIMATE INTEGRATION ---

def get_lat_lon(city):
    """Fetches latitude and longitude for a given city using Open-Meteo Geocoding API."""
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        response = requests.get(url).json()
        if 'results' in response:
            return response['results'][0]['latitude'], response['results'][0]['longitude']
    except Exception as e:
        print(f"Error fetching coordinates: {e}")
    return 18.5204, 73.8567 # Default to Pune, India

def get_climate_data(lat, lon):
    """Fetches current weather and forecast from Open-Meteo."""
    try:
        # Fetching Temp, Humidity, Wind Speed, Weather Code (for rain/sun), UV (if available - using shortwave_radiation as proxy or separate API if needed, Open-Meteo has uv_index in hourly)
        # We will use 'current' for real-time and 'daily' for forecast
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,is_day,precipitation,rain,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,uv_index_max,precipitation_sum&timezone=auto&forecast_days=7"
        response = requests.get(url).json()
        return response
    except Exception as e:
        print(f"Error fetching climate data: {e}")
        return None

def calculate_climate_dosha_impact(user_dosha, climate_data):
    """
    Determines how current weather impacts Doshas.
    Returns a dictionary of aggravation factors.
    """
    if not climate_data or 'current' not in climate_data:
        return {'Vata': 0, 'Pitta': 0, 'Kapha': 0}
    
    current = climate_data['current']
    temp = current['temperature_2m']
    humidity = current['relative_humidity_2m']
    wind = current['wind_speed_10m']
    rain = current['rain']
    
    impact = {'Vata': 0, 'Pitta': 0, 'Kapha': 0}
    
    # VATA: Aggravated by Cold, Dry, Wind
    if temp < 20: impact['Vata'] += 2
    if humidity < 40: impact['Vata'] += 2
    if wind > 15: impact['Vata'] += 2
    
    # PITTA: Aggravated by Heat, Sun
    if temp > 30: impact['Pitta'] += 3
    if temp > 35: impact['Pitta'] += 2 # Extra heat
    # (UV index check would go here if available in current, using daily max for now)
    
    # KAPHA: Aggravated by Cold, Damp, Rain
    if temp < 20: impact['Kapha'] += 1
    if humidity > 70: impact['Kapha'] += 2
    if rain > 0: impact['Kapha'] += 3
    
    return impact

def calculate_imbalance_score(user_dosha, seasonal_dosha, climate_impact):
    """
    Calculates overall risk (High/Medium/Low).
    """
    # Base risk from Season
    base_risk = 0
    if user_dosha in seasonal_dosha:
        base_risk += 2 # Season matches User Dosha
        
    # Add Climate Impact for User's Dosha
    # user_dosha can be "Vata", "Pitta", "Kapha" or dual "Vata-Pitta"
    
    climate_risk_points = 0
    for d in ['Vata', 'Pitta', 'Kapha']:
        if d in user_dosha:
            climate_risk_points += climate_impact.get(d, 0)
            
    total_score = base_risk + climate_risk_points
    
    if total_score >= 5:
        return "High"
    elif total_score >= 3:
        return "Medium"
    else:
        return "Low"

@app.route('/climate-impact')
def climate_impact():
    return render_template('climate_impact.html')

@app.route('/api/climate-risk', methods=['GET'])
def get_climate_risk():
    user_id = session.get('user_id')
    city = "Pune" # Default
    user_dosha = "Vata" # Default
    
    if user_id:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        if user:
            city = user['city'] or "Pune"
            user_dosha = user['prakruti'] or "Vata"
            
    # 1. Get Location & Weather
    lat, lon = get_lat_lon(city)
    climate_data = get_climate_data(lat, lon)
    
    # 2. Calculate Impact
    impact = calculate_climate_dosha_impact(user_dosha, climate_data)
    
    # 3. Determine Seasonal Dosha (Reusing logic from diseases API essentially)
    month = datetime.datetime.now().strftime("%B").lower()
    season_dosha = 'Vata'
    if month in ['february', 'march', 'april', 'may']: season_dosha = 'Kapha'
    elif month in ['june', 'july', 'august', 'september']: season_dosha = 'Pitta'
    elif month in ['october', 'november']: season_dosha = 'Vata'
    elif month in ['december', 'january']: season_dosha = 'Vata-Kapha'
    
    # 4. Calculate Final Score
    risk_level = calculate_imbalance_score(user_dosha, season_dosha, impact)
    
    return jsonify({
        "city": city,
        "climate_data": climate_data,
        "user_dosha": user_dosha,
        "season_dosha": season_dosha,
        "impact_factors": impact,
        "risk_level": risk_level
    })



if __name__ == '__main__':
    print("--------------------------------------------------")
    print("  AYURDOSHA PRO+: FLASK SERVER STARTING (SQLite)  ")
    print("--------------------------------------------------")
    app.run(debug=True, host='0.0.0.0', port=5000)
