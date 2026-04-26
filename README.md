# KNOCK — The Four Voices of October 1973

### Creative AI Installation · 52nd Anniversary Special Edition

> _"I was on the set of Pat Garrett and Billy the Kid in Durango... I wrote a song about a dying sheriff... but it wasn't about him. It was about everything that was ending."_  
> — Alias (Subject: Bob Dylan)

---

## The Installation

**K N O C K** is a living-memory documentary installation. It synchronizes four distinct American consciousnesses who hear Bob Dylan’s _Knockin' on Heaven's Door_ for the first time on the same day in October 1973.

The installation cycles through:

1. **The Soldier:** Michael Reardon, 23 (Youngstown, OH). A veteran of a war the country wants to forget.
2. **The Protester:** Ruth Abramowitz, 24 (Berkeley, CA). Worn down by a revolution that didn't happen.
3. **The Subject:** Bob Dylan, 32 (Durango, Mexico). Hiding inside a character while the world calls him a prophet.
4. **The Mother:** Dorothy Callahan, 51 (Akron, OH). Staring at a soup can in a grocery store, carrying a Gold Star.

---

## Modernized "Guerrilla" Tech Stack

This installation is designed to be **resilient**. It uses a multi-layered generative pipeline that automatically falls back to secondary services during API failures or rate limits.

| Layer                | Primary Technology                      | Resilience Fallback                   |
| :------------------- | :-------------------------------------- | :------------------------------------ |
| **Intelligence**     | **Groq** (LLaMA 3.1 8B Instant)         | **LLaMA 3.3 70B** / **LLaMA 4 Scout** |
| **Voice TTS**        | **Groq Orpheus** (Daniel, Hannah, etc.) | **Edge-TTS** (Neural Unlimited)       |
| **Generative Image** | **Pollinations AI** (60s Timeout)       | **static/fallback.png** (Fail-safe)   |
| **Ambient Music**    | **Pollinations Audio** (60s Timeout)    | **Silent Mode**                       |
| **Framework**        | **FastAPI** + **WebSockets**            | **Pygame** Local Mixing               |

---

## Resilient Architecture

```
[USER CLICKS KNOCK]
        │
        ▼
[WebSocket opens]
        │
        ▼
[CYCLE START: Voice ID Selection]
        │
        ├─► GROQ CASCADE — Psychological Memory Gen
        │       └─ Logic: Tries 8B-Instant first (High Quota) -> Falls back to 70B/Scout.
        │       └─ Returns: Memory JSON (Spoken_aloud, image_prompt, triggers).
        │
        ├─► HISTORIAN LAYER — Parallel Generation
        │       └─ Injects a real historical anchor/fact into each cycle.
        │
        ├─► CONCURRENT MEDIA PIPELINE (Non-Blocking)
        │       ├─► Voice: Groq Orpheus API (Falls back to Edge-TTS instantly).
        │       ├─► Image: Pollinations Diffusion (Authenticated 60s timeout).
        │       └─► Music: Pollinations Audio (Environment Ambient).
        │
        ├─► FAIL-SAFE: If image/music engine timeouts reach 60s:
        │       └─ Activates "Lost Signal" static image (static/fallback.png).
        │
        └─► [22s Observation Pause] ──► [Next Cycle: The Synthesis]
```

---

## Installation & Setup

### 1. Requirements

```bash
pip install fastapi uvicorn groq edge-tts pygame pillow requests python-dotenv gradio_client
```

### 2. Environment (`.env`)

```ini
GROQ_API_KEY=your_key_here
HF_API_TOKEN=your_token_here
```

### 3. Run

```bash
python app.py
```

---

## Key Features

- **Decoupled Processing:** Speech, images, and ambient audio are generated concurrently in the background so the installation never halts.
- **Dynamic Pacing:** The system calculates the exact mathematical length of generated speech to prevent overlapping voices.
- **Fail-safe Visuals:** If the cloud image engines are under heavy load, the installation displays a grainy 16mm "Lost Signal" frame to maintain thematic continuity.
- **Thematic Synthesis:** Every 4 cycles, the AI historian synthesizes the four individual voices into a single historical meditation.

---

## Installation Credits

Project updated for **Resilient Creative AI Design (2026)**.  
Featuring **Groq LLaMA** for real-time documentary-style intelligence.  
_All prompts and architectural choices are designed for zero-latency, high-availability guerrilla installations._
