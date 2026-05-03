# KNOCK — The Four Voices of October 1973

> *"Mama, take this badge off of me / I can't use it anymore"*
> — Bob Dylan, Knockin' on Heaven's Door (1973)

**Creative AI Installation · CSE 358 Introduction to Artificial Intelligence**

KNOCK is a living-memory documentary installation. It places four distinct American consciousnesses — a Vietnam veteran, a burned-out Berkeley protester, Bob Dylan himself, and a Gold Star mother — in the same October 1973 moment, all hearing *Knockin' on Heaven's Door* for the first time. The installation cycles through each voice continuously, generating psychological memories, synthesized visuals, neural speech, and ambient audio in real time. Every session is unique. No two knocks are the same.

---

## The Four Voices

| Voice | Identity | Location | Focus |
|---|---|---|---|
| **The Veteran** | Michael Reardon, 23 | Youngstown, OH — a diner | The war the country wants to forget |
| **The Idealist** | Ruth Abramowitz, 24 | Berkeley, CA — her apartment | A revolution that didn't happen |
| **The Subject** | Alias (Bob Dylan), 32 | Durango, Mexico — a film set trailer | Hiding inside a Western while the world calls him a prophet |
| **The Silent** | Dorothy Callahan, 51 | Akron, OH — a grocery store aisle | The weight of 58,220 names |

---

## AI Techniques Used

This project combines **four distinct generative AI technique families** working together in a single real-time pipeline.

### 1. Large Language Model (LLM) — Psychological Memory Generation
**Technology:** Groq API — LLaMA 3.3 70B / LLaMA 3.1 8B Instant / LLaMA 4 Scout (cascade fallback)

Each voice is powered by a deeply engineered character system prompt containing historical facts, biographical detail, and psychological constraints specific to that person's 1973 experience. On every cycle, the LLM generates a structured JSON memory object containing the character's spoken thought, internal memory, reaction to a specific Dylan lyric, and a prompt for image generation. The model is given conversation history (last 5 exchanges) so each cycle deepens rather than repeats.

A separate **Historian Layer** uses a second LLM call to inject one documented historical fact (drawn from a pool of 32 anchors across the four voices) into each cycle, grounding the fiction in real 1973 data.

A **Synthesis Layer** fires every 4 cycles, prompting the LLM to write a poet-historian meditation connecting all four voices' spoken thoughts into a single unified reflection.

### 2. Neural Text-to-Speech Synthesis (TTS)
**Technology:** Groq Orpheus v1 (English) → Edge-TTS Neural fallback

Each character has an assigned neural voice persona. The system generates WAV audio from the LLM's spoken output using Groq's Orpheus model. If Groq TTS fails (rate limit or API error), the system falls back instantly to Microsoft Edge-TTS neural voices, each matched to the character's demographic and tone. Speech duration is calculated programmatically to synchronize the installation's pacing — the next cycle does not begin until the voice has finished speaking.

| Character | Groq Orpheus Voice | Edge-TTS Fallback |
|---|---|---|
| The Veteran | troy | en-US-AndrewNeural |
| The Idealist | diana | en-US-AvaNeural |
| The Subject (Dylan) | daniel | en-US-BrianNeural |
| The Silent (Mother) | hannah | en-US-EmmaNeural |

### 3. Text-to-Image Diffusion
**Technology:** Pollinations AI (Stable Diffusion backend) → static fallback image

Each LLM memory cycle produces a cinematic image prompt constrained to a consistent aesthetic: black and white Kodak Tri-X grain, 16mm film still, 1973 documentary style. The image is requested concurrently with TTS generation (non-blocking) using `asyncio.create_task`. A rotating set of cinematographic styles (handheld shake, extreme close-up, chiaroscuro shadow) is applied per cycle to prevent visual repetition. If the image engine times out after 60 seconds, a pre-rendered "Lost Signal" 16mm static frame is displayed to maintain thematic continuity.

### 4. Ambient Music (Local Score Crossfader)
**Technology:** Pygame mixer with local audio track pool

The installation maintains a continuous ambient score by randomly selecting audio tracks from `static/score/` and crossfading between them every 4 cycles (3-second fade). This keeps the sonic environment alive without interrupting voice delivery. The music volume is set low (0.2) to sit beneath the speech layer.

### How the Techniques Interact

```
[USER CLICKS KNOCK]
        │
        ▼
[WebSocket opens — FastAPI]
        │
        ▼
[CYCLE START: Voice selected round-robin]
        │
        ├─► LLM CASCADE (Groq)
        │       └─ System prompt + character history → JSON memory object
        │       └─ Cascade: 70B Versatile → 8B Instant → LLaMA 4 Scout
        │
        ├─► HISTORIAN LAYER (Groq, parallel)
        │       └─ Draws 1 unused historical anchor per voice from 32-fact pool
        │       └─ LLM anchors the fictional memory to a documented 1973 event
        │
        ├─► CONCURRENT MEDIA PIPELINE (non-blocking asyncio.create_task)
        │       ├─► TTS: Groq Orpheus → Edge-TTS fallback → WAV/MP3 to disk
        │       ├─► Image: Pollinations Diffusion → fallback.png → WebSocket push
        │       └─► Music: Pygame crossfader (fires every 4 cycles)
        │
        ├─► WEBSOCKET PUSH → Frontend updates text, image, annotation in real time
        │
        ├─► [Audio duration calculated] → [Sleep until voice completes + 3s]
        │
        └─► Every 4 cycles: SYNTHESIS LAYER (Groq)
                └─ All four spoken_aloud fields → poet-historian meditation
                └─ 14-second display pause before next round begins
```

---

## Project Structure

```
Knock-AI-Project/
├── app.py              # FastAPI backend — all LLM, TTS, image, audio logic
├── index.html          # Frontend — WebSocket client, documentary UI
├── requirements.txt    # Python dependencies
├── .env example        # API key template
├── .gitignore
├── static/
│   ├── current_memory.png    # Generated image (overwritten each cycle)
│   ├── fallback.png          # 16mm "Lost Signal" frame (fail-safe)
│   ├── voice.wav / voice.mp3 # Generated speech (overwritten each cycle)
│   ├── assets/               # Static UI assets
│   └── score/                # Local ambient audio tracks (add your own)
```

---

## Requirements

- Python 3.10+
- A **Groq API key** (free tier works — the cascade handles rate limits automatically)
- A **Hugging Face API token** (used by `InferenceClient` initialization)
- Audio files (`.mp3`, `.wav`, or `.ogg`) placed in `static/score/` for ambient music
- A `static/fallback.png` image for the fail-safe display

---

## Setup & Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/ArdaDemirr/Knock-AI-Project.git
cd Knock-AI-Project
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install fastapi uvicorn groq edge-tts pygame pillow requests python-dotenv huggingface_hub
```

### Step 3 — Configure your API keys

Copy the example env file and fill in your keys:

```bash
cp ".env example" .env
```

Open `.env` and add:

```env
GROQ_API_KEY=your_groq_api_key_here
HF_API_TOKEN=your_huggingface_token_here
```

- Get a free Groq key at [console.groq.com](https://console.groq.com)
- Get a Hugging Face token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### Step 4 — Add ambient audio (optional but recommended)

Place one or more audio files (`.mp3`, `.wav`, `.ogg`) into `static/score/`. The installation crossfades between them automatically. Atmospheric, drone, or acoustic guitar tracks work best thematically.

### Step 5 — Run the installation

```bash
python app.py
```

The server starts on `http://127.0.0.1:8000`. Open that address in your browser.

### Step 6 — Experience the installation

Click **KNOCK** on the screen. A WebSocket connection opens and the installation begins cycling through the four voices. Each cycle:

1. The LLM generates a new psychological memory for the current voice
2. The text appears on screen with a historical annotation
3. A period-appropriate image develops (Polaroid reveal effect)
4. The voice speaks the memory aloud via neural TTS
5. After 4 voices, a synthesis meditation appears for 14 seconds
6. The cycle continues indefinitely — each session is unique

To stop, close the browser tab or kill the server (`Ctrl+C`).

---

## Historical Grounding

The installation does not treat 1973 as backdrop — it treats it as structural material. Every voice draws from a dedicated pool of 8 documented historical anchors, rotated randomly without repetition:

- The Veteran's pool includes the 1969 draft lottery mechanics, the March 29 troop withdrawal, Operation Dewey Canyon III, and the VA's 1973 PTSD statistics
- The Idealist's pool includes the May Day 1971 mass arrests, Nixon's 49-state landslide, Kent State, and COINTELPRO
- The Subject's pool includes the Newport 1965 electric controversy, the Basement Tapes, Woody Guthrie's death, and Dylan's 2016 Nobel lecture
- The Silent's pool includes the casualty notification procedure, Gold Star Mothers, the folded flag ceremony, and the 1982 Vietnam Memorial

These anchors are injected into every LLM cycle and shaped by a second model call into a single documented fact that appears on screen as an annotation — separating historical record from fictional memory throughout the experience.

---

## Technical Stack Summary

| Component | Technology |
|---|---|
| Backend framework | FastAPI + Uvicorn |
| Real-time communication | WebSockets |
| LLM inference | Groq API (LLaMA 3.3 70B / 3.1 8B / 4 Scout) |
| TTS synthesis | Groq Orpheus v1 → Edge-TTS (neural fallback) |
| Image generation | Pollinations AI (Stable Diffusion) → static fallback |
| Audio playback | Pygame mixer (crossfade, volume control) |
| Image processing | Pillow (PIL) |
| Concurrency | Python asyncio + asyncio.create_task |
| Frontend | Vanilla HTML/CSS/JS — WebSocket client |
| Environment management | python-dotenv |


## Credits

Built for **CSE 358 Introduction to Artificial Intelligence** — Spring 2025–2026.
Inspired by Bob Dylan's *Knockin' on Heaven's Door* (1973), written for Sam Peckinpah's *Pat Garrett and Billy the Kid*.
Featuring Groq LLaMA for real-time documentary intelligence.

## Screenshots

<img width="1901" height="906" alt="knock1" src="https://github.com/user-attachments/assets/ea24a0ab-1fc7-458e-9b07-d9a29aa1bc0d" />

<img width="1897" height="915" alt="knock2" src="https://github.com/user-attachments/assets/97217311-f19d-453a-b944-a59c4b653adb" />

<img width="1897" height="921" alt="knock3" src="https://github.com/user-attachments/assets/65b8b492-bbfc-4e60-918b-e5c43ea7cc51" />

<img width="1901" height="908" alt="knock4" src="https://github.com/user-attachments/assets/dd26e7af-610f-4d72-b6f6-15e7cff16345" />




