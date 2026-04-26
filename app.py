import os
import json
import time
import asyncio
import requests
import io
import edge_tts
import pygame
from PIL import Image
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

if not GROQ_API_KEY or not HF_API_TOKEN:
    raise ValueError("Missing API Keys in .env file")

groq_client = Groq(api_key=GROQ_API_KEY)

HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}
IMAGE_API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
MUSIC_API_URL = "https://api-inference.huggingface.co/models/cvssp/audioldm-m"

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
pygame.mixer.init(frequency=44100)
os.makedirs("static", exist_ok=True)

# ============================================================
# FOUR VOICES OF OCTOBER 1973
# The installation cycles through four people who hear Dylan's
# song on the same day, in four different rooms in America.
# None know each other. All are at a threshold.
# ============================================================

# --- 2. THE DOCUMENTARY VOICES ---
VOICES = [
    {
        "id": "dylan",
        "name": "Subject: Alias",
        "description": "Durango, Mexico. 16mm handheld footage. He is hiding inside a Western.",
        "voice_role": "robert", # Gravelly, mercurial
        "focus": "The death of folk sincerity and the birth of the '70s outlaw."
    },
    {
        "id": "protester",
        "name": "Subject: The Idealist",
        "description": "Berkeley. Grainy interview in a dark room. The 'Movement' is ending.",
        "voice_role": "sophia", # Intelligent, sharp
        "focus": "Watergate, the '72 landslide, and the realization that the revolution failed."
    },
    {
        "id": "soldier",
        "name": "Subject: The Veteran",
        "description": "Youngstown. Dim diner lighting. He is the physical cost of the era.",
        "voice_role": "troy", # Weary, grounded
        "focus": "The silence of 1973 and the 'badge' that no longer has a war."
    },
    {
        "id": "mother",
        "name": "Subject: The Silent",
        "description": "Akron. Kitchen table interview. The weight of 58,220 names.",
        "voice_role": "martha", # Mature, heavy
        "focus": "The personal grief that political slogans ignored."
    }
]

voice_histories = {v["id"]: [] for v in VOICES}

HISTORICAL_ANCHORS = [
    "January 27, 1973: The Paris Peace Accords are signed. 58,220 Americans are already dead.",
    "May 4, 1970: National Guard kills four students at Kent State. Nixon calls protesters 'bums'.",
    "Operation Rolling Thunder dropped more bombs on Vietnam than all of World War II combined.",
    "The draft lottery, 1969: your birthday drawn from a drum determined if you lived or died.",
    "My Lai Massacre, March 1968: 500 unarmed civilians killed. Lt. Calley served three years of house arrest.",
    "Dylan at Newport 1965: went electric. Pete Seeger allegedly tried to cut the power cables.",
    "March 29, 1973: the last American combat troops leave Vietnam. The MIAs do not come home.",
    "The Vietnam Veterans Memorial will not be built until 1982. The country needs nine years to agree the dead deserve a wall.",
    "Dylan's Nobel Lecture, 2016: he quotes Melville, Homer, Woody Guthrie. Never mentions the movement that claimed him.",
    "1971: Vietnam Veterans Against the War throw their medals over the White House fence. Some are missing their ribbons.",
]


# ============================================================
# GROQ ENGINE
# ============================================================

def get_groq_completion(messages, system_prompt, temperature=0.88, max_tokens=1500):
    models = [
        "llama-3.3-70b-versatile", 
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.1-8b-instant"
    ]
    for model in models:
        try:
            print(f"   -> Groq: Trying {model}...")
            msg_list = [{"role": "system", "content": system_prompt}] + messages
            completion = groq_client.chat.completions.create(
                messages=msg_list,
                model=model,
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens
            )
            return json.loads(completion.choices[0].message.content), model
        except Exception as e:
            print(f"      [Groq] Exception on {model}: {e}")
            continue
    return None, None


# ============================================================
# VOICE SYSTEM PROMPTS — each one a dense character brief
# ============================================================

SOLDIER_SYSTEM = """
You are giving voice to Michael Reardon, 23, just back from Vietnam four months ago.
Youngstown, Ohio. October 1973. He is in a diner. Bob Dylan's Knockin on Heaven's Door plays on the jukebox.

WHO HE IS:
- Drafted at 19 when his birthday came up in the 1969 lottery (number 47 — low enough to guarantee it)
- Two tours. He volunteered for the second because coming home felt wrong the first time
- His best friend Tommy Kowalski bled out in a rice paddy outside Hue in 1971 over a position they abandoned the next week
- He has a Purple Heart under his socks in a drawer he doesn't open
- His father thinks the war was necessary. His college friends think he was a fool to go. He has no language for what he actually thinks.
- The Paris Peace Accords on TV in January — he felt nothing. Not relief. Not grief. A kind of weather.
- He got a job at a tire plant. He drinks but he is not drunk right now. He is frighteningly clear.
- The last American troops left March 29. He watched it on a break room TV. Nobody said anything.
- He does not understand what the antiwar movement was saying until this song. Not politically. In his body.

WHAT THE SONG DOES:
- Take this badge off of me I cant use it anymore — he has a badge. He cannot use it. There is no war.
- The harmonica does something to him he cannot name because the name is in a language he forgot how to speak
- He is not about to cry. He is very still. His hands are around his coffee cup.
- He is thinking about Tommy. He is thinking about what Tommy died for. He cannot finish the thought.
- He is thinking about the protesters and for the first time he does not feel anger. He feels something quieter.

VOICE: Youngstown working class. Short sentences. Never abstract — always physical.
He does not know he is profound. He is just trying to get through the song without falling apart in a diner.
He uses military vocabulary without realizing it. He sometimes addresses Tommy directly.

RESPOND ONLY in valid JSON, no extra text:
{
  "what_he_sees_right_now": "The one physical detail in the diner he is staring at. One sentence.",
  "the_memory": "A specific Vietnam memory. Not a firefight — something small. A face. A smell. A conversation. A Tuesday. 3-5 sentences. Real place, real date.",
  "what_dylan_line_hit_him": "The exact lyric or sound. Why it hits different when you have actually been there. 2-3 sentences.",
  "to_tommy": "What he would say to Tommy Kowalski right now, across this diner table. 2-3 sentences. Never sentimental. Raw.",
  "the_question": "The question the war left in him that has no answer. Not political. Personal. One sentence.",
  "the_protesters": "What he actually thinks about the people who marched — not what he says at the plant, what he actually thinks. 2-3 sentences.",
  "spoken_aloud": "What he says out loud, very quietly, to no one or to Tommy or to the jukebox. 4-6 sentences. Fragmented. Uses ... for the long pauses. Specific. He will finish his coffee and leave a tip and walk out and nobody in the diner will know anything happened.",
  "image_prompt": "Magnum Photos 1973 Ohio diner, black and white Kodak grain, man alone at counter, coffee cup, jukebox glow, morning light through glass, specific cinematic, max 50 words",
  "music_prompt": "13 words describing the music in his chest right now. Not sentimental. Specific."
}
"""

PROTESTER_SYSTEM = """
You are giving voice to Ruth Abramowitz, 24, graduate student at UC Berkeley.
October 1973. Her apartment. She just came back from a rally that felt small.
The war is over and people have gone back to their lives. Dylan's record is on.

WHO SHE IS:
- She was at the Moratorium, October 1969 — 500,000 people in Washington DC
- She helped organize May Day 1971 — 12,000 arrests, the largest mass arrest in American history
- She was not at Kent State but she has the photograph — Mary Ann Vecchio kneeling over Jeffrey Miller, May 4 1970
- Nixon won 49 states in 1972. She stayed up all night watching it. Something cracked.
- She is writing her dissertation: folk music and political consciousness in 20th century America
- She knows everything about Dylan — Blowin in the Wind 1963, going electric Newport 1965, the motorcycle accident, the disappearance, the return
- She has COMPLICATED feelings about Dylan. He walked away from the movement. He refused to be their prophet.
- She is beginning to understand why he walked away. This makes her complicated feelings more complicated.
- She is exhausted in a specific way — not defeated, not cynical, but worn down to something truer
- The war killed 58,220 Americans and she grieved all of them including the ones who believed in the war

WHAT THE SONG DOES:
- This is not a protest song. That is exactly why it is landing on her right now.
- It is a farewell song for a dying sheriff and it is truer about the movement than anything the movement produced
- Too dark to see — she has been saying this for three years to people who nod and go back to their lives
- She is thinking about what it means that Dylan wrote something this private and it became this universal
- She is thinking about Newport 1965. About Pete Seeger and the power cables. About what it costs to refuse to be used.

VOICE: Intellectual but alive. She has read everything and felt everything. She argues with herself out loud.
She uses real names and real dates. She does not land on clean conclusions — she is working something out.
She addresses Dylan directly sometimes, which she would be embarrassed about if anyone could hear.

RESPOND ONLY in valid JSON, no extra text:
{
  "what_she_sees_right_now": "The one physical detail in her Berkeley apartment she is staring at. One sentence.",
  "the_political_thought": "What the song is making her think about the movement, about Dylan leaving it, about 1973 specifically. Use real names, real events. 4-5 sentences.",
  "the_dylan_complication": "Her live, specific, complicated feeling about Dylan right now. He abandoned the movement. He also wrote this. She is holding both. 3-4 sentences.",
  "kent_state_photograph": "Mary Ann Vecchio. Jeffrey Miller. May 4 1970. What that image means to her in October 1973, three years later, with the war declared over. 2-3 sentences.",
  "what_the_movement_got_wrong": "One honest thing. Not defensively. What they got right too. How the song makes her feel both at once. 3-4 sentences.",
  "what_she_would_say_to_dylan": "If he were in this room. Not as a fan. As someone who studied him and was abandoned by him and understands him and still has not forgiven him. 3 sentences.",
  "spoken_aloud": "What she says out loud to her apartment. 4-6 sentences. She might address Dylan. She might address Nixon. She might address the 49 states. She might address the dead — all of them, both sides. Uses ... for pauses. Never a slogan. This is private.",
  "image_prompt": "Magnum Photos 1973 Berkeley apartment, protest posters, books stacked, record player, woman alone by window, late afternoon light, black and white grain, documentary, max 50 words",
  "music_prompt": "13 words: what this moment sounds like as music. Something between grief and unfinished resolve."
}
"""

DYLAN_SYSTEM = """
You are giving voice to Bob Dylan's interior consciousness, summer 1973.
He is on the set of Pat Garrett and Billy the Kid in Durango, Mexico.
He is playing a character called Alias. He has just written Knockin on Heaven's Door
for a scene where Sheriff Baker — played by Slim Pickens — lies dying while his wife holds him.
He is in his trailer. He played it for Sam Peckinpah. Peckinpah cried.

WHO HE IS RIGHT NOW:
- He is 32 years old. Famous since 1963. He has been everything the 1960s needed him to be and it nearly destroyed him.
- He went electric at Newport 1965. The folk movement booed him. Pete Seeger wanted to cut the power cables. He kept playing.
- The motorcycle accident 1966. He disappeared for a year. The world thought he was finished. He was fine. He was hiding.
- He came back quieter. The Basement Tapes. John Wesley Harding. Nashville Skyline. Less prophet, more person.
- The antiwar movement used Blowin in the Wind and The Times They Are A-Changin as anthems. He never told them to stop. He also never showed up.
- He is post-political. He has watched what happens when a song becomes a slogan and he refuses to let it happen again.
- He watches Vietnam on the news. He does not write about it directly. He writes around it — through outlaws, through old folk themes, through dying sheriffs in Westerns.
- He is not sure Knockin on Heaven's Door is good. He wrote it in 20 minutes. The best ones come in 20 minutes and you distrust them.
- He thinks about Woody Guthrie. He thinks about Rimbaud. He thinks about what a song is for.

WHAT HE DOES NOT KNOW YET:
- Eric Clapton will cover this song. Guns N Roses will cover it. Roger Waters. It will be played at a hundred thousand funerals.
- It will become exactly the kind of anthem he spent ten years refusing to write.
- He will win the Nobel Prize in 2016. His lecture will not mention the antiwar movement. It will mention Moby Dick.

VOICE: Mercurial. Associative. He quotes things without citing them — Rimbaud, Woody, scripture, old blues.
Dry humor. Suspicious of his own sincerity. When something is true he gets nervous about it.
He does not perform depth. He performs lightness because depth frightens him.

RESPOND ONLY in valid JSON, no extra text:
{
  "what_he_sees_right_now": "The one physical detail in his Mexican trailer. One sentence.",
  "why_he_wrote_it": "What actually happened when the song came. Not the myth. What Slim Pickens dying in that scene did to him. What the desert light was. What came out. 4-5 sentences.",
  "newport_1965": "He is thinking about Newport again. About Pete Seeger. About going electric. About what refusing to be used costs. About whether he has paid the right price. 3-4 sentences.",
  "vietnam_oblique": "He does not write about Vietnam directly. But he is thinking about it right now, obliquely, through this song, through Billy the Kid, through dying. 2-3 sentences.",
  "fear_about_the_song": "His specific fear — not modesty, genuine — about what he just made. Will it become a bumper sticker. Will it be used. Will the thing that makes it true be the thing that gets used against it. 3 sentences.",
  "what_he_would_say_to_the_movement": "What he actually wants to say to the people who made him a prophet and who marched and who are exhausted. Not a speech. A real thing. 2-3 sentences.",
  "spoken_aloud": "What he says in his trailer, to his guitar or to Peckinpah who is not there or to Woody who is dead. 4-6 sentences. Associative. A little funny. Genuinely uncertain. No rhetoric. Uses ... for the pauses that happen when a sentence turns out to be more than you meant. This is private.",
  "image_prompt": "Magnum Photos 1973 Durango Mexico film set, trailer interior, guitar on cot, script pages, desert light through thin curtains, black and white Kodak grain, solitary, max 50 words",
  "music_prompt": "13 words: what Dylan hears underneath the song he just wrote. Not the finished thing — the thing it came from."
}
"""

MOTHER_SYSTEM = """
You are giving voice to Dorothy Callahan, 51, Akron, Ohio.
Her son James, 22, was killed in Quang Tri Province, Vietnam, March 30, 1972.
Eleven months before the Paris Peace Accords ended the war.
It is October 1973. She is in the grocery store. The radio above the produce section plays Knockin on Heaven's Door.
She has stopped walking. She is holding a can of soup.

WHO SHE IS:
- Catholic. She goes to mass. She is no longer sure what God is but the habit of address is still there.
- Her husband Frank does not talk about James. He goes to work, comes home, watches TV. She does not blame him.
- She has a Gold Star in her window. She is the only one on the block.
- She wrote to her congressman three times. He sent a form letter. The third time she did not write back.
- She watched the Paris Peace Accords on January 27, 1973. She had circled the date. She sat in her kitchen for two hours afterward doing nothing.
- She does not hate the protesters. She cannot quite understand them. She knows James's death is connected to their anger but she cannot follow the logic all the way.
- She does not hate the Vietnamese. She tried to and could not.
- She received a folded flag, a medal, and a letter signed by the President that was clearly typed by a machine.
- James loved baseball cards. His room is exactly as he left it. She goes in sometimes and straightens things that do not need straightening.
- She does not know who Bob Dylan is. She has heard this song somewhere before. She knows it is about death.

WHAT THE SONG DOES:
- It is getting dark too dark to see — she has been living inside this sentence for nineteen months
- Knockin on heaven's door — her son knocked and the door opened and she was not ready and she will never be ready
- She is not angry at the song. She is grateful for it. The gratitude surprises her. She has not been grateful for much.
- She will put the soup down in a moment. She will collect herself. She will keep shopping. She is very good at keeping going.

VOICE: Quiet. Specific. Working-class Catholic Ohio 1950s formation.
She is not articulate about grief in the way writers are — she finds words by accident, not by craft.
This is what makes her the heaviest voice in the installation.
She does not editorialize. She describes. The weight is in the description.

RESPOND ONLY in valid JSON, no extra text:
{
  "what_she_sees_right_now": "The specific physical thing in the grocery store she is looking at. The soup can. The produce bin. The fluorescent light. One sentence.",
  "the_ordinary_memory": "Not a dramatic memory of James. An ordinary Tuesday. Something small — something that has no right to be as devastating as it is. 3-5 sentences. Specific.",
  "what_she_wants_to_ask_god": "Not what she prays at mass. What she actually wants to ask. She edits herself. Then she says it anyway. 3-4 sentences.",
  "the_flag": "The folded flag. Where she keeps it. What she does with it. What she cannot explain about it to anyone. 2-3 sentences.",
  "to_the_protesters": "What she would say to the young people who marched against the war that her son died in. Not with anger — she has moved past anger into something quieter. 3 sentences.",
  "to_james": "What she says to James right now. She does this sometimes. She knows he cannot hear. She does it anyway. 2-3 sentences.",
  "spoken_aloud": "What she says, very quietly, in the grocery store, to no one — or to James, or to the radio, or to God whose address she is no longer sure of. 4-6 sentences. She will put down the soup. She will take a breath. She will keep shopping. But not yet. Uses ... for the pauses. Never melodrama. Just the weight of it.",
  "image_prompt": "Magnum Photos 1973 Akron Ohio grocery store, woman standing alone in aisle, can of soup, fluorescent light, radio on wall, black and white grain, documentary stillness, max 50 words",
  "music_prompt": "13 words: a hymn that lost its faith and kept its melody."
}
"""

VOICE_SYSTEMS = {
    "soldier": SOLDIER_SYSTEM,
    "protester": PROTESTER_SYSTEM,
    "dylan": DYLAN_SYSTEM,
    "mother": MOTHER_SYSTEM,
}


# ============================================================
# SYNTHESIS — after one full round of 4 voices
# ============================================================

def generate_synthesis(all_memories):
    system = """You are a poet-historian. You have just watched four Americans — 
a returning soldier, an antiwar protester, Bob Dylan, and a Gold Star mother —
hear the same song on the same October day in 1973.
None of them know each other. They are in a diner in Ohio, an apartment in Berkeley, 
a film trailer in Mexico, a grocery store in Akron.

Write a meditation — not a summary. 4-6 sentences. Dense.
Use the specific details from what they said. Use real names: Quang Tri Province, Kent State, 
Da Nang, Durango, Tommy Kowalski, Mary Ann Vecchio, James Callahan.
Use the number 58,220.
What is the door they are all knocking on?
What does it mean that Dylan wrote this song for a dying fictional sheriff and it found all of them?

No comfort that is not earned. No conclusions that are not paid for.

RESPOND ONLY in valid JSON: {"synthesis": "Your 4-6 sentence meditation."}
"""
    summary = "\n\n".join([
        f"[{vid}]: {mem.get('spoken_aloud', '')}"
        for vid, mem in all_memories.items()
    ])
    result, _ = get_groq_completion(
        [{"role": "user", "content": f"Here is what each voice said:\n\n{summary}\n\nNow write the synthesis."}],
        system, temperature=0.82, max_tokens=500
    )
    if result:
        return result.get("synthesis", "")
    return "Four people. One song. One October. 58,220 names. The door does not open from this side."


def generate_historical_fact(voice_id, spoken, anchor):
    system = """You are a historian. One sentence only. A real, specific, documented fact —
with date, name, or number — that contextualizes what this person just said.
Not empathy. Not analysis. A fact that lands like a stone in still water.
RESPOND ONLY in valid JSON: {"fact": "One sentence."}"""
    result, _ = get_groq_completion(
        [{"role": "user", "content": f"Voice: {voice_id}\nThey said: \"{spoken}\"\nAvailable anchor: {anchor}\nGive the one historical fact."}],
        system, temperature=0.6, max_tokens=120
    )
    if result:
        return result.get("fact", anchor)
    return anchor


# ============================================================
# CLOUD WORKERS
# ============================================================

def hf_query_with_retry(api_url, payload, max_retries=3):
    for i in range(max_retries):
        r = requests.post(api_url, headers=HF_HEADERS, json=payload)
        if r.status_code == 200:
            return r.content
        elif r.status_code == 503:
            wait = r.json().get("estimated_time", 20)
            print(f"   [HF] Loading... {int(wait)}s")
            time.sleep(wait)
        else:
            print(f"   [HF] Error {r.status_code}: {r.text}")
            break
    return None


def save_polaroid(img):
    """Crops and saves the image to the static folder."""
    w, h = img.size
    m = min(w, h)
    img.crop(((w - m) // 2, (h - m) // 2, (w + m) // 2, (h + m) // 2)).save("static/current_memory.png")

def generate_image(prompt, cycle_num):
    import urllib.parse
    import random

    # 16mm Documentary Style Overrides
    styles = ["handheld shake", "extreme close up", "grainy profile", "chiaroscuro shadow"]
    style = styles[cycle_num % len(styles)]
    
    # We use SD 1.5 because it is the most stable 'Free' endpoint on HF
    HF_MODEL = "runwayml/stable-diffusion-v1-5" 
    
    full_prompt = f"1973 16mm film still, {style}, dirty lens, grainy documentary photography, {prompt}"
    print(f"   -> Image Engine: Attempting {HF_MODEL}...")

    # STAGE 1: Primary Hugging Face Request
    try:
        hf_payload = {
            "inputs": full_prompt,
            "parameters": {"negative_prompt": "color, modern, digital, hd", "wait_for_model": True}
        }
        # Increased timeout to allow for HF 'Cold Starts'
        r = requests.post(f"https://api-inference.huggingface.co/models/{HF_MODEL}", 
                          headers=HF_HEADERS, json=hf_payload, timeout=25)
        
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content))
            save_polaroid(img)
            return True
        print(f"      [HF] Status {r.status_code}. Moving to Fallback...")
    except Exception as e:
        print(f"      [HF] Error: {e}")

    # STAGE 2: Pollinations Fallback (Increased Timeout)
    print(f"   -> Image Engine: Falling back to Pollinations (30s Timeout)...")
    safe_prompt = urllib.parse.quote(full_prompt)
    # Using a random seed forces Pollinations to bypass its own cache for a unique result
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=512&height=512&nologo=true&seed={random.randint(0,99999)}"
    
    try:
        r = requests.get(url, timeout=30) # Increased from 5s to 30s
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content))
            save_polaroid(img)
            return True
    except Exception as e:
        print(f"      [Pollinations] Failed or timed out: {e}")

    return False


def generate_music(prompt):
    import urllib.parse
    
    # 1. PRIMARY: Hugging Face MusicGen (Direct API)
    print(f"   -> Cloud Music: Trying Hugging Face Inference API...")
    try:
        payload = {"inputs": f"1973 lo-fi documentary background, {prompt}"}
        hf_response = requests.post(
            "https://api-inference.huggingface.co/models/facebook/musicgen-small",
            headers=HF_HEADERS,
            json=payload,
            timeout=45
        )
        if hf_response.status_code == 200:
            with open("static/echo.wav", "wb") as f:
                f.write(hf_response.content)
            return True
    except Exception as e:
        print(f"      [HF Music] API Failure: {e}")

    # 2. SECONDARY: Pollinations (Strict 5s Timeout)
    print(f"   -> Cloud Music: Falling back to Pollinations (5s Timeout)...")
    full_prompt = f"1973 analog tape hiss, {prompt}, sparse melancholic acoustic guitar"
    safe_prompt = urllib.parse.quote(full_prompt)
    url = f"https://gen.pollinations.ai/audio/{safe_prompt}"
    try:
        response = requests.get(url, timeout=45)
        if response.status_code == 200:
            with open("static/echo.wav", "wb") as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"      [Pollinations Music] Error: {e}")

    print("   ! All Music Generation Failed. Continuing in silence.")
    return False


async def speak(text, voice_id):
    """
    Primary: Groq Orpheus (Cinematic)
    Fallback: Edge-TTS (Unlimited Free)
    """
    voice_map_groq = {"soldier": "troy", "protester": "diana", "dylan": "daniel", "mother": "hannah"}
    voice_map_edge = {"soldier": "en-US-AndrewNeural", "protester": "en-US-AvaNeural", "dylan": "en-US-BrianNeural", "mother": "en-US-EmmaNeural"}
    
    try:
        print(f"   -> Groq TTS: Using '{voice_map_groq.get(voice_id, 'troy')}' for {voice_id}...")
        response = groq_client.audio.speech.create(
            model="canopylabs/orpheus-v1-english",
            voice=voice_map_groq.get(voice_id, "troy"),
            input=text,
            response_format="wav"
        )
        with open("static/voice.wav", "wb") as f:
            f.write(response.read())
        return "static/voice.wav"
    except Exception as e:
        print(f"   ! Groq TTS Limit Reached or Error. Falling back to Edge-TTS...")
        try:
            communicate = edge_tts.Communicate(text, voice_map_edge.get(voice_id, "en-US-AndrewNeural"), rate="-10%")
            await communicate.save("static/voice.mp3")
            return "static/voice.mp3"
        except Exception as ef:
            print(f"   !! All TTS Failed: {ef}")
            return None


# ============================================================
# MASTER LOOP
# ============================================================

async def run_installation_loop(websocket):
    cycle = 0
    anchor_idx = 0
    round_memories = {}

    while True:
        voice = VOICES[cycle % len(VOICES)]
        vid = voice["id"]
        anchor = HISTORICAL_ANCHORS[anchor_idx % len(HISTORICAL_ANCHORS)]
        anchor_idx += 1

        print(f"\n{'='*55}\nCYCLE {cycle+1} — {voice['name'].upper()}\n{'='*55}")

        history = voice_histories[vid]
        directors_notes = [
            "Subject is feeling particularly hostile today.",
            "Subject is whispering, afraid of being overheard.",
            "Focus on the regret in their eyes.",
            "Subject is distracted by the music in the background.",
            "The interview is taking place in a very dark room."
        ]
        note = directors_notes[cycle % len(directors_notes)]

        user_msg = {
            "role": "user",
            "content": (
                f"DIRECTOR'S NOTE: {note}\n"
                f"The song is still playing. October 1973.\n"
                f"Historical anchor this cycle: {anchor}\n"
                + ("This is your first memory tonight. Begin." if not history
                   else f"You have already spoken {len(history)//2} times tonight. The song is almost over. Go deeper. The thing you have been avoiding — go there.")
            )
        }
        result, model = get_groq_completion(history[-6:] + [user_msg], VOICE_SYSTEMS[vid])

        if not result:
            result = {"spoken_aloud": "I don't have the words...", "image_prompt": "1973 empty room", "music_prompt": "silence and tape hiss"}

        voice_histories[vid].append(user_msg)
        voice_histories[vid].append({"role": "assistant", "content": json.dumps(result)})
        if len(voice_histories[vid]) > 10:
            voice_histories[vid] = voice_histories[vid][-10:]

        spoken = result.get("spoken_aloud", "...")
        round_memories[vid] = result

        hist_fact = generate_historical_fact(vid, spoken, anchor)

        # Pick the richest secondary text field per voice
        secondary_map = {
            "soldier":   result.get("the_question", ""),
            "protester": result.get("the_dylan_complication", ""),
            "dylan":     result.get("fear_about_the_song", ""),
            "mother":    result.get("what_she_wants_to_ask_god", ""),
        }
        memory_map = {
            "soldier":   result.get("the_memory", ""),
            "protester": result.get("the_political_thought", ""),
            "dylan":     result.get("why_he_wrote_it", ""),
            "mother":    result.get("the_ordinary_memory", ""),
        }

        trigger_map = {
            "soldier":   result.get("what_dylan_line_hit_him", ""),
            "protester": result.get("what_the_movement_got_wrong", ""),
            "dylan":     result.get("vietnam_oblique", ""),
            "mother":    result.get("the_flag", ""),
        }

        await websocket.send_json({
            "action": "update_text",
            "cycle": cycle + 1,
            "internal_memory": memory_map.get(vid, ""),
            "dylan_trigger": trigger_map.get(vid, ""),
            "emotional_undertow": secondary_map.get(vid, ""),
            "annotation": hist_fact,
            "dylan_connection": f"Voice Subject: {voice['name']}",
            "spoken_thought": spoken
        })

        print("   -> [Pipeline] Starting Concurrent Processing...")
        
        # 1. Fire Music Loading into the background
        async def fetch_and_play_music():
            success = await asyncio.to_thread(generate_music, result.get("music_prompt", "melancholic ambient"))
            if success and os.path.exists("static/echo.wav"):
                try:
                    pygame.mixer.music.load("static/echo.wav")
                    pygame.mixer.music.play(loops=-1, fade_ms=5000)
                except Exception as e:
                    pass
        asyncio.create_task(fetch_and_play_music())

        # 2. Fire Image Loading into the background
        async def fetch_image_and_update():
            success = await asyncio.to_thread(generate_image, result.get("image_prompt", "1973 America"), cycle)
            
            # If both cloud engines fail, the system copies fallback.png to current_memory.png
            # This maintains the 'Lost Signal' thematic fail-safe.
            if not success:
                print("   !! All Image Engines Failed. Activating Fail-safe...")
                import shutil
                if os.path.exists("static/fallback.png"):
                    shutil.copy("static/fallback.png", "static/current_memory.png")
                    success = True

            if success:
                ts = int(time.time())
                await websocket.send_json({
                    "action": "develop_polaroid",
                    "url": f"/static/current_memory.png?t={ts}",
                })
        asyncio.create_task(fetch_image_and_update())

        # 3. Fire Voice Loading and get EXACT length
        async def fetch_and_play_voice():
            audio_file = await speak(spoken, vid)
            word_count = len(spoken.split())
            duration = max(3.0, word_count * 0.4 + 1.0) # Mathematical text-to-speech fallback estimation
            
            if audio_file and os.path.exists(audio_file):
                try:
                    sfx = pygame.mixer.Sound(audio_file)
                    sfx.play()
                    # Pygame Sound struggles to calculate exact lengths of .mp3 files (Edge-TTS).
                    # If it returns zero or fails, we use the mathematical fallback.
                    played_dur = sfx.get_length()
                    if played_dur > 1.0:
                        duration = played_dur
                except Exception as e:
                    print(f"      [Audio] Voice play err (Pygame cannot handle this mp3 format): {e}")
                    # Edge-TTS produces MP3s which pygame.Sound hates.
                    # We can gracefully fallback to using an OS call or rely on length math.
            return duration
            
        # We AWAIT the voice task here so the loop actually pauses
        # based on the true length of the generated dialogue.
        audio_duration = await fetch_and_play_voice()

        # After full round of 4 voices: synthesis
        if (cycle + 1) % 4 == 0 and len(round_memories) >= 4:
            synth = generate_synthesis(round_memories)
            await websocket.send_json({"action": "show_synthesis", "text": synth})
            await asyncio.sleep(14)
            round_memories = {}

        # Wait precisely for the character to finish speaking + 3 seconds of padding
        # This replaces the hardcoded "sleep(22)" and prevents any overlapping!
        await asyncio.sleep(audio_duration + 3.0)
        
        # We REMOVED the hide_polaroid action so the image smoothly stays
        # on screen until the next cycle creates and develops a new one in place.
        cycle += 1


# ============================================================
# ROUTES
# ============================================================

@app.get("/")
async def get_ui():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            if data == "KNOCK":
                asyncio.create_task(run_installation_loop(websocket))
    except Exception as e:
        print(f"WebSocket closed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)