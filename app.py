import os
import json
import time
import asyncio
import requests
import io
import urllib.parse
import random
import shutil
import glob
import edge_tts
import pygame
from PIL import Image
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq
from huggingface_hub import InferenceClient

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
SUNO_API_KEY = os.getenv("SUNO_API_KEY")

if not GROQ_API_KEY or not HF_API_TOKEN:
    raise ValueError("Missing API Keys in .env file (GROQ_API_KEY and HF_API_TOKEN required)")

groq_client = Groq(api_key=GROQ_API_KEY)
hf_client = InferenceClient(token=HF_API_TOKEN)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
pygame.mixer.init(frequency=44100)

os.makedirs("static", exist_ok=True)
os.makedirs("static/assets", exist_ok=True)
os.makedirs("static/music_cache", exist_ok=True)

# ============================================================
# MUSIC CACHE CONFIG
# ============================================================

MUSIC_CACHE_DIR = "static/music_cache"

# 8 thematic variants — each generation picks the next one in sequence
SUNO_MUSIC_PROMPTS = [
    # 0 — classic Dylan fingerpicked
    ("slow acoustic guitar fingerpicked, blues harmonica, 1973 americana folk, "
     "melancholic minor key, sparse cinematic, instrumental no vocals, "
     "dusty tape warmth, knockin on heavens door dylan style, documentary score, mournful, quiet"),
    # 1 — slide guitar elegy
    ("open-tuned slide guitar, weeping harmonica, 1973 southern blues, "
     "slow progression, analog tape hiss, delta grief, no vocals, "
     "documentary score, vietnam era, sparse and lonely"),
    # 2 — late night piano
    ("solo piano nocturne, 1970s americana, sparse left hand, slow tempo meditative, "
     "single melody line, influenced by late night radio 1973, "
     "no vocals, instrumental, cinematic grief"),
    # 3 — banjo elegy
    ("clawhammer banjo, mountain folk, 1973 appalachian, mournful minor, "
     "sparse drums, acoustic bass, pat garrett billy the kid soundtrack style, "
     "no vocals, instrumental documentary"),
    # 4 — solo harmonica
    ("solo harmonica minor blues, 1973 late night, no other instruments, "
     "dusty room tone, long reverb, sustained bends, "
     "inspired by dylan basement tapes, somber, meditative, no vocals"),
    # 5 — nashville session
    ("acoustic guitar and pedal steel, 1973 nashville session, "
     "slow country elegy, minor key, inspired by knockin on heavens door, "
     "sparse drums brush and snare, instrumental no vocals, cinematic"),
    # 6 — dobro and strings
    ("dobro resonator guitar, sparse string quartet, 1973 americana, "
     "cinematic documentary score, slow tempo, melancholic, "
     "pat garrett soundtrack style, no vocals, vietnam era grief"),
    # 7 — upright bass duo
    ("upright bass and acoustic guitar duo, 1973 folk jazz, "
     "slow walking tempo, minor mode, sparse documentary, "
     "late night radio sound, dylan and the band style, no vocals"),
]
_suno_prompt_idx = 0

# ============================================================
# FOUR VOICES OF OCTOBER 1973
# ============================================================

VOICES = [
    {
        "id": "dylan",
        "name": "Subject: Alias",
        "description": "Durango, Mexico. 16mm handheld footage. He is hiding inside a Western.",
        "voice_role": "robert",
        "focus": "The death of folk sincerity and the birth of the '70s outlaw."
    },
    {
        "id": "protester",
        "name": "Subject: The Idealist",
        "description": "Berkeley. Grainy interview in a dark room. The 'Movement' is ending.",
        "voice_role": "sophia",
        "focus": "Watergate, the '72 landslide, and the realization that the revolution failed."
    },
    {
        "id": "soldier",
        "name": "Subject: The Veteran",
        "description": "Youngstown. Dim diner lighting. He is the physical cost of the era.",
        "voice_role": "troy",
        "focus": "The silence of 1973 and the 'badge' that no longer has a war."
    },
    {
        "id": "mother",
        "name": "Subject: The Silent",
        "description": "Akron. Kitchen table interview. The weight of 58,220 names.",
        "voice_role": "martha",
        "focus": "The personal grief that political slogans ignored."
    }
]

voice_histories = {v["id"]: [] for v in VOICES}

# ============================================================
# PER-VOICE HISTORICAL ANCHOR POOLS  (8 facts × 4 voices)
# Each voice draws randomly without repetition; resets when exhausted.
# ============================================================

HISTORICAL_ANCHORS: dict[str, list[str]] = {
    "soldier": [
        "Draft lottery 1969: number 47 guaranteed induction. 366 capsules drawn from a drum — numbers below 195 were nearly certain to go.",
        "March 29, 1973: the last U.S. combat troops left Vietnam. No ceremony. No welcome home crowds. Nobody said anything.",
        "Operation Dewey Canyon III, April 1971: Vietnam veterans threw their medals over a fence at the U.S. Capitol. Some wept. Some did not.",
        "Agent Orange was sprayed across 4.5 million acres of Vietnamese land. Soldiers handling it were told it was harmless.",
        "Unemployment among Vietnam veterans in 1973 ran at 12% — double the national average.",
        "By 1973, the VA estimated 700,000 Vietnam veterans were experiencing severe psychological trauma. PTSD was not a diagnosis yet.",
        "The last 591 American POWs were returned from Hanoi on March 29, 1973. The men who stayed in had no ceremony and no crowd.",
        "By 1973, more Vietnam veterans had died by suicide after returning home than had died in combat.",
    ],
    "protester": [
        "May Day 1971: 12,000 people arrested in Washington D.C. — the largest mass arrest in U.S. history. Most charges were later dismissed.",
        "Nixon won 49 states in November 1972, carrying 60.7% of the popular vote. McGovern carried only Massachusetts and D.C.",
        "Vietnam Moratorium, October 15, 1969: an estimated 2 million Americans participated — the largest single-day protest in U.S. history.",
        "Kent State, May 4, 1970: four students killed, nine wounded. The National Guard fired for thirteen seconds.",
        "SDS collapsed in 1969, fracturing into the Weathermen and scores of local chapters. The movement had already begun eating itself.",
        "The FBI's COINTELPRO program infiltrated every major antiwar organization. The Church Committee would expose this in 1975.",
        "The War Powers Resolution was passed over Nixon's veto on November 7, 1973 — the week after this October.",
        "Dylan refused to appear at the March on Washington in August 1963, though Baez sang and Peter, Paul and Mary performed.",
    ],
    "dylan": [
        "Pat Garrett and Billy the Kid began filming in January 1973 in Durango, Mexico. Peckinpah went $1 million over budget.",
        "Newport Folk Festival, July 25, 1965: Dylan played three electric songs. Pete Seeger reportedly tried to cut the sound cables.",
        "Dylan's motorcycle accident, July 29, 1966: he disappeared for eighteen months. He later said he was simply hiding.",
        "Blonde on Blonde, 1966: the first double album in rock history, recorded in Nashville in under three weeks of session time.",
        "Woody Guthrie died October 3, 1967. Dylan had visited him in Greystone Hospital regularly since January 1961.",
        "The Basement Tapes, summer 1967: recorded in a pink house in Woodstock with The Band. Not officially released until 1975.",
        "John Wesley Harding, December 1967: recorded in three Nashville sessions. Biblical, spare, and produced without overdubs.",
        "Dylan's Nobel Prize lecture, 2016: forty-five minutes on Buddy Holly, Moby Dick, and the Odyssey. The Vietnam War was not mentioned.",
    ],
    "mother": [
        "Quang Tri Province, March 1972: North Vietnamese forces overran the province. James Callahan was killed March 30, 1972.",
        "58,220 Americans were killed in Vietnam. The youngest was 16. The oldest was 62. Each had a mother.",
        "The casualty notification system: a uniformed officer arrived at the front door. No phone call. No warning. Just the knock.",
        "Gold Star Mothers of America, founded 1928: by 1973, its Vietnam-era chapter was the largest in the organization's history.",
        "The Vietnam Veterans Memorial would not be built until November 1982. Dorothy Callahan will be 60 years old when it opens.",
        "The folded flag given at military funerals follows a 13-fold procedure. The 13th fold: to honor God. There is no fold for grief.",
        "By 1973, the Akron, Ohio metropolitan area had lost 47 sons in Vietnam. Their names are on a plaque most people walk past.",
        "The form letter signed by the President: an estimated 3,000 families received nearly identical letters. The signature was a stamp.",
    ],
}

# Per-voice shuffled draw pools — refilled when exhausted
_voice_anchor_pool: dict[str, list[str]] = {vid: [] for vid in HISTORICAL_ANCHORS}


def get_next_anchor(voice_id: str) -> str:
    """Draw a random unused fact for this voice. Resets pool when all facts used."""
    pool = _voice_anchor_pool[voice_id]
    if not pool:
        pool[:] = random.sample(HISTORICAL_ANCHORS[voice_id], len(HISTORICAL_ANCHORS[voice_id]))
    return pool.pop()

# ============================================================
# GROQ ENGINE
# ============================================================

def get_groq_completion(messages, system_prompt, temperature=0.88, max_tokens=1500):
    models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "meta-llama/llama-4-scout-17b-16e-instruct"
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
# VOICE SYSTEM PROMPTS
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
# SYNTHESIS + HISTORICAL FACT
# ============================================================

def generate_synthesis(all_memories):
    system = """You are a poet-historian. You have just watched four Americans hear the same song on the same October day in 1973.
Write a meditation — not a summary. 4-6 sentences. Dense. Use real names.
What is the door they are all knocking on?
RESPOND ONLY in valid JSON: {"synthesis": "Your 4-6 sentence meditation."}
"""
    summary = "\n\n".join([f"[{vid}]: {mem.get('spoken_aloud', '')}" for vid, mem in all_memories.items()])
    result, _ = get_groq_completion(
        [{"role": "user", "content": f"Here is what each voice said:\n\n{summary}\n\nNow write the synthesis."}],
        system, temperature=0.82, max_tokens=500
    )
    if result:
        return result.get("synthesis", "")
    return "Four people. One song. One October. 58,220 names. The door does not open from this side."

def generate_historical_fact(voice_id, spoken, anchor):
    system = """You are a historian. One sentence only. A real, specific, documented fact.
RESPOND ONLY in valid JSON: {"fact": "One sentence."}"""
    result, _ = get_groq_completion(
        [{"role": "user", "content": f"Voice: {voice_id}\nThey said: \"{spoken}\"\nAvailable anchor: {anchor}\nGive the one historical fact."}],
        system, temperature=0.6, max_tokens=120
    )
    if result:
        return result.get("fact", anchor)
    return anchor

# ============================================================
# MUSIC SYSTEM — Suno Cache + Background Generation
# ============================================================

def get_cached_tracks():
    """Return list of locally saved Suno tracks, newest first."""
    tracks = glob.glob(f"{MUSIC_CACHE_DIR}/*.mp3")
    tracks.sort(key=os.path.getmtime, reverse=True)
    return tracks

def play_track(path):
    """Load and loop a track in pygame with fade-in."""
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(loops=-1, fade_ms=4000)
        print(f"   -> Music: Now playing {os.path.basename(path)}")
        return True
    except Exception as e:
        print(f"   ! Music playback error: {e}")
        return False

# Suno statuses that carry audio data (FIRST_SUCCESS = first clip ready, SUCCESS = all done)
_SUNO_AUDIO_STATUSES = {"SUCCESS", "FIRST_SUCCESS", "completed", "success", "first_success"}
_SUNO_FAIL_STATUSES  = {"FAILED", "failed", "error", "ERROR"}


def _extract_suno_audio_url(record: dict) -> str | None:
    """
    Try every known key path to find the audio URL inside a Suno poll record.
    Returns the URL string, or None if nothing was found.
    Logs the full record for debugging when extraction fails.
    """
    response_obj = record.get("response", {})

    # Candidate track lists — try both shapes the API has been observed to return
    candidate_lists = [
        response_obj.get("data"),       # data.response.data[]
        response_obj.get("sunoData"),   # data.response.sunoData[]
        record.get("data"),             # data.data[] (flat shape)
    ]

    # Keys the first track object might carry the audio URL under
    audio_keys = ["audio_url", "audioUrl", "stream_audio_url", "streamAudioUrl",
                  "clipAudioUrl", "clip_audio_url", "url"]

    for track_list in candidate_lists:
        if not isinstance(track_list, list) or len(track_list) == 0:
            continue
        first = track_list[0]
        if not isinstance(first, dict):
            continue
        for key in audio_keys:
            val = first.get(key)
            if val and isinstance(val, str) and val.startswith("http"):
                print(f"   -> Suno: audio_url found under key '{key}': {val[:80]}...")
                return val

    # Nothing found — log the full record so the dev can add the right key
    print(f"   ! Suno: Could not extract audio_url. Full record dump:")
    try:
        print(json.dumps(record, indent=2)[:2000])
    except Exception:
        print(str(record)[:2000])
    return None


async def generate_suno_track_background():
    """
    Submit to sunoapi.org, poll until FIRST_SUCCESS or SUCCESS,
    save to cache, crossfade pygame into new track.

    Status flow: PENDING → TEXT_SUCCESS → FIRST_SUCCESS → SUCCESS
    Audio is downloadable from FIRST_SUCCESS onwards.
    """
    global _suno_prompt_idx
    _current_suno_prompt = SUNO_MUSIC_PROMPTS[_suno_prompt_idx % len(SUNO_MUSIC_PROMPTS)]
    _suno_prompt_idx += 1
    print(f"   -> Suno: Using music prompt variant #{_suno_prompt_idx} of {len(SUNO_MUSIC_PROMPTS)}")

    if not SUNO_API_KEY:
        print("   ! SUNO_API_KEY missing in .env — skipping music generation.")
        return

    print("   -> Suno: Submitting music generation request...")

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json"
    }

    # ---- STEP 1: Submit ----
    try:
        res = await asyncio.to_thread(
            requests.post,
            "https://api.sunoapi.org/api/v1/generate",
            json={
                "customMode": False,
                "instrumental": True,
                "model": "V3_5",
                "prompt": _current_suno_prompt,
                "callBackUrl": "https://httpbin.org/post"  # dummy — we poll manually

            },
            headers=headers,
            timeout=30
        )

        print(f"   -> Suno submit: HTTP {res.status_code} | {res.text[:400]}")

        if res.status_code != 200:
            print(f"   ! Suno rejected request (status {res.status_code})")
            return

        submit_data = res.json()

        # sunoapi.org wraps taskId inside data{} on some responses, or at top level
        task_id = None
        inner = submit_data.get("data")
        if isinstance(inner, dict):
            task_id = inner.get("taskId") or inner.get("task_id")
        if not task_id:
            task_id = submit_data.get("taskId") or submit_data.get("task_id")
        if not task_id:
            print(f"   ! Suno gave no taskId. Full response: {json.dumps(submit_data)[:800]}")
            return

        print(f"   -> Suno: Task submitted (ID: {task_id}). Polling every 5s (max 5 min)...")

    except Exception as e:
        print(f"   ! Suno submit error: {e}")
        return

    # ---- STEP 2: Poll for FIRST_SUCCESS or SUCCESS ----
    audio_url = None
    for attempt in range(60):   # 60 × 5s = 5 minutes max
        await asyncio.sleep(5)
        try:
            status_res = await asyncio.to_thread(
                requests.get,
                f"https://api.sunoapi.org/api/v1/generate/record-info?taskId={task_id}",
                headers=headers,
                timeout=20
            )

            if status_res.status_code != 200:
                print(f"   -> Suno poll #{attempt+1}: HTTP {status_res.status_code} — retrying")
                continue

            poll_data = status_res.json()

            record = poll_data.get("data", {})
            if not isinstance(record, dict):
                print(f"   -> Suno poll #{attempt+1}: unexpected data shape — {str(poll_data)[:120]}")
                continue

            status = record.get("status", "UNKNOWN")
            print(f"   -> Suno poll #{attempt+1}: status={status}")

            if status in _SUNO_AUDIO_STATUSES:
                print(f"   -> Suno FULL RECORD: {json.dumps(record)}")  # DEBUG: verify audio_url key path
                audio_url = _extract_suno_audio_url(record)

                if audio_url:
                    print(f"   -> Suno: Audio ready at status '{status}'. Breaking poll loop.")
                    break
                else:
                    # URL not in response yet even though status looks ready
                    # (can happen with FIRST_SUCCESS before CDN propagation)
                    if status == "FIRST_SUCCESS":
                        print("   -> Suno: FIRST_SUCCESS but no URL yet — will retry in 5s")
                        continue
                    # For full SUCCESS with no URL, something is truly wrong
                    print("   ! Suno: status SUCCESS but could not extract audio_url — aborting.")
                    return

            elif status in _SUNO_FAIL_STATUSES:
                print(f"   ! Suno generation failed (status={status}): {json.dumps(record)[:400]}")
                return

            else:
                # Normal in-progress states: PENDING, TEXT_SUCCESS
                pass  # just loop

        except Exception as e:
            print(f"   ! Suno poll error on attempt {attempt+1}: {e}")
            continue

    if not audio_url:
        print("   ! Suno timed out after 5 minutes — no audio_url received.")
        return

    # ---- STEP 3: Download and cache ----
    print(f"   -> Suno: Downloading track from {audio_url[:80]}...")
    try:
        dl_response = await asyncio.to_thread(
            lambda: requests.get(audio_url, timeout=120, stream=False)
        )
        if dl_response.status_code != 200:
            print(f"   ! Suno download failed: HTTP {dl_response.status_code}")
            return

        audio_bytes = dl_response.content
        if len(audio_bytes) < 10_000:
            # Sanity check — a real MP3 should be at least ~10 KB
            print(f"   ! Suno: Downloaded file suspiciously small ({len(audio_bytes)} bytes). Aborting.")
            return

        filename = f"{MUSIC_CACHE_DIR}/suno_{int(time.time())}.mp3"
        with open(filename, "wb") as f:
            f.write(audio_bytes)
        print(f"   -> Suno: Saved {len(audio_bytes)//1024} KB to {filename}")

        # ---- STEP 4: Crossfade into new track ----
        # Fade out whatever is playing, wait for fade to complete, then start new track
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(3000)
            await asyncio.sleep(3.5)  # let fade complete
        play_track(filename)

    except Exception as e:
        print(f"   ! Suno download/save error: {e}")

# ============================================================
# IMAGE GENERATION
# ============================================================

def save_polaroid(img):
    w, h = img.size
    m = min(w, h)
    img.crop(((w - m) // 2, (h - m) // 2, (w + m) // 2, (h + m) // 2)).save("static/current_memory.png")

def generate_image(prompt, cycle_num):
    print(f"   -> Image Engine: Generating for cycle {cycle_num}...")
    styles = ["handheld shake", "extreme close up", "grainy profile", "chiaroscuro shadow"]
    style = styles[cycle_num % len(styles)]
    full_prompt = (
        f"black and white, Kodak Tri-X grain, 16mm film still, {style}, "
        f"dirty lens, 1973 documentary, {prompt}"
    )
    safe_prompt = urllib.parse.quote(full_prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{safe_prompt}"
        f"?width=512&height=512&nologo=true&seed={random.randint(0,99999)}"
    )
    try:
        time.sleep(random.uniform(1.0, 3.0))  # avoid 429
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content))
            save_polaroid(img)
            print("   -> Image Engine: Pollinations success.")
            return True
        print(f"      [Pollinations] HTTP {r.status_code}")
    except Exception as e:
        print(f"      [Pollinations] Error: {e}")
    return False

# ============================================================
# TTS — Groq Orpheus → Edge-TTS fallback
# ============================================================

async def speak(text, voice_id):
    import re
    voice_map_groq = {"soldier": "troy", "protester": "diana", "dylan": "daniel", "mother": "hannah"}
    voice_map_edge = {
        "soldier": "en-US-AndrewNeural",
        "protester": "en-US-AvaNeural",
        "dylan": "en-US-BrianNeural",
        "mother": "en-US-EmmaNeural"
    }

    if not text or not re.search('[a-zA-Z0-9]', text):
        print("   ! Speech text empty or punctuation-only. Using placeholder.")
        text = "I don't have the words."

    try:
        print(f"   -> Groq TTS: Voice '{voice_map_groq.get(voice_id, 'troy')}'...")
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
        print(f"   ! Groq TTS Error: {e}. Falling back to Edge-TTS...")

    try:
        communicate = edge_tts.Communicate(
            text,
            voice_map_edge.get(voice_id, "en-US-AndrewNeural"),
            rate="-10%"
        )
        await communicate.save("static/voice.mp3")
        return "static/voice.mp3"
    except Exception as ef:
        print(f"   !! All TTS failed: {ef}")
        return None

# ============================================================
# MASTER LOOP
# ============================================================

async def run_installation_loop(websocket):
    cycle = 0
    round_memories = {}
    music_started = False

    # ---- MUSIC STARTUP ----
    # On first run: play cached track instantly if available,
    # always generate a fresh one in background.
    cached = get_cached_tracks()
    if cached:
        print(f"   -> Music: Found {len(cached)} cached track(s). Playing latest immediately.")
        play_track(cached[0])
        music_started = True
    else:
        print("   -> Music: No cache yet. Generating first track in background (will take ~2-3 min)...")

    # Always kick off a fresh generation on startup
    asyncio.create_task(generate_suno_track_background())

    while True:
        voice = VOICES[cycle % len(VOICES)]
        vid = voice["id"]
        anchor = get_next_anchor(vid)

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
                   else f"You have already spoken {len(history)//2} times tonight. "
                        f"The song is almost over. Go deeper. The thing you have been avoiding — go there.")
            )
        }

        result, model = get_groq_completion(history[-6:] + [user_msg], VOICE_SYSTEMS[vid])

        if not result:
            result = {
                "spoken_aloud": "I don't have the words...",
                "image_prompt": "1973 empty room, single light bulb, wooden chair",
                "music_prompt": "silence and tape hiss and the sound of someone leaving"
            }

        voice_histories[vid].append(user_msg)
        voice_histories[vid].append({"role": "assistant", "content": json.dumps(result)})
        if len(voice_histories[vid]) > 10:
            voice_histories[vid] = voice_histories[vid][-10:]

        spoken = result.get("spoken_aloud", "...")
        round_memories[vid] = result

        # Stagger historical fact call to avoid Groq rate limit collision
        await asyncio.sleep(1.5)
        hist_fact = generate_historical_fact(vid, spoken, anchor)

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
        secondary_map = {
            "soldier":   result.get("the_question", ""),
            "protester": result.get("the_dylan_complication", ""),
            "dylan":     result.get("fear_about_the_song", ""),
            "mother":    result.get("what_she_wants_to_ask_god", ""),
        }

        await websocket.send_json({
            "action": "update_text",
            "cycle": cycle + 1,
            "voice_id": vid,
            "voice_location": voice["description"],
            "internal_memory": memory_map.get(vid, ""),
            "dylan_trigger": trigger_map.get(vid, ""),
            "emotional_undertow": secondary_map.get(vid, ""),
            "annotation": hist_fact,
            "dylan_connection": f"Voice Subject: {voice['name']}",
            "spoken_thought": spoken
        })

        print("   -> [Pipeline] Starting Concurrent Processing...")

        # ---------------------------------------------------------
        # PIPELINE 1: MUSIC — every 8 cycles generate a fresh track
        # The current track keeps looping. New track crossfades in
        # when Suno finishes (background, ~2-3 min).
        # ---------------------------------------------------------
        if cycle > 0 and cycle % 8 == 0:
            print("   -> Music: Scheduling fresh Suno generation in background...")
            asyncio.create_task(generate_suno_track_background())

        # ---------------------------------------------------------
        # PIPELINE 2: IMAGE GENERATION (delayed 2.5s so voice starts first)
        # ---------------------------------------------------------
        image_prompt = result.get("image_prompt", "1973 America, black and white")

        # Default-arg capture freezes image_prompt and cycle at their current
        # values — prevents closure bugs when the outer loop advances before
        # this create_task fires.
        async def fetch_image_and_update(
            _prompt=image_prompt, _cycle=cycle
        ):
            await asyncio.sleep(2.5)
            success = await asyncio.to_thread(generate_image, _prompt, _cycle)

            if not success:
                print("   !! Image engine failed. Using fallback.")
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

        # ---------------------------------------------------------
        # PIPELINE 3: VOICE — Groq Orpheus TTS → Edge-TTS fallback
        # ---------------------------------------------------------
        # Capture spoken and vid by value so the closure is stable
        # even though we await it immediately (defensive, and good practice).
        async def fetch_and_play_voice(
            _spoken=spoken, _vid=vid
        ):
            audio_file = await speak(_spoken, _vid)
            word_count = len(_spoken.split())
            duration = max(3.0, word_count * 0.4 + 1.0)

            if audio_file and os.path.exists(audio_file):
                try:
                    sfx = pygame.mixer.Sound(audio_file)
                    sfx.play()
                    played_dur = sfx.get_length()
                    if played_dur > 1.0:
                        duration = played_dur
                except Exception as e:
                    print(f"      [Audio] Pygame playback error: {e}")
            return duration

        audio_duration = await fetch_and_play_voice()

        # ---------------------------------------------------------
        # SYNTHESIS CHECK — every 4 cycles (one full round of voices)
        # ---------------------------------------------------------
        if (cycle + 1) % 4 == 0 and len(round_memories) >= 4:
            synth = generate_synthesis(round_memories)
            await websocket.send_json({"action": "show_synthesis", "text": synth})
            await asyncio.sleep(14)
            round_memories = {}

        # Wait for voice to finish + 3s breathing room
        await asyncio.sleep(audio_duration + 3.0)

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