# KNOCK — Design Your Door

### CSE 358 · Creative AI Installation · Spring 2025–2026

> _"Mama, take this badge off of me / I can't use it anymore"_  
> — Bob Dylan, Knockin' on Heaven's Door (1973)

---

## What This Is

A living-memory installation. A Korean War veteran. Nashville, November 1973. A transistor radio playing Bob Dylan.

The installation runs an infinite loop of AI-generated consciousness — a veteran who has never spoken about what he carried for 20 years. The song is breaking something loose.

**This is not a chatbot. It is a grief machine.**

---

## AI Techniques Used (4 distinct layers)

| Layer                 | Technique                                                                 | Model                                 |
| --------------------- | ------------------------------------------------------------------------- | ------------------------------------- |
| Primary consciousness | Multi-turn LLM with psychological prompt engineering + dialogue history   | Groq / LLaMA 3.3 70B                  |
| Historical annotation | Secondary LLM call — a historian's voice annotating the veteran's thought | Groq / LLaMA 3.3 70B                  |
| Memory image          | Text-to-image diffusion with documentary photography style prompts        | Stable Diffusion v1.5 via HuggingFace |
| Music                 | Generative audio — ambient/melancholic compositions                       | MusicGen (Facebook) via HuggingFace   |
| Voice synthesis       | Neural TTS — slow, weathered, Southern male voice                         | Edge-TTS (en-US-GuyNeural)            |

---

## Architecture

```
[USER CLICKS KNOCK]
        │
        ▼
[WebSocket connection opens]
        │
        ▼
[CYCLE BEGINS]
        │
        ├─► GROQ (LLaMA 3.3 70B) — Multi-turn memory generation
        │       └─ System prompt: 800-word character profile (Korean War veteran, 1929-1973)
        │       └─ User prompt: specific memory seed (place, year, event)
        │       └─ Dialogue history: last 6 exchanges (veteran deepens, doesn't repeat)
        │       └─ Returns: internal_memory, dylan_trigger, emotional_undertow,
        │                   image_prompt, music_prompt, spoken_thought
        │
        ├─► GROQ (LLaMA 3.1 70B) — Historian annotation (parallel call)
        │       └─ Takes spoken_thought, returns 1973 historical context
        │
        ├─► Edge-TTS — Voice synthesis
        │       └─ Rate: -25%, Pitch: -15Hz (weary, deliberate speech)
        │       └─ '...' in text creates natural pauses
        │
        ├─► [Voice plays] → [Overlap: HuggingFace image generation]
        │
        ├─► [Image reveals via polaroid animation] → [Overlap: HuggingFace music generation]
        │
        ├─► [Music fades in at 4s] → [20s absorption pause]
        │
        └─► [Fade out] → [Next cycle — veteran goes deeper]
```

---

## Installation & Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/knock-door
cd knock-door
pip install fastapi uvicorn groq edge-tts pygame pillow requests python-dotenv websockets
```

### 2. Create `.env`

```
GROQ_API_KEY=your_groq_key_here
HF_API_TOKEN=your_huggingface_token_here
```

Get Groq API key free at: https://console.groq.com  
Get HuggingFace token at: https://huggingface.co/settings/tokens

### 3. Run

```bash
python main.py
```

Open `http://127.0.0.1:8000` in your browser.

Click **KNOCK**.

Wait. The first cycle takes 30–60 seconds while HuggingFace models boot.

---

## What Makes the Prompts Deep

The system prompt establishes:

- **Full biographical identity** — James Elroy Hatch, born 1929, Meridian MS, 7th Infantry Division
- **Specific trauma geography** — Chosin Reservoir, Heartbreak Ridge, Pusan Perimeter
- **Psychological state** — survivor's guilt, 20 years of silence, the VA appointment he stopped going to
- **Voice constraints** — Southern working-class, 1950s military, laconic, fragmented
- **Dylan-specific reaction** — what the harmonica does to him, why "badge" hits different if you've worn one

The **multi-turn memory system** means:

- Cycle 1: He remembers a battle
- Cycle 3: He starts naming a dead man
- Cycle 5: He addresses his estranged daughter indirectly
- Cycle 7: He speaks to his younger self

Each cycle the AI knows what was already said. The veteran deepens. He doesn't repeat.

---

## Historical Context (Constraint 3)

The 1973 context is load-bearing, not decorative:

- **Korea vs Vietnam**: The veteran watches the Vietnam antiwar movement and feels something he can't name — not anger, but recognition. His war was forgotten. These kids had a movement.
- **Pat Garrett & Billy the Kid**: Dylan wrote the song for a dying lawman who'd outlived his era. The veteran IS that lawman. He's been obsolete since 1953.
- **The badge**: "Take this badge off of me" — in the film, it's a literal sheriff's badge. For the veteran, it's everything he was trained to be. He can't use it anymore. There's no war. There's no welcome home.
- **"Too dark to see"**: The veteran has been living in that darkness. The song doesn't offer him light. It offers him company in the dark.

---

## Output Examples

**Spoken thought (cycle 3):**

> "Tommy Brewer... I said his name out loud in 1953 and then never again... You'd have hated this song, Tommy... too soft for you... but you never got old enough to go soft..."

**Historical annotation:**

> "The Korean War produced 36,940 American dead and no monument until 1995. This veteran's silence was not personal failure — it was national policy."

---

## Dependencies

```
fastapi, uvicorn, groq, edge-tts, pygame, Pillow, requests, python-dotenv
```

---

## Team / Individual

[Your name] — Individual submission  
All architectural decisions, prompt engineering, and philosophical direction are original.
