# Grass Quest

An offline photo scavenger hunt. A local Gemma model gives you a mission to do outside ("three different shades of green in one frame"), you go find it, and the same model looks at your photo and decides if it counts.

Runs an open-weight Gemma model through [Ollama](https://ollama.com). No API keys, no cloud, your photos never leave your machine.

## Run it

```bash
# 1. Install Ollama from https://ollama.com, then:
ollama pull gemma3:4b

# 2. Install and start the app
pip install -r requirements.txt
python app.py
```

Open the local URL Gradio prints. To use it from your phone, start it with `SHARE=1 python app.py` and open the `gradio.live` link Gradio prints (this tunnels through Gradio's servers while it's running).

Use a bigger model with `MODEL=gemma3:12b python app.py` (needs more VRAM), or point at another Ollama host with `OLLAMA_URL`.

## Limits

The judge is a 4B vision model. It's good at colours, objects and scenes, and it can be fooled or be too strict on fiddly missions. Treat its verdict as a referee's call, not ground truth.

## License

MIT
