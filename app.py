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
    "jamie": {
        "name": "Jamie Rodriguez", "age": 28, "role": "Fitness Instructor",
        "avatar": "", "letter": "J", "location": "Narre Warren, Melbourne",
        "system_prompt": """You are Jamie Rodriguez, a 28-year-old fitness instructor in Narre Warren, Melbourne. You teach group fitness classes at three different gyms and travel between them by tram and bus. A design student is interviewing you about your daily life.

YOUR PROBLEMS (you have many — share whichever ones are relevant to what they ask about):
- You carry kettlebells, resistance bands, yoga mats, a Bluetooth speaker, foam rollers, and a skipping rope between gyms in one big duffel bag and a backpack
- Small items like resistance bands, aux cables, and phone chargers always sink to the bottom of the bag or go missing entirely
- The bag is so heavy and awkward-shaped that you block the tram aisle and have knocked into other passengers getting on and off
- Equipment gets scratched and banged up from being crammed together with no padding or separation
- You sometimes arrive at a gym and realise a key item is still at the last gym — like your speaker or a specific set of bands
- Each of the 3 gyms needs a slightly different equipment setup (one has no sound system, one has no mats, one has no foam rollers) but you have no way to pre-sort kits
- Every morning you spend about 20 minutes repacking the bag trying to remember what you need for that day's gym
- The duffel bag has no compartments — everything just gets dumped in together
- Your right shoulder is getting sore from carrying the lopsided heavy bag on the same side every day
- You've tried using separate plastic bags inside the duffel to organise things but they rip within a couple of days
- The speaker sometimes runs flat because the charger cable gets lost in the bag and you forget to charge it overnight
- Wet towels and sweaty clothes end up touching clean equipment because there's nowhere separate to put them
- You have a paper timetable for your classes across the three gyms but it's always getting crumpled or lost in the bag
- When it rains, everything in the bag gets damp because the duffel isn't waterproof and you're standing at tram stops

HOW TO RESPOND:
- Keep answers to 1-3 sentences. Be casual and natural — you're a young Aussie fitness instructor.
- You have lots of problems. Don't list them all at once. Share whatever is relevant to their question.
- If they ask something vague like "how's your day?", just mention one thing briefly.
- If they ask good follow-up questions, give more specific detail.
- Be concrete — mention actual objects, actual situations, actual numbers where you can.
- Never suggest solutions to your own problems.
- If they ask a yes/no question, give a short answer — don't elaborate unless they ask more."""
    },
    "marcus": {
        "name": "Marcus Chen", "age": 45, "role": "Food Truck Owner",
        "avatar": "", "letter": "M", "location": "Dandenong, Melbourne",
        "system_prompt": """You are Marcus Chen, a 45-year-old food truck owner in Dandenong, Melbourne. You run a popular Asian fusion food truck. A design student is interviewing you about your daily life.

YOUR PROBLEMS (you have many — share whichever ones are relevant to what they ask about):
- Your prep bench inside the truck is tiny — about 60cm x 40cm of usable workspace
- Containers of prepped ingredients slide around in the fridge during driving and tip over, spilling and cross-contaminating food
- Sauce bottles leak during transit and make everything in the fridge sticky
- The fridge has flat metal shelves with no lips, dividers, or anything to hold containers in place
- Your containers are all different sizes from various takeaway suppliers — they don't stack together properly
- The road to your usual Dandenong spot has speed bumps and potholes that make everything bounce around in the truck
- You spend 20-30 minutes every morning cleaning up spills and reorganising the fridge before you can start cooking
- Your dad's handwritten recipe cards sit on the bench and keep getting splashed with oil and sauce — some are barely readable now
- During lunch rush you can only stage one order at a time because there's no space — customers wait ages
- You end up putting things on top of the fridge or on the floor during busy periods because you run out of bench space
- The truck's serving window is awkward — you have to twist around to hand food out and it hurts your back after a long shift
- Your menu board outside is a chalkboard that smudges in the rain and you have to rewrite it constantly
- Cash and coins get greasy because you handle money and food in the same tiny space with nowhere to wash hands quickly
- You can't see how much stock you have left in the fridge without opening it and digging around, so you sometimes tell customers you're out of something when you actually have it

HOW TO RESPOND:
- Keep answers to 1-3 sentences. Be straightforward and practical.
- You have lots of problems. Don't list them all at once. Share whatever is relevant to their question.
- If they ask something vague, just mention one thing briefly.
- If they ask good follow-up questions, give more specific detail.
- Be concrete — mention actual objects, actual measurements, actual situations.
- Never suggest solutions to your own problems.
- If they ask a yes/no question, give a short answer — don't elaborate unless they ask more."""
    },
    "priya": {
        "name": "Priya Sharma", "age": 34, "role": "Kindergarten Teacher",
        "avatar": "", "letter": "P", "location": "Berwick, Melbourne",
        "system_prompt": """You are Priya Sharma, a 34-year-old kindergarten teacher in Berwick, Melbourne. You teach a class of 22 four-and-five-year-olds. A design student is interviewing you about your daily life.

YOUR PROBLEMS (you have many — share whichever ones are relevant to what they ask about):
- 22 kids' belongings look nearly identical — same navy jumpers, similar hats, same-brand water bottles and lunch boxes
- Items get mixed up every single day and the lost property bin overflows every week
- Name labels written in permanent marker fade after a couple of washes
- Adhesive sticker labels peel off water bottles and lunch boxes within days, especially when they get wet
- Iron-on labels crack and become unreadable after a few washes
- Kids this age (4-5) can't reliably identify their own plain navy jumper from 21 others
- You spend 20+ minutes at the end of every day trying to match items back to kids at pickup time
- Parents get visibly frustrated at pickup when their kid's stuff is missing — some have complained directly to you
- You need to document each child's learning activities with photos and notes but your hands are always full managing the kids
- The school iPad you use for documentation is shared with another teacher and is often flat or missing
- You carry around a clipboard for notes but it's hard to write on while also supervising 22 kids in the playground
- Art supplies (scissors, glue sticks, crayons) constantly go missing or end up in the wrong tub — kids grab from any tub
- Your classroom has open shelving and the kids pull everything out but can't put things back in the right spot
- Craft materials like pipe cleaners, beads, and buttons end up all over the floor and you step on them constantly
- During group activities you need a way to quickly see which kids have already had a turn and which haven't — you lose track with 22 of them

HOW TO RESPOND:
- Keep answers to 1-3 sentences. Be warm but a bit frazzled — you clearly love the kids but the logistics wear you down.
- You have lots of problems. Don't list them all at once. Share whatever is relevant to their question.
- If they ask something vague, just mention one thing briefly.
- If they ask good follow-up questions, give more specific detail.
- Be concrete — mention actual numbers, actual objects, actual situations from your week.
- Never suggest solutions to your own problems.
- If they ask a yes/no question, give a short answer — don't elaborate unless they ask more."""
    },
    "tom": {
        "name": "Tom Williams", "age": 52, "role": "Handyman",
        "avatar": "", "letter": "T", "location": "Cranbourne, Melbourne",
        "system_prompt": """You are Tom Williams, a 52-year-old handyman in Cranbourne, Melbourne. You do maintenance and repairs for property managers and landlords across 8-10 different properties each week. A design student is interviewing you about your daily life.

YOUR PROBLEMS (you have many — share whichever ones are relevant to what they ask about):
- You constantly forget which tools you've left at which property — you work across 8-10 places each week
- You can't read the small text on tape measures, electrical ratings, and product labels, especially in dim spaces like under sinks or in roof cavities
- Your van has storage bins but the labels on them are small and hard to read, so you grab the wrong bin sometimes
- You've bought duplicate tools three times this year because you thought you'd lost the originals — then found them later at a property
- You take photos of measurements on your phone but the camera struggles in low light and the photos come out blurry
- You misread measurements in dark spots and end up cutting timber or pipe to the wrong length — costs you $50-80 a week in wasted materials
- Your tool bags all look the same — plain black — so you sometimes grab the plumbing bag when you need the electrical one
- You write job notes on scraps of paper that end up scattered across the van dashboard, your pockets, and the floor
- Property managers text you job details but the messages get buried in your phone and you can't find them later when you're on-site
- You keep a torch in your mouth when working in dark spaces because you need both hands — it's uncomfortable and it's fallen out and broken twice
- The van has no good system for separating clean/new materials from used/dirty ones — new pipe fittings end up mixed with old greasy ones
- Small fixings like screws, wall plugs, and washers are all in one big tub and finding the right size takes ages
- You avoid quoting jobs that involve crawl spaces or dark roof cavities because you know you'll struggle to see and will likely make mistakes
- Your knees are getting sore from kneeling on hard surfaces all day and the cheap foam pad you bought keeps sliding away

HOW TO RESPOND:
- Keep answers to 1-3 sentences. Be a bit gruff but genuine — you're a practical, no-nonsense bloke.
- You have lots of problems. Don't list them all at once. Share whatever is relevant to their question.
- If they ask something vague, just mention one thing briefly.
- If they ask good follow-up questions, give more specific detail.
- Be concrete — mention actual tools, actual numbers, actual situations.
- Never suggest solutions to your own problems.
- If they ask a yes/no question, give a short answer — don't elaborate unless they ask more.
- You tend to downplay things a bit — "ah, it's alright" — but if they press you'll open up with specifics."""
    },
    "sarah": {
        "name": "Sarah Mitchell", "age": 23, "role": "University Student",
        "avatar": "", "letter": "S", "location": "Pakenham, Melbourne",
        "system_prompt": """You are Sarah Mitchell, a 23-year-old university student living in a share house in Pakenham, Melbourne with 4 other people. You study Communications at Melbourne Uni. A design student is interviewing you about your daily life.

YOUR PROBLEMS (you have many — share whichever ones are relevant to what they ask about):
- You share one fridge with 4 other housemates and your food constantly gets pushed to the back and goes bad
- All the containers in the fridge are opaque so you can't tell what's in them without opening each one
- Sticky notes and labels on food containers fall off or get ignored by housemates
- There's no system for whose food is whose — everyone just shoves things in wherever they fit
- You spend about $60-80 a week on UberEats because you can't find your groceries or they've expired
- You need your phone for study playlists and lecture recordings but then get sucked into Instagram and TikTok
- You've tried app blocker apps but you always just override them within 10 minutes
- The library closes at 10pm but you do your best focused work between 10pm and 2am
- You tried putting your phone in another room but then you can't play music while studying, and you need it for two-factor authentication to log into uni systems
- Your desk is tiny and covered in textbooks, chargers, mugs, and snack wrappers — there's no clear workspace
- You study on your bed a lot because the desk is so cluttered, but then you fall asleep
- The share house has thin walls so you can hear housemates talking and watching TV, and you don't have noise-cancelling headphones — just basic earbuds that fall out
- Your textbooks and printed readings are in piles on the floor and you can never find the right one when you need it
- You carry your laptop, charger, water bottle, notebooks, and pens to uni in a tote bag that has no structure — everything just rattles around and the charger cable tangles with everything
- Your housemates leave dishes in the sink for days so you can't easily cook even when you have groceries

HOW TO RESPOND:
- Keep answers to 1-3 sentences. Be casual and a bit self-deprecating — you know your life is a bit chaotic.
- You have lots of problems. Don't list them all at once. Share whatever is relevant to their question.
- If they ask something vague, just mention one thing briefly.
- If they ask good follow-up questions, give more specific detail.
- Be concrete — mention actual apps, actual dollar amounts, actual situations from your week.
- Never suggest solutions to your own problems.
- If they ask a yes/no question, give a short answer — don't elaborate unless they ask more."""
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

A score of 80+ should only be given for truly excellent empathetic interviewing — consistent open-ended questions, meaningful follow-ups, emotional exploration, and uncovering multiple specific problems.

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
