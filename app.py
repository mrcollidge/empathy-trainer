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
    try:
        with open(f'{SESSIONS_DIR}/{session_id}.json', 'w') as f:
            json.dump(session_data, f)
    except Exception as e:
        print(f"Error saving session: {e}")

def load_session(session_id):
    try:
        with open(f'{SESSIONS_DIR}/{session_id}.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading session: {e}")
        return None

CHARACTERS = {
    "ayaan": {
        "name": "Ayaan Malik", "age": 17, "role": "Year 11 Student",
        "avatar": "", "letter": "A", "location": "Melbourne",
        "system_prompt": """You are Ayaan Malik, a 17-year-old Year 11 student in Melbourne. A design student is interviewing you to understand your needs and daily challenges — they will later design a solution to help you.

WHO YOU ARE:
- You are intelligent and highly motivated — your goal is to do really well at school and get into Monash University to study medicine
- You genuinely love learning but you battle two big problems: getting distracted in class and procrastinating at home
- You have a supportive family but they put a lot of pressure on you to succeed, which stresses you out
- You have a good group of friends and play soccer, which you love — it's one of your main outlets
- You are a real person with a real inner life — you feel the weight of your family's expectations, you feel guilty when you waste time, you feel proud when you do well

YOUR PROBLEMS (share them naturally as they become relevant — don't list them all at once):
- In class you often drift off, especially in subjects you find less interesting — your mind wanders and you miss things the teacher has said
- You find yourself on your phone during lessons even when you're trying not to be — you just reach for it without thinking
- When you sit down to study at home, you start tasks but then switch to YouTube, social media, or messaging friends
- You often study late at night because you've wasted the afternoon, which means you're tired the next day
- The pressure from your parents to get high ATAR scores makes you anxious, and sometimes that anxiety actually makes it harder to focus
- You sometimes feel like you're falling behind even when you're working hard, which is discouraging
- Soccer training takes up two evenings a week plus weekend games — you love it but it cuts into study time and you feel torn
- You don't have a great system for keeping on top of all your assignments and due dates — you sometimes forget things or leave them too late

HOW TO RESPOND:
- Keep answers to 1-3 sentences. Sound like a real Year 11 student — casual, honest, occasionally self-deprecating.
- Share problems naturally in response to what's asked. Don't dump everything at once.
- If asked something vague like "how's school going?", give a brief honest answer — mention one thing.
- Be concrete — mention specific subjects, specific situations, real feelings.
- Never suggest solutions to your own problems.
- If they ask a yes/no question, give a short answer and only expand if they follow up."""
    },
    "lachlan": {
        "name": "Lachlan Matthews", "age": 16, "role": "Year 10 Student & AFL Player",
        "avatar": "", "letter": "L", "location": "Melbourne",
        "system_prompt": """You are Lachlan Matthews, a 16-year-old Year 10 student in Melbourne. You want to become a professional AFL player. A design student is interviewing you to understand your needs and daily challenges — they will later design a solution to help you.

WHO YOU ARE:
- You are a genuinely gifted athlete — coaches have told you your ball skills, read of the game, and mental toughness are exceptional
- Your dream is to be drafted and play professional AFL — you think about it constantly
- You've just been selected to play in your club's senior team, which is a massive achievement — but it's also really hard
- You have a supportive family and a great mentor at your footy club who looks out for you
- You're decent at school but it's not your priority — footy is everything to you right now

YOUR PROBLEMS (share them naturally as they become relevant — don't list them all at once):
- Your fitness is your biggest weakness — you run out of steam in the second half of games and your performance drops noticeably
- Playing with the senior men is a big physical step up — they're stronger, heavier, and faster, and you're getting beaten in contests you'd win at your age group
- Your aerobic base isn't where it needs to be — you get winded and your decision-making gets worse late in games when you're tired
- You feel embarrassed when you make mistakes against the older players — you worry they don't take you seriously
- You're not sure how to improve your fitness on top of training — you don't want to overtrain and get injured
- Balancing school and footy training is hard — by the time you get home from training you're exhausted and have no energy for homework
- You sometimes get frustrated watching yourself on video because you can see exactly when you fade in games
- You're not eating as well as you probably should — it's hard to know what to eat and when around training and games

HOW TO RESPOND:
- Keep answers to 1-3 sentences. Sound like a real 16-year-old footy-obsessed kid — genuine, keen, sometimes a bit blunt.
- Share problems naturally in response to what's asked. Don't list everything at once.
- Be concrete — mention specific moments from games, specific feelings, real situations.
- Never suggest solutions to your own problems.
- If they ask a yes/no question, give a short answer and only expand if they follow up."""
    },
    "hinata": {
        "name": "Hinata Takahashi", "age": 16, "role": "Year 10 Student (EAL)",
        "avatar": "", "letter": "H", "location": "Melbourne (from Japan)",
        "system_prompt": """You are Hinata Takahashi, a 16-year-old student who recently moved to Melbourne from Japan. A design student is interviewing you to understand your needs and daily challenges — they will later design a solution to help you.

WHO YOU ARE:
- You have been learning English for 4 years in Japan and can generally follow conversations — but Australian accents and fast speech are genuinely hard for you
- You are highly academic and motivated — your goal is to finish high school in Melbourne and get into the University of Melbourne
- You are polite, thoughtful, and work extremely hard
- You have made some good friends at school — but they are all Japanese students, and at lunchtime you all speak Japanese together
- At home you speak Japanese with your parents, so English is only really happening at school
- By the end of each school day you are mentally exhausted in a way that's hard to describe

YOUR PROBLEMS (share them naturally as they become relevant — don't list them all at once):
- Some teachers speak too quickly and you lose track of what they're saying, especially when they don't write things on the board
- The Australian accent is different from what you studied in Japan — some words and expressions you simply don't recognise
- Keeping up with class discussions is hard because by the time you've processed what someone said and thought of something to add, the conversation has moved on
- Following along all day in a second language takes enormous energy — it's like always having to think twice about everything
- By the afternoon you find it hard to concentrate because you're so fatigued — you sometimes zone out in your last couple of classes
- You feel embarrassed to ask teachers to repeat things because you don't want to seem slow or like a burden
- Because you only speak Japanese at lunch and at home, you don't get much practice outside of class time
- Academic vocabulary — words used in science, humanities, and maths — is different from everyday English and you still find a lot of it unfamiliar
- You sometimes miss important instructions or assessment details because you misheard or misunderstood something

HOW TO RESPOND:
- Keep answers to 1-3 sentences. Your English is good but careful — you sometimes pause to find the right word.
- Sound genuine — you are hardworking and earnest, not timid.
- Share problems naturally in response to what's asked. Don't list everything at once.
- Be concrete — mention specific classes, specific moments, real feelings.
- Never suggest solutions to your own problems.
- If they ask a yes/no question, give a short answer and only expand if they follow up."""
    },
    "jamie": {
        "name": "Jamie Nguyen", "age": 15, "role": "Year 9 Student",
        "avatar": "", "letter": "J", "location": "Melbourne",
        "system_prompt": """You are Jamie Nguyen, a 15-year-old Year 9 student in Melbourne. You have cerebral palsy and use a wheelchair to get around. A design student is interviewing you to understand your needs and daily challenges — they will later design a solution to help you.

WHO YOU ARE:
- You have cerebral palsy that affects your mobility, but through years of physical therapy, medication, and assistive devices you lead a pretty normal teenage life — you are social, funny, and have a great group of friends
- Your favourite subject is Science and you want to become a scientist when you leave school
- You are independent and determined — you don't want people to make a big deal of your wheelchair
- You have a great group of friends and several teachers who are really supportive
- You're a pretty positive person but there's one thing at school that genuinely stresses you out: the elevator

YOUR PROBLEMS (share them naturally as they become relevant — don't list them all at once):
- Your school has two floors — ground floor and first floor — connected by an elevator
- The elevator works, but it is horrible to use: the lights flicker, it shudders when it moves, and the doors sometimes don't open immediately when you arrive at a floor
- All of this has made you moderately claustrophobic — you feel trapped and panicky inside it, even though you know it's probably fine
- Sometimes you avoid going to class rather than taking the elevator — especially if you're already feeling anxious that day
- The Science labs are on the first floor, and Science is your favourite subject — so avoiding the elevator means missing the class you love most
- You feel frustrated and embarrassed that something so small has this effect on you — your friends don't really understand
- You've tried to explain to teachers why you're sometimes late or absent, but it's hard to talk about without feeling like you're complaining
- On bad days you'll take a longer route around the building just to delay having to face the elevator
- You worry that missing Science labs is going to affect your marks and your future plans

HOW TO RESPOND:
- Keep answers to 1-3 sentences. Sound like a normal, relaxed 15-year-old — you don't lead with your disability, it's just part of your life.
- Share problems naturally in response to what's asked. Don't list everything at once.
- Be concrete — mention specific feelings, specific moments, real situations from school.
- Never suggest solutions to your own problems.
- If they ask a yes/no question, give a short answer and only expand if they follow up.
- You are matter-of-fact about your wheelchair but the elevator issue genuinely bothers you — let that come through if they ask about it."""
    }
}

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Empathy Interview</title>
<link href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}

body{
    font-family:'Libre Franklin',sans-serif;
    background:#F5F0EB;
    color:#1a1a1a;
    min-height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    padding:20px;
}

.container{
    background:#fff;
    border:1px solid #d4cfc9;
    max-width:720px;
    width:100%;
    max-height:92vh;
    overflow:hidden;
}

/* --- SCREENS --- */
.screen{display:none;padding:48px 40px}
.screen.active{display:block}

h1{
    font-size:1.5em;
    font-weight:700;
    letter-spacing:-0.02em;
    margin-bottom:6px;
}
h2{
    font-size:0.9em;
    font-weight:400;
    color:#6b6560;
    margin-bottom:32px;
}

/* --- FORMS --- */
.input-group{margin-bottom:20px}
.input-group label{
    display:block;
    margin-bottom:6px;
    font-size:0.8em;
    font-weight:600;
    text-transform:uppercase;
    letter-spacing:0.05em;
    color:#6b6560;
}
input[type="text"],select{
    width:100%;
    padding:10px 12px;
    border:1px solid #d4cfc9;
    background:#fff;
    font-family:inherit;
    font-size:15px;
    color:#1a1a1a;
}
input[type="text"]:focus,select:focus{
    outline:none;
    border-color:#1a1a1a;
}

.btn{
    background:#1a1a1a;
    color:#fff;
    border:none;
    padding:12px 28px;
    font-family:inherit;
    font-size:14px;
    font-weight:600;
    letter-spacing:0.02em;
    cursor:pointer;
    display:block;
    margin:28px auto 0;
    transition:background 0.15s;
}
.btn:hover{background:#333}
.btn:disabled{background:#bbb;cursor:not-allowed}
.btn-secondary{background:#2a6e3f}
.btn-secondary:hover{background:#35884e}
.btn-download{background:#555;margin-top:12px}
.btn-download:hover{background:#666}

.error-message{
    background:#fce8e8;
    color:#8c2020;
    padding:10px 14px;
    font-size:0.85em;
    margin:12px 0;
    text-align:center;
}

/* --- CHARACTER GRID --- */
.character-grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
    gap:12px;
    margin-bottom:24px;
}
.character-card{
    border:1px solid #d4cfc9;
    padding:20px 16px;
    text-align:center;
    cursor:pointer;
    transition:all 0.15s;
}
.character-card:hover{
    border-color:#1a1a1a;
}
.character-card.selected{
    border-color:#1a1a1a;
    background:#F5F0EB;
}
.character-initial{
    width:48px;height:48px;
    border-radius:50%;
    background:#1a1a1a;
    color:#fff;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    font-size:18px;
    font-weight:700;
    margin-bottom:10px;
}
.character-name{
    font-weight:600;
    font-size:0.95em;
    margin-bottom:2px;
}
.character-role{
    font-size:0.78em;
    color:#6b6560;
}
.character-location{
    font-size:0.72em;
    color:#9a9590;
    margin-top:3px;
}

/* --- CHAT HEADER --- */
.header{
    background:#1a1a1a;
    color:#fff;
    padding:20px 24px;
}
.header h1{
    font-size:1em;
    font-weight:600;
    color:#fff;
    margin:0;
    letter-spacing:0;
}
.header-sub{
    font-size:0.82em;
    color:#aaa;
    margin-top:4px;
}
.progress-bar{
    background:#333;
    height:3px;
    margin-top:14px;
}
.progress-fill{
    background:#F5F0EB;
    height:100%;
    transition:width 0.3s;
}
.msg-counter{
    font-size:0.75em;
    color:#888;
    margin-top:8px;
    font-variant-numeric:tabular-nums;
}

/* --- CHAT --- */
.chat-container{
    padding:20px 24px;
    overflow-y:auto;
    background:#F5F0EB;
    max-height:400px;
}
.message{
    margin-bottom:14px;
    display:flex;
    gap:10px;
}
.message.user{flex-direction:row-reverse}

.message-avatar{
    width:32px;height:32px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:13px;
    font-weight:700;
    flex-shrink:0;
}
.message.user .message-avatar{
    background:#1a1a1a;
    color:#fff;
}
.message.ai .message-avatar{
    background:#d4cfc9;
    color:#1a1a1a;
}

.message-content{
    padding:10px 14px;
    max-width:72%;
    font-size:0.9em;
    line-height:1.55;
}
.message.user .message-content{
    background:#1a1a1a;
    color:#fff;
}
.message.ai .message-content{
    background:#fff;
    color:#1a1a1a;
    border:1px solid #d4cfc9;
}

/* --- INPUT --- */
.input-container{
    padding:16px 24px;
    background:#fff;
    border-top:1px solid #d4cfc9;
    display:flex;
    gap:10px;
}
.message-input{
    flex:1;
    padding:10px 14px;
    border:1px solid #d4cfc9;
    font-family:inherit;
    font-size:14px;
    color:#1a1a1a;
    background:#fff;
}
.message-input:focus{outline:none;border-color:#1a1a1a}
.send-button{
    background:#1a1a1a;
    color:#fff;
    border:none;
    width:42px;height:42px;
    cursor:pointer;
    font-size:16px;
    display:flex;align-items:center;justify-content:center;
    transition:background 0.15s;
}
.send-button:hover{background:#333}

/* --- CHAT SCREEN LAYOUT --- */
.chat-screen{display:none;flex-direction:column;padding:0;height:82vh}
.chat-screen.active{display:flex}

/* --- RESULTS --- */
.score-display{
    background:#1a1a1a;
    color:#fff;
    padding:36px;
    text-align:center;
    margin:20px 0;
}
.score-number{
    font-size:3.5em;
    font-weight:700;
    letter-spacing:-0.03em;
    font-variant-numeric:tabular-nums;
}
.score-label{
    font-size:0.85em;
    color:#aaa;
    margin-top:6px;
}
</style>
</head>
<body>
<div class="container">

<!-- SCREEN 1: LOGIN -->
<div id="screen1" class="screen active">
    <h1>Empathy Interview</h1>
    <h2>Practice empathy skills through conversation</h2>
    <div class="input-group">
        <label>Your Name</label>
        <input type="text" id="studentName" placeholder="Full name">
    </div>
    <div class="input-group">
        <label>Class</label>
        <select id="classCode">
            <option value="">Select your class</option>
            <option value="08DM">08 Design Mechanics</option>
            <option value="07DM">07 Design and Materials</option>
            <option value="WORKSHOP">Workshop Session</option>
        </select>
    </div>
    <div class="input-group">
        <label>Access Code</label>
        <input type="text" id="accessCode" placeholder="Enter code">
    </div>
    <div id="error1" class="error-message" style="display:none;"></div>
    <button class="btn" onclick="goToCharacterSelect()">Continue</button>
</div>

<!-- SCREEN 2: CHARACTER SELECT -->
<div id="screen2" class="screen">
    <h1>Who will you interview?</h1>
    <h2>Each person has real problems in their daily life. Your job is to uncover them.</h2>
    <div id="characterGrid" class="character-grid"></div>
    <div id="error2" class="error-message" style="display:none;"></div>
    <button class="btn" onclick="startConversation()">Start Interview</button>
</div>

<!-- SCREEN 3: CHAT -->
<div id="screen3" class="screen chat-screen">
    <div class="header">
        <h1 id="characterInfo">Interview</h1>
        <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
        <div class="msg-counter" id="questionCounter">7 questions remaining</div>
    </div>
    <div class="chat-container" id="chatContainer"></div>
    <div class="input-container">
        <input type="text" id="messageInput" class="message-input" placeholder="Ask a question...">
        <button class="send-button" onclick="sendMessage()">&rarr;</button>
    </div>
</div>

<!-- SCREEN 4: RESULTS -->
<div id="screen4" class="screen">
    <h1>Interview Complete</h1>
    <div class="score-display">
        <div class="score-number" id="finalScore">&mdash;</div>
        <div class="score-label">Empathy Score</div>
    </div>
    <p style="text-align:center;color:#6b6560;font-size:0.9em;margin:20px 0;">Download your files below.</p>
    <button class="btn btn-secondary" onclick="downloadCertificate()">Download Certificate</button>
    <button class="btn btn-download" onclick="downloadTranscript()">Download Transcript (CSV)</button>
    <button class="btn" onclick="location.reload()" style="margin-top:28px;">New Interview</button>
</div>

</div>

<script>
let studentName='',classCode='',accessCode='',selectedCharacter=null,sessionId=null,questionCount=0;
const MAX_QUESTIONS=7;

async function goToCharacterSelect(){
    studentName=document.getElementById('studentName').value.trim();
    classCode=document.getElementById('classCode').value;
    accessCode=document.getElementById('accessCode').value.trim();
    if(!studentName)return showError('error1','Please enter your name');
    if(!classCode)return showError('error1','Please select your class');
    if(!accessCode)return showError('error1','Please enter access code');
    try{
        const response=await fetch('/api/characters');
        const characters=await response.json();
        const grid=document.getElementById('characterGrid');
        grid.innerHTML='';
        for(const[id,char]of Object.entries(characters)){
            const card=document.createElement('div');
            card.className='character-card';
            card.onclick=()=>selectCharacter(id,card);
            card.innerHTML=
                '<div class="character-initial">'+char.name.charAt(0)+'</div>'+
                '<div class="character-name">'+char.name+'</div>'+
                '<div class="character-role">'+char.role+', '+char.age+'</div>'+
                '<div class="character-location">'+char.location+'</div>';
            grid.appendChild(card);
        }
        switchScreen('screen1','screen2');
    }catch(error){showError('error1','Failed to load characters')}
}

function selectCharacter(charId,card){
    document.querySelectorAll('.character-card').forEach(c=>c.classList.remove('selected'));
    card.classList.add('selected');
    selectedCharacter=charId;
}

async function startConversation(){
    if(!selectedCharacter)return showError('error2','Please select a character');
    try{
        const response=await fetch('/api/start-conversation',{
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({character:selectedCharacter,access_code:accessCode,student_name:studentName,class_code:classCode})
        });
        if(!response.ok)throw new Error((await response.json()).error);
        const data=await response.json();
        sessionId=data.session_id;
        document.getElementById('characterInfo').textContent=data.character.name+' \u2014 '+data.character.role;
        document.getElementById('chatContainer').innerHTML='';
        addMessage(data.initial_message,'ai',data.character.letter);
        switchScreen('screen2','screen3');
        document.getElementById('messageInput').focus();
    }catch(error){showError('error2',error.message)}
}

async function sendMessage(){
    const input=document.getElementById('messageInput');
    const message=input.value.trim();
    if(!message||questionCount>=MAX_QUESTIONS)return;
    addMessage(message,'user','Y');
    input.value='';
    questionCount++;
    updateProgress();
    input.disabled=true;
    try{
        const response=await fetch('/api/send-message',{
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({session_id:sessionId,message})
        });
        const data=await response.json();
        addMessage(data.response,'ai',selectedCharacter.charAt(0).toUpperCase());
        if(questionCount>=MAX_QUESTIONS){setTimeout(completeInterview,1000)}
        else{input.disabled=false;input.focus()}
    }catch(error){
        addMessage("Sorry, an error occurred.",'ai','!');
        input.disabled=false;
    }
}

function addMessage(content,sender,avatar){
    const chat=document.getElementById('chatContainer');
    const div=document.createElement('div');
    div.className='message '+sender;
    div.innerHTML='<div class="message-avatar">'+avatar+'</div><div class="message-content">'+content+'</div>';
    chat.appendChild(div);
    chat.scrollTop=chat.scrollHeight;
}

function updateProgress(){
    document.getElementById('progressFill').style.width=(questionCount/MAX_QUESTIONS*100)+'%';
    document.getElementById('questionCounter').textContent=(MAX_QUESTIONS-questionCount)+' question'+(MAX_QUESTIONS-questionCount!==1?'s':'')+' remaining';
}

async function completeInterview(){
    try{
        const response=await fetch('/api/complete-session',{
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({session_id:sessionId})
        });
        const data=await response.json();
        document.getElementById('finalScore').textContent=data.empathy_score;
        switchScreen('screen3','screen4');
    }catch(error){alert('Error completing session')}
}

async function downloadCertificate(){
    try{
        const response=await fetch('/api/generate-certificate',{
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({session_id:sessionId})
        });
        const blob=await response.blob();
        const url=window.URL.createObjectURL(blob);
        const a=document.createElement('a');
        a.href=url;a.download=classCode+'_'+studentName.replace(/ /g,'_')+'_certificate.png';a.click();
    }catch(error){alert('Error downloading certificate')}
}

async function downloadTranscript(){
    try{
        const response=await fetch('/api/export-conversation',{
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({session_id:sessionId})
        });
        const data=await response.json();
        const blob=new Blob([data.csv_data],{type:'text/csv'});
        const url=window.URL.createObjectURL(blob);
        const a=document.createElement('a');
        a.href=url;a.download=classCode+'_'+studentName.replace(/ /g,'_')+'_transcript.csv';a.click();
    }catch(error){alert('Error downloading transcript')}
}

function switchScreen(from,to){
    document.getElementById(from).classList.remove('active');
    document.getElementById(to).classList.add('active');
}

function showError(id,msg){
    const el=document.getElementById(id);
    el.textContent=msg;el.style.display='block';
    setTimeout(()=>el.style.display='none',5000);
}
</script>
</body>
</html>'''

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
        assistant_msgs = [m["content"] for m in session["messages"] if m["role"] == "assistant"]
        
        # Build conversation transcript for Claude to evaluate
        char = CHARACTERS[session["character"]]
        transcript = ""
        msg_list = session["messages"]
        for m in msg_list:
            speaker = "Student" if m["role"] == "user" else char["name"]
            transcript += f"{speaker}: {m['content']}\n"
        
        try:
            eval_prompt = f"""You are assessing a design student's empathy interview skills. They interviewed {char['name']}, a {char['role']} from {char['location']}, to understand their daily problems — with the goal of eventually designing a physical product to help them.

Here is the full conversation transcript:
{transcript}

Score the student out of 100 based on these design thinking empathy criteria:

1. OPEN-ENDED QUESTIONS (0-20): Did they ask how/what/why questions that let the person talk freely? Or did they ask closed yes/no questions?

2. FOLLOW-UP & DEPTH (0-25): Did they dig deeper into answers? Did they ask "why" behind the first answer? Did they follow threads rather than jumping between unrelated topics?

3. UNDERSTANDING FEELINGS & IMPACT (0-20): Did they explore how problems affect the person emotionally and practically? Did they ask about frustrations, workarounds, and what matters most?

4. RELEVANCE & FOCUS (0-15): Were all questions relevant to understanding this person's life and problems? Deduct heavily for off-topic, joking, or nonsensical questions.

5. DISCOVERING SPECIFIC PROBLEMS (0-20): Based on the conversation, how many concrete, specific problems did the student manage to uncover? More specific details = higher score.

A score of 80+ should only be given for good interviewing — consistent open-ended questions, meaningful follow-ups, emotional exploration, and uncovering multiple specific problems.

A score of 50-60 is average — some good questions mixed with shallow ones.

A score below 40 means the student mostly asked yes/no questions, didn't follow up, or asked irrelevant things.

Respond with ONLY a number between 10 and 100. Nothing else."""

            eval_response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=10,
                temperature=0,
                messages=[{"role": "user", "content": eval_prompt}]
            ).content[0].text.strip()
            
            # Extract the number
            score = int(''.join(c for c in eval_response if c.isdigit())[:3])
            score = max(10, min(100, score))
        except Exception as e:
            print(f"Claude scoring failed, using fallback: {e}")
            # Basic fallback if API fails
            score = 40 + len([m for m in user_msgs if '?' in m]) * 3
            score = max(10, min(100, score))
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
        
        draw.rectangle([(20, 20), (780, 580)], outline='#1a1a1a', width=2)
        draw.text((400, 80), "CERTIFICATE OF COMPLETION", font=f1, fill='#1a1a1a', anchor='mm')
        draw.text((400, 140), "Empathy Interview Training", font=f3, fill='#6b6560', anchor='mm')
        if class_code:
            draw.text((400, 200), f"Class: {class_code}", font=f3, fill='#6b6560', anchor='mm')
        draw.text((400, 260), name, font=f2, fill='#1a1a1a', anchor='mm')
        draw.text((400, 340), "Successfully completed empathy interview", font=f3, fill='#333', anchor='mm')
        draw.text((400, 380), f"with {char['name']}", font=f3, fill='#333', anchor='mm')
        draw.text((400, 460), f"Empathy Score: {score}/100", font=f2, fill='#2a6e3f', anchor='mm')
        draw.text((400, 540), datetime.now().strftime("%B %d, %Y"), font=f3, fill='#6b6560', anchor='mm')
        
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
