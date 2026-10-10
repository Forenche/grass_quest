"""
Grass Quest: an offline photo scavenger hunt.
A local Gemma model hands you a mission to do outside, then looks at your photo and judges it.
"""
import base64
import io
import json
import os
import random
import urllib.error
import urllib.request

import gradio as gr

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("MODEL", "gemma3:4b")

THEMES = [
    "colours", "textures", "shapes", "nature", "street life", "light and shadow",
    "something old", "something tiny", "patterns", "the sky", "animals", "water",
]

MISSION_PROMPT = """You create one short outdoor photo mission for a scavenger hunt.
Theme: {theme}. Difficulty: {difficulty}.
Rules: it must be doable on an ordinary walk in a city or park, safe, legal,
and must not involve photographing strangers' faces or private property.
Make it specific enough that a photo can prove it, like "a leaf with a hole in it"
or "three different shades of green in one frame".
Respond ONLY with JSON: {{"mission": "...", "hint": "one short tip on where to look"}}"""

JUDGE_PROMPT = """You are the judge of an outdoor photo scavenger hunt.
The mission was: "{mission}"
Look at the photo. Decide honestly whether it completes the mission.
Be fair but not a pushover: a blurry guess or a photo of a screen does not count.
Respond ONLY with JSON:
{{"passed": true or false, "what_i_see": "one sentence describing the photo",
"verdict": "one short, playful sentence explaining the call"}}"""

OLLAMA_DOWN = f"Can't reach Ollama at {OLLAMA_URL}. Run `ollama serve` and `ollama pull {MODEL}`."


def call_ollama(prompt: str, image_b64: str | None = None, temperature: float = 0.2) -> dict:
    message = {"role": "user", "content": prompt}
    if image_b64:
        message["images"] = [image_b64]
    payload = {
        "model": MODEL,
        "stream": False,
        "format": "json",
        "options": {"temperature": temperature},
        "messages": [message],
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.load(resp)
    return json.loads(body["message"]["content"])


def image_to_b64(img) -> str:
    img = img.convert("RGB")
    img.thumbnail((1024, 1024))  # phone photos are huge; smaller = faster judging
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def score_md(score: dict) -> str:
    return f"**Missions completed:** {score['done']} / {score['tried']} attempts"


def new_mission(difficulty: str):
    theme = random.choice(THEMES)
    try:
        m = call_ollama(MISSION_PROMPT.format(theme=theme, difficulty=difficulty), temperature=0.9)
        mission = str(m.get("mission", "")).strip()
        if not mission:
            raise KeyError("mission")
    except urllib.error.URLError:
        return "", OLLAMA_DOWN, None
    except (json.JSONDecodeError, KeyError, AttributeError):
        return "", "The model fumbled the mission. Press the button again.", None
    md = (
        f"## 🎯 {mission}\n\n**Hint:** {m.get('hint', '')}\n\n"
        "Put the phone away, go find it, come back with one photo."
    )
    return mission, md, None


def judge(mission: str, img, score: dict):
    if not mission:
        return "Get a mission first.", score, score_md(score)
    if img is None:
        return "Upload or take a photo first.", score, score_md(score)
    try:
        r = call_ollama(JUDGE_PROMPT.format(mission=mission), image_b64=image_to_b64(img))
    except urllib.error.URLError:
        return OLLAMA_DOWN, score, score_md(score)
    except (json.JSONDecodeError, KeyError, AttributeError):
        return "The judge got confused. Submit again.", score, score_md(score)
    passed = r.get("passed") is True or str(r.get("passed")).lower() == "true"
    score = {"done": score["done"] + int(passed), "tried": score["tried"] + 1}
    head = "## ✅ Mission complete" if passed else "## ❌ Not quite"
    md = f"{head}\n\n**What I see:** {r.get('what_i_see', '')}\n\n{r.get('verdict', '')}"
    if not passed:
        md += "\n\nGo back out and try again."
    return md, score, score_md(score)


with gr.Blocks(title="Side Quest") as demo:
    gr.Markdown("# Grass Quest\nAn offline photo scavenger hunt. Get a mission, go outside, prove it with one photo.")
    mission_state = gr.State("")
    score_state = gr.State({"done": 0, "tried": 0})

    with gr.Row():
        difficulty = gr.Radio(["easy", "medium", "hard"], value="easy", label="Difficulty")
        mission_btn = gr.Button("Give me a mission", variant="primary")
    mission_md = gr.Markdown()
    photo = gr.Image(type="pil", label="Your proof (upload or use the camera)")
    judge_btn = gr.Button("Judge my photo", variant="primary")
    verdict_md = gr.Markdown()
    score_view = gr.Markdown(score_md({"done": 0, "tried": 0}))

    mission_btn.click(new_mission, inputs=[difficulty], outputs=[mission_state, mission_md, photo])
    judge_btn.click(judge, inputs=[mission_state, photo, score_state], outputs=[verdict_md, score_state, score_view])

if __name__ == "__main__":
    demo.launch(share=os.getenv("SHARE") == "1")
