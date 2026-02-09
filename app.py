# EMPATHY INTERVIEW SIMULATOR - WITH PERSISTENCE
# Students download files at end of interview

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import anthropic
import httpx
import csv
import json
from datetime import datetime
import uuid
import os
from io import StringIO, BytesIO
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

app = Flask(__name__)
CORS(app)

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
http_client = httpx.Client(verify=False)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, http_client=http_client)

VALID_ACCESS_CODES = os.getenv('ACCESS_CODES', 'STUDENT2024,DESIGN2024').split(',')

# Create sessions directory for persistence
SESSIONS_DIR = '/tmp/sessions'
Path(SESSIONS_DIR).mkdir(exist_ok=True)

def save_session(session_id, session_data):
    """Save session to disk"""
    try:
        with open(f'{SESSIONS_DIR}/{session_id}.json', 'w') as f:
            json.dump(session_data, f)
    except Exception as e:
        print(f"Error saving session: {e}")

def load_session(session_id):
    """Load session from disk"""
    try:
        with open(f'{SESSIONS_DIR}/{session_id}.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading session: {e}")
        return None

CHARACTERS = {
    "jamie": {
        "name": "Jamie Rodriguez", "age": 28, "role": "Fitness Instructor",
        "avatar": "💪", "letter": "J", "location": "Brunswick, Melbourne",
        "system_prompt": "You are Jamie, a 28-year-old fitness instructor. Problems: 1) Carrying equipment between 3 gyms on public transport 2) Tracking clients. Keep responses SHORT (1-2 sentences). Only share details when asked."
    },
    "marcus": {
        "name": "Marcus Chen", "age": 45, "role": "Food Truck Owner",
        "avatar": "🍜", "letter": "M", "location": "Footscray, Melbourne",
        "system_prompt": "You are Marcus, food truck owner. Problems: 1) Wasting ingredients - can't predict customers 2) Chaotic payments during rush. Keep responses SHORT (1-2 sentences)."
    },
    "priya": {
        "name": "Priya Sharma", "age": 34, "role": "Kindergarten Teacher",
        "avatar": "👩‍🏫", "letter": "P", "location": "Richmond, Melbourne",
        "system_prompt": "You are Priya, kindergarten teacher. Problems: 1) 22 kids' items get lost/mixed up 2) Documenting activities takes too long. Keep responses SHORT (1-2 sentences)."
    },
    "tom": {
        "name": "Tom Williams", "age": 52, "role": "Handyman",
        "avatar": "🔧", "letter": "T", "location": "Coburg, Melbourne",
        "system_prompt": "You are Tom, handyman. Problems: 1) Forgetting which tools at which property 2) Can't read small text in dim lighting. Keep responses SHORT (1-2 sentences)."
    },
    "sarah": {
        "name": "Sarah Mitchell", "age": 23, "role": "University Student",
        "avatar": "📚", "letter": "S", "location": "Carlton, Melbourne",
        "system_prompt": "You are Sarah, student. Problems: 1) Shared fridge - food gets mixed up 2) Can't focus - phone distracts. Keep responses SHORT (1-2 sentences)."
    }
}

# Same HTML as before - keeping it unchanged for brevity
HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Empathy Interview</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Arial,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}.container{background:white;border-radius:20px;box-shadow:0 20px 40px rgba(0,0,0,0.1);max-width:900px;width:100%;max-height:90vh;overflow:hidden}.screen{display:none;padding:40px}.screen.active{display:block}h1{color:#333;text-align:center;margin-bottom:20px}h2{color:#555;text-align:center;margin-bottom:30px;font-size:1.1em}.input-group{margin-bottom:20px}.input-group label{display:block;margin-bottom:8px;font-weight:600;color:#555}input[type="text"],select{width:100%;padding:12px 16px;border:2px solid #eee;border-radius:8px;font-size:16px}input[type="text"]:focus,select:focus{outline:none;border-color:#667eea}.character-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:15px;margin-bottom:30px}.character-card{border:3px solid #eee;border-radius:12px;padding:15px;text-align:center;cursor:pointer;transition:all 0.3s}.character-card:hover{border-color:#667eea;transform:translateY(-2px)}.character-card.selected{border-color:#667eea;background:#f0f4ff}.character-avatar{font-size:40px;margin-bottom:8px}.character-name{font-weight:600;color:#333;margin-bottom:3px;font-size:14px}.character-role{font-size:12px;color:#666}.btn{background:#667eea;color:white;border:none;padding:14px 30px;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;display:block;margin:20px auto 0}.btn:hover{background:#5a67d8}.btn:disabled{background:#ccc;cursor:not-allowed}.btn-secondary{background:#28a745}.btn-download{background:#6c757d;margin-top:10px}.error-message{background:#f8d7da;color:#721c24;padding:12px;border-radius:8px;margin:10px 0;text-align:center}.header{background:linear-gradient(135deg,#ff6b6b,#ee5a24);color:white;padding:20px;text-align:center}.progress-bar{background:rgba(255,255,255,0.2);height:8px;border-radius:4px;margin-top:15px}.progress-fill{background:#00d2ff;height:100%;transition:width 0.3s}.chat-container{padding:20px;overflow-y:auto;background:#f8f9fa;max-height:400px}.message{margin-bottom:15px;display:flex;gap:10px}.message.user{flex-direction:row-reverse}.message-avatar{width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:bold}.message.user .message-avatar{background:#667eea;color:white}.message.ai .message-avatar{background:#ff6b6b;color:white}.message-content{background:white;padding:12px 16px;border-radius:18px;max-width:70%}.message.user .message-content{background:#667eea;color:white}.input-container{padding:20px;background:white;border-top:1px solid #eee;display:flex;gap:10px}.message-input{flex:1;padding:12px 16px;border:2px solid #eee;border-radius:25px}.send-button{background:#667eea;color:white;border:none;border-radius:50%;width:48px;height:48px;cursor:pointer}.chat-screen{display:none;flex-direction:column;padding:0;height:80vh}.chat-screen.active{display:flex}.score-display{background:linear-gradient(135deg,#28a745,#20c997);color:white;padding:40px;border-radius:15px;margin:20px 0;text-align:center}.score-number{font-size:4em;font-weight:bold}</style></head><body><div class="container"><div id="screen1" class="screen active"><h1>Empathy Interview Simulator</h1><h2>Practice empathy skills through AI roleplay</h2><div class="input-group"><label>Your Name:</label><input type="text" id="studentName" placeholder="Enter your full name"></div><div class="input-group"><label>Class Code:</label><select id="classCode"><option value="">Select your class</option><option value="08DM">08 Design Mechanics</option><option value="07DM">07 Design and Materials</option><option value="WORKSHOP">Workshop Session</option></select></div><div class="input-group"><label>Access Code:</label><input type="text" id="accessCode" placeholder="TEST123"></div><div id="error1" class="error-message" style="display:none;"></div><button class="btn" onclick="goToCharacterSelect()">Continue</button></div><div id="screen2" class="screen"><h1>Choose Your Interview Subject</h1><h2>Select a person to interview</h2><div id="characterGrid" class="character-grid"></div><div id="error2" class="error-message" style="display:none;"></div><button class="btn" onclick="startConversation()">Start Interview</button></div><div id="screen3" class="screen chat-screen"><div class="header"><h1 style="color:white;margin:0;">Empathy Interview</h1><p id="characterInfo" style="margin:10px 0 0;opacity:0.9;"></p><div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div><p id="questionCounter" style="margin:10px 0 0;">Questions remaining: 7</p></div><div class="chat-container" id="chatContainer"></div><div class="input-container"><input type="text" id="messageInput" class="message-input" placeholder="Ask your question..."><button class="send-button" onclick="sendMessage()">➤</button></div></div><div id="screen4" class="screen"><h1>Interview Complete!</h1><div class="score-display"><div class="score-number" id="finalScore">--</div><p style="font-size:1.2em;margin-top:10px;">Empathy Score</p></div><p style="text-align:center;color:#666;margin:20px 0;">Download your files below:</p><button class="btn btn-secondary" onclick="downloadCertificate()">📜 Download Certificate</button><button class="btn btn-download" onclick="downloadTranscript()">📄 Download Transcript (CSV)</button><button class="btn" onclick="location.reload()" style="margin-top:30px;">Start New Interview</button></div></div><script>let studentName='',classCode='',accessCode='',selectedCharacter=null,sessionId=null,questionCount=0;const MAX_QUESTIONS=7;async function goToCharacterSelect(){studentName=document.getElementById('studentName').value.trim();classCode=document.getElementById('classCode').value;accessCode=document.getElementById('accessCode').value.trim();if(!studentName)return showError('error1','Please enter your name');if(!classCode)return showError('error1','Please select your class');if(!accessCode)return showError('error1','Please enter access code');try{const response=await fetch('/api/characters');const characters=await response.json();const grid=document.getElementById('characterGrid');grid.innerHTML='';for(const[id,char]of Object.entries(characters)){const card=document.createElement('div');card.className='character-card';card.onclick=()=>selectCharacter(id,card);card.innerHTML=`<div class="character-avatar">${char.avatar}</div><div class="character-name">${char.name}</div><div class="character-role">${char.role}</div><div class="character-role" style="font-size:11px;margin-top:5px;">${char.location}</div>`;grid.appendChild(card)}switchScreen('screen1','screen2')}catch(error){showError('error1','Failed to load characters')}}function selectCharacter(charId,card){document.querySelectorAll('.character-card').forEach(c=>c.classList.remove('selected'));card.classList.add('selected');selectedCharacter=charId}async function startConversation(){if(!selectedCharacter)return showError('error2','Please select a character');try{const response=await fetch('/api/start-conversation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({character:selectedCharacter,access_code:accessCode,student_name:studentName,class_code:classCode})});if(!response.ok)throw new Error((await response.json()).error);const data=await response.json();sessionId=data.session_id;document.getElementById('characterInfo').textContent=`${data.character.name} - ${data.character.role}`;document.getElementById('chatContainer').innerHTML='';addMessage(data.initial_message,'ai',data.character.letter);switchScreen('screen2','screen3');document.getElementById('messageInput').focus()}catch(error){showError('error2',error.message)}}async function sendMessage(){const input=document.getElementById('messageInput');const message=input.value.trim();if(!message||questionCount>=MAX_QUESTIONS)return;addMessage(message,'user','Y');input.value='';questionCount++;updateProgress();input.disabled=true;try{const response=await fetch('/api/send-message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId,message})});const data=await response.json();addMessage(data.response,'ai',selectedCharacter.charAt(0).toUpperCase());if(questionCount>=MAX_QUESTIONS){setTimeout(completeInterview,1000)}else{input.disabled=false;input.focus()}}catch(error){addMessage("Sorry, error occurred.",'ai','X');input.disabled=false}}function addMessage(content,sender,avatar){const chat=document.getElementById('chatContainer');const div=document.createElement('div');div.className=`message ${sender}`;div.innerHTML=`<div class="message-avatar">${avatar}</div><div class="message-content">${content}</div>`;chat.appendChild(div);chat.scrollTop=chat.scrollHeight}function updateProgress(){document.getElementById('progressFill').style.width=(questionCount/MAX_QUESTIONS*100)+'%';document.getElementById('questionCounter').textContent=`Questions remaining: ${MAX_QUESTIONS-questionCount}`}async function completeInterview(){try{const response=await fetch('/api/complete-session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId})});const data=await response.json();document.getElementById('finalScore').textContent=data.empathy_score;switchScreen('screen3','screen4')}catch(error){alert('Error completing session')}}async function downloadCertificate(){try{const response=await fetch('/api/generate-certificate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId})});const blob=await response.blob();const url=window.URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`${classCode}_${studentName.replace(/ /g,'_')}_certificate.png`;a.click()}catch(error){alert('Error downloading certificate')}}async function downloadTranscript(){try{const response=await fetch('/api/export-conversation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId})});const data=await response.json();const blob=new Blob([data.csv_data],{type:'text/csv'});const url=window.URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`${classCode}_${studentName.replace(/ /g,'_')}_transcript.csv`;a.click()}catch(error){alert('Error downloading transcript')}}function switchScreen(from,to){document.getElementById(from).classList.remove('active');document.getElementById(to).classList.add('active')}function showError(id,msg){const el=document.getElementById(id);el.textContent=msg;el.style.display='block';setTimeout(()=>el.style.display='none',5000)}</script></body></html>'''

@app.route('/')
def index():
    return HTML

@app.route('/api/characters')
def get_characters():
    return jsonify({k: {key: v[key] for key in ['name', 'age', 'role', 'avatar', 'location']} for k, v in CHARACTERS.items()})

@app.route('/api/start-conversation', methods=['POST'])
def start_conversation():
    try:
        data = request.json
        if data.get('access_code') not in VALID_ACCESS_CODES:
            return jsonify({"error": "Invalid access code"}), 403
        
        session_id = str(uuid.uuid4())
        char_id = data['character']
        session_data = {
            "character": char_id,
            "student_name": data['student_name'],
            "class_code": data.get('class_code', 'GENERAL'),
            "messages": [],
            "started_at": datetime.now().isoformat()
        }
        
        msg = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=150,
            system=CHARACTERS[char_id]["system_prompt"],
            messages=[{"role": "user", "content": "Introduce yourself briefly in 1-2 sentences."}]
        ).content[0].text
        
        session_data["messages"].append({"role": "assistant", "content": msg, "timestamp": datetime.now().isoformat()})
        save_session(session_id, session_data)
        
        return jsonify({"session_id": session_id, "character": CHARACTERS[char_id], "initial_message": msg})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/send-message', methods=['POST'])
def send_message():
    try:
        data = request.json
        session_id = data.get('session_id')
        
        session = load_session(session_id)
        if not session:
            return jsonify({"error": "Session expired or not found"}), 404
        
        session["messages"].append({"role": "user", "content": data['message'], "timestamp": datetime.now().isoformat()})
        
        msgs = [{"role": m["role"], "content": m["content"]} for m in session["messages"][-10:]]
        
        api_response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=150,
            temperature=0.7,
            system=CHARACTERS[session["character"]]["system_prompt"],
            messages=msgs
        )
        
        response_text = api_response.content[0].text if api_response.content else "Could you rephrase that?"
        
        session["messages"].append({"role": "assistant", "content": response_text, "timestamp": datetime.now().isoformat()})
        save_session(session_id, session)
        
        return jsonify({"response": response_text})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/complete-session', methods=['POST'])
def complete_session():
    try:
        session_id = request.json['session_id']
        session = load_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
            
        user_msgs = [m["content"] for m in session["messages"] if m["role"] == "user"]
        
        score = 40
        for msg in user_msgs:
            ml = msg.lower()
            if '?' in msg: score += 4
            if any(w in ml for w in ['how', 'what', 'why', 'tell me']): score += 3
            if len(msg) > 40: score += 2
            if any(w in ml for w in ['feel', 'challenge', 'struggle']): score += 3
            if any(p in ml for p in ['tell me more', 'what else']): score += 4
        
        score = max(20, min(100, score))
        session["empathy_score"] = score
        session["completed_at"] = datetime.now().isoformat()
        save_session(session_id, session)
        
        return jsonify({"empathy_score": score, "student_name": session["student_name"]})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/export-conversation', methods=['POST'])
def export_conversation():
    try:
        session_id = request.json['session_id']
        session = load_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
            
        char = CHARACTERS[session["character"]]
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Student', 'Class', 'Character', 'Timestamp', 'Speaker', 'Message', 'Score'])
        
        for m in session["messages"]:
            writer.writerow([
                session["student_name"], session.get("class_code", ""), char["name"], m["timestamp"],
                "Student" if m["role"] == "user" else char["name"],
                m["content"], session.get("empathy_score", "")
            ])
        
        return jsonify({"csv_data": output.getvalue()})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-certificate', methods=['POST'])
def generate_certificate():
    try:
        session_id = request.json['session_id']
        session = load_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
            
        name = session["student_name"]
        score = session.get("empathy_score", 0)
        char = CHARACTERS[session["character"]]
        class_code = session.get("class_code", "")
        
        img = Image.new('RGB', (800, 600), 'white')
        draw = ImageDraw.Draw(img)
        
        try:
            f1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            f3 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        except:
            f1 = f2 = f3 = ImageFont.load_default()
        
        draw.rectangle([(20, 20), (780, 580)], outline='#667eea', width=5)
        draw.text((400, 80), "CERTIFICATE OF COMPLETION", font=f1, fill='#333', anchor='mm')
        draw.text((400, 140), "Empathy Interview Training", font=f3, fill='#666', anchor='mm')
        if class_code:
            draw.text((400, 200), f"Class: {class_code}", font=f3, fill='#666', anchor='mm')
        draw.text((400, 260), name, font=f2, fill='#667eea', anchor='mm')
        draw.text((400, 340), "Successfully completed empathy interview", font=f3, fill='#333', anchor='mm')
        draw.text((400, 380), f"with {char['name']}", font=f3, fill='#333', anchor='mm')
        draw.text((400, 460), f"Empathy Score: {score}/100", font=f2, fill='#28a745', anchor='mm')
        draw.text((400, 540), datetime.now().strftime("%B %d, %Y"), font=f3, fill='#666', anchor='mm')
        
        buf = BytesIO()
        img.save(buf, 'PNG')
        buf.seek(0)
        
        return send_file(buf, mimetype='image/png', as_attachment=True, 
                        download_name=f'{class_code}_{name.replace(" ", "_")}_certificate.png')
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
