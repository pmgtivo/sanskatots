# Running Open-Source AI Models Locally — A Complete Guide

> **Target machine for this guide:** MacBook Pro, Apple **M4 Pro**, **24 GB unified memory**, macOS 26.x.
> Most instructions also apply to other Apple Silicon Macs (M1–M4) and, where noted, to Windows / Linux with NVIDIA GPUs.

---

## 0. Important clarification: "OpenAI" vs "open AI models"

| Term | What it means | Can you run it locally? |
|---|---|---|
| **OpenAI** (the company) | Makers of ChatGPT, GPT-4o, GPT-5, o3, DALL·E | **No.** Their flagship models are **closed-weight**, API-only. |
| **Open-source / open-weight models** | Llama (Meta), Qwen (Alibaba), Mistral, Gemma (Google), Phi (Microsoft), DeepSeek, etc. | **Yes.** Weights are downloadable. This guide is about these. |
| **OpenAI-compatible API** | A *protocol* (the `/v1/chat/completions` HTTP shape). Many local runners expose this so existing tools "just work". | The protocol is local; only the shape matches OpenAI. |

The rest of this document uses **"local LLM"** to mean an open-weight model running on your own machine.

---

## 1. TL;DR — what to do on your M4 Pro / 24 GB

1. **Install [Ollama](https://ollama.com)** (one-click, CLI + background server).
2. Pull a model:
	```bash
	ollama pull llama3.1:8b           # great general default
	ollama pull qwen2.5-coder:14b     # best local coding model that fits 24 GB
	ollama pull gemma3:12b            # strong multilingual incl. Hindi
	```
3. Chat in terminal:
	```bash
	ollama run llama3.1:8b
	```
4. (Optional) Install **LM Studio** for a polished GUI, or **MLX** for the absolute fastest speed on Apple Silicon.
5. Connect to **VS Code** via the **Continue** or **Cline** extension, pointing it at `http://localhost:11434` (Ollama's OpenAI-compatible endpoint).

Everything else in this guide is *why* and *how to pick*.

---

## 2. How local LLMs actually work (60-second mental model)

A model is a big file of **weights** (numbers). A **runner** loads those weights into RAM/VRAM and runs matrix multiplications on every token you type or generate.

Two things dominate whether a model is usable on your laptop:

| Factor | What it controls | Your M4 Pro / 24 GB reality |
|---|---|---|
| **Model size** (params: 7B, 13B, 70B…) | Quality ceiling | 7B–14B comfortable, 20B–32B possible with aggressive quantization, 70B impractical |
| **Quantization** (Q4, Q5, Q8, fp16) | File size + RAM use + small quality loss | Q4_K_M is the sweet spot |

**Rule of thumb for RAM usage:**

`RAM needed ≈ (params in billions) × (bits per weight / 8) + ~1–3 GB overhead + context buffer`

Examples (Q4_K_M ≈ 4.5 bits/weight):

| Model | Approx RAM | Fits in 24 GB? |
|---|---|---|
| 7B Q4 | ~5 GB | ✅ Easy |
| 8B Q4 | ~6 GB | ✅ Easy |
| 13–14B Q4 | ~9–10 GB | ✅ Comfortable |
| 22B Q4 | ~14 GB | ✅ Tight but workable |
| 27B Q4 | ~17 GB | ✅ Works, leaves little for OS |
| 32B Q4 | ~20 GB | ⚠️ Marginal, close other apps |
| 70B Q4 | ~42 GB | ❌ Won't fit |
| 70B Q2 | ~26 GB | ❌ Still over |

Apple Silicon has **unified memory** — the GPU shares the same 24 GB as the CPU. There's no separate VRAM; whatever the model takes is unavailable to macOS.

---

## 3. Pick your runner

There are five serious options. Pick **one** for daily use; you can install more later.

### 3.1 Comparison table

| Runner | Best for | UI | Speed on M-series | Model formats | OpenAI-compatible API | Hard to install? |
|---|---|---|---|---|---|---|
| **Ollama** | Default daily driver, dev workflows | CLI + minimal | Very good (Metal) | GGUF (its own registry) | ✅ `:11434` | One-click |
| **LM Studio** | Non-developers, browsing models, fast experiments | Polished GUI | Very good (Metal/MLX) | GGUF, MLX | ✅ Local server tab | One-click |
| **llama.cpp** | Maximum control, scripting, embedding into apps | None (CLI / C++) | Very good (Metal) | GGUF | ✅ `llama-server` | Moderate (Homebrew) |
| **MLX / mlx-lm** | **Fastest** on Apple Silicon, research | Python CLI | **Best** | MLX (Apple's own) | ✅ via `mlx_lm.server` | Moderate (Python) |
| **vLLM / TGI / Ray Serve** | Production serving, multi-GPU rigs | None | N/A on Mac (CUDA-only realistically) | HF safetensors | ✅ | Hard, Linux+NVIDIA |

### 3.2 Recommendation matrix

| You are… | Use |
|---|---|
| Just starting, want it to "work" | **Ollama** |
| Want a pretty GUI like ChatGPT, hate terminals | **LM Studio** |
| Want squeezing every last token/sec on Apple Silicon | **MLX** |
| Building a product / need scripting | **llama.cpp** server or **Ollama** API |
| Have a Linux box with an NVIDIA 3090/4090 | **vLLM** |

---

## 4. Install & run — Ollama (recommended default)

### 4.1 Install

```bash
# macOS (Homebrew)
brew install ollama

# or download .dmg from https://ollama.com/download
```

Start the background service (one-time):

```bash
brew services start ollama
# or just open the Ollama app once
```

Verify:

```bash
ollama --version
curl http://localhost:11434/api/tags
```

### 4.2 Pull and run your first model

```bash
ollama pull llama3.1:8b
ollama run llama3.1:8b
# >>> Hello! What can you do?
```

Useful commands:

```bash
ollama list                  # what's installed
ollama ps                    # what's loaded in RAM right now
ollama rm <model>            # delete to free disk
ollama show llama3.1:8b      # context length, params, license
```

### 4.3 Use the API (OpenAI-compatible)

Ollama exposes an OpenAI-shaped endpoint at `http://localhost:11434/v1`. Example with `curl`:

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
	"model": "llama3.1:8b",
	"messages": [{"role": "user", "content": "Write a tagline for SanskaTots."}]
  }'
```

Or with the official Python SDK (works because it's OpenAI-compatible):

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")  # key is ignored
print(client.chat.completions.create(
	model="llama3.1:8b",
	messages=[{"role": "user", "content": "Hi"}]
).choices[0].message.content)
```

### 4.4 Tuning context length and quantization

```bash
# Pull a specific quantization
ollama pull llama3.1:8b-instruct-q5_K_M

# Run with a larger context window (uses more RAM!)
OLLAMA_CONTEXT_LENGTH=16384 ollama run llama3.1:8b
```

---

## 5. Install & run — LM Studio (GUI alternative)

1. Download from <https://lmstudio.ai>.
2. Open it → **Discover** tab → search e.g. `llama-3.1-8b-instruct` → pick a GGUF (Q4_K_M is fine) → **Download**.
3. Go to **Chat** tab → load the model → talk to it.
4. Go to **Developer / Local Server** tab → **Start Server** → it exposes `http://localhost:1234/v1` (OpenAI-compatible).

LM Studio's strengths: model browser, side-by-side comparison, easy quant switching, MLX support toggle.

---

## 6. Install & run — MLX (fastest on Apple Silicon)

MLX is Apple's own ML framework. Models converted to MLX format run noticeably faster (often 1.3–2× tok/sec vs GGUF) and use slightly less memory.

```bash
# Use a dedicated Python (uv is fast; pipx or venv work too)
brew install uv
uv tool install mlx-lm

# Run any MLX model from Hugging Face
mlx_lm.generate \
  --model mlx-community/Llama-3.1-8B-Instruct-4bit \
  --prompt "Explain Sanskrit shlokas to a 5-year-old."

# Start an OpenAI-compatible server
mlx_lm.server --model mlx-community/Qwen2.5-14B-Instruct-4bit --port 8080
```

Find MLX-converted models at <https://huggingface.co/mlx-community>.

---

## 7. The models — what to download in 2026

All sizes/RAM below assume **Q4_K_M GGUF** unless noted. Pick based on your use case (Section 8).

### 7.1 General-purpose chat & reasoning

| Model | Sizes (good for 24 GB) | Strengths | Weaknesses | License |
|---|---|---|---|---|
| **Llama 3.3** / **Llama 3.1** (Meta) | 8B | Best-rounded default, huge ecosystem, 128k context | 70B doesn't fit | Llama Community (commercial OK with <700M MAU) |
| **Qwen 2.5** (Alibaba) | 7B, 14B, 32B | Top-tier reasoning at every size, great at code & math, multilingual incl. Hindi | Some refusals on edge prompts | Apache 2.0 (most sizes) |
| **Mistral Small 3** / **Nemo** | 12B, 22B | Fast, excellent instruction following, strong European languages | Slightly weaker at math vs Qwen | Apache 2.0 |
| **Gemma 3** (Google) | 4B, 12B, 27B | Excellent multilingual (140+ langs), strong long-context, vision-enabled at 12B+ | Verbose by default | Gemma terms (commercial OK) |
| **Phi-4** (Microsoft) | 14B | Punches way above weight on reasoning/STEM | Smaller world knowledge | MIT |
| **DeepSeek-R1-Distill** | 7B, 14B, 32B | Open-weight reasoning model, shows chain-of-thought | Verbose, slower | MIT |

### 7.2 Coding specialists

| Model | Best size for 24 GB | Notes |
|---|---|---|
| **Qwen 2.5 Coder** | **14B** | Currently the best local coding model that fits; rivals GPT-4o-mini on many tasks |
| **DeepSeek Coder V2 Lite** | 16B (MoE, ~2.4B active) | Very fast, good for autocomplete |
| **Codestral** (Mistral) | 22B | Excellent code completion, non-commercial license — read carefully |
| **StarCoder2** | 15B | Permissive, weaker than Qwen Coder for chat-style help |

### 7.3 Vision (image + text in)

| Model | Size | Notes |
|---|---|---|
| **Llama 3.2 Vision** | 11B | Solid general image understanding |
| **Qwen 2.5 VL** | 7B | Strong OCR, charts, UI screenshots |
| **Gemma 3** | 12B / 27B | Native multimodal, very good |
| **MiniCPM-V 2.6** | 8B | Punchy small VLM, great for receipts/docs |

In Ollama: `ollama pull llama3.2-vision:11b` then pass an image via the API's `images` field.

### 7.4 Embeddings (for RAG / search)

| Model | Notes |
|---|---|
| **nomic-embed-text** | Default — fast, 768-dim, English |
| **bge-m3** | Multilingual (incl. Hindi), 1024-dim, also does sparse + ColBERT |
| **mxbai-embed-large** | Top-quality English, 1024-dim |

`ollama pull nomic-embed-text` then call `/api/embeddings`.

### 7.5 Speech / Audio (not LLMs but commonly co-deployed)

| Model | Use | Tool |
|---|---|---|
| **Whisper** (OpenAI, open weights) | Speech-to-text | `whisper.cpp`, `mlx-whisper` |
| **Parakeet** (NVIDIA) | Faster English STT | `nemo` |
| **Kokoro**, **Piper** | Text-to-speech, runs on CPU | standalone |

### 7.6 Image generation (different stack)

Not LLMs but often asked about: **Stable Diffusion XL**, **FLUX.1 [dev]**, **SD 3.5** via **ComfyUI** or **DrawThings** (DrawThings is the easiest on Mac).

---

## 8. Use-case → model cheat sheet

| Your task | First pick | Why |
|---|---|---|
| General Q&A, brainstorming | **Llama 3.1 8B** | Best default, fast, low RAM |
| Writing long marketing copy (English) | **Mistral Small 3 22B** or **Qwen 2.5 14B** | Better long-form coherence |
| **Hindi / Indic content** (relevant to SanskaTots reels) | **Gemma 3 12B** or **Qwen 2.5 14B** | Strongest non-English on local models |
| Coding / VS Code copilot replacement | **Qwen 2.5 Coder 14B** | Best local coder that fits 24 GB |
| Math / logical reasoning | **DeepSeek-R1-Distill 14B** or **Phi-4 14B** | Reasoning-tuned |
| Summarising long PDFs / RAG over documents | **Llama 3.1 8B** (128k ctx) + **bge-m3** embeddings | Long context + multilingual retrieval |
| Reading screenshots / scanned forms | **Qwen 2.5 VL 7B** | Best small VLM for OCR |
| Real-time tool / function calling | **Llama 3.1 8B** or **Qwen 2.5 7B** | Both natively support tool calls |
| Roleplay / creative fiction | **Mistral Nemo 12B** | Looser, more creative |
| You only have ~8 GB free | **Phi-4-mini 3.8B** or **Gemma 3 4B** | Acceptable quality, tiny RAM |

---

## 9. Quantization — what those `Q4_K_M` labels actually mean

| Quant | Bits/weight | Quality loss | Use when |
|---|---|---|---|
| **fp16** / **bf16** | 16 | None (baseline) | You have lots of VRAM (you don't, on 24 GB for big models) |
| **Q8_0** | 8 | Negligible | You want highest quality and the model still fits |
| **Q6_K** | ~6.5 | Very small | Slight upgrade over Q5 |
| **Q5_K_M** | ~5.5 | Small | Good balance if RAM allows |
| **Q4_K_M** | ~4.5 | Small–moderate, **the sweet spot** | **Default choice** |
| **Q3_K_M** | ~3.5 | Noticeable | Squeezing a larger model into limited RAM |
| **Q2_K** | ~2.6 | Significant | Last resort, often worse than a smaller Q4 model |

**Rule:** A 14B at Q4 almost always beats a 7B at Q8. **Pick the biggest model that fits, then drop quant to make it fit.**

---

## 10. Context length and the KV cache

Context (the "memory" of the conversation) is **not free**. Every token in the context takes extra RAM in something called the **KV cache**.

Approximate KV-cache cost per 1k tokens:

| Model size | ~RAM per 1k tokens of context |
|---|---|
| 7–8B | ~130 MB |
| 13–14B | ~200 MB |
| 27–32B | ~400 MB |

So a Llama 3.1 8B Q4 (~6 GB weights) at **32k context** can need **6 GB + ~4 GB KV ≈ 10 GB**. Push to 128k and you're at ~22 GB.

Most runners default to a **safe small context (4k–8k)**. Raise it explicitly when you need it:

```bash
# Ollama
OLLAMA_CONTEXT_LENGTH=32768 ollama run llama3.1:8b
```

---

## 11. Wire it into VS Code

Two great extensions, both free:

### 11.1 Continue (`continue.dev`)

1. Install **Continue** from the VS Code marketplace.
2. Open its `config.yaml` and add:
	```yaml
	models:
	  - name: Llama 3.1 8B (local)
		 provider: ollama
		 model: llama3.1:8b
	  - name: Qwen Coder 14B (local)
		 provider: ollama
		 model: qwen2.5-coder:14b
		 roles: [autocomplete, chat]
	```
3. Use `Cmd+L` for chat, `Cmd+I` for inline edit, `Tab` for autocomplete.

### 11.2 Cline (autonomous agent)

1. Install **Cline** from the marketplace.
2. Settings → API Provider: **Ollama** → base URL `http://localhost:11434` → pick model.
3. Cline can read/write files and run terminal commands locally — works great with `qwen2.5-coder:14b`.

### 11.3 GitHub Copilot Chat (BYO model — experimental)

Recent Copilot Chat versions let you add a custom OpenAI-compatible endpoint. Point it at `http://localhost:11434/v1` and pick your installed Ollama model. (Feature availability changes; check Copilot settings.)

---

## 12. Licenses — what you can ship commercially

| Model family | License | Commercial use? |
|---|---|---|
| Llama 3.x | Llama Community License | ✅ if your product has <700M MAU; attribution required |
| Qwen 2.5 (most sizes) | Apache 2.0 | ✅ Yes, no restrictions |
| Mistral *open* weights (Nemo, Small 3) | Apache 2.0 | ✅ Yes |
| Codestral | MNPL (research only) | ❌ Not for commercial without paid license |
| Gemma 3 | Gemma Terms of Use | ✅ Yes, with use-policy restrictions |
| Phi-4 | MIT | ✅ Fully open |
| DeepSeek-R1 (and distills) | MIT | ✅ Fully open |

**Always read the actual model card** before shipping — terms change.

---

## 13. Performance tips for Apple Silicon

1. **Close other heavy apps** (Chrome with 200 tabs, Docker, Xcode simulators) — unified memory matters.
2. **Use MLX builds** when available — 1.3–2× tok/sec over GGUF for the same model.
3. **Prefer Q4_K_M** GGUF; Q5/Q6 give diminishing returns and cost RAM.
4. **Smaller context = faster + less RAM.** Don't ask for 128k if 8k suffices.
5. **Keep one model loaded.** Ollama auto-unloads idle models after 5 min — set `OLLAMA_KEEP_ALIVE=30m` if you switch often.
6. **Disable mmap on very tight RAM** (`OLLAMA_NO_MMAP=1`) — sometimes faster on Apple Silicon.
7. **Speculative decoding** (Ollama 0.5+, llama.cpp): pair a tiny "draft" model with a big one for ~1.5× speedup.
8. **Battery vs plugged in:** macOS throttles GPU on battery. Plug in for benchmarks.

Expected speeds on **M4 Pro / 24 GB** (rough, Q4_K_M, short context):

| Model | tok/sec (generation) |
|---|---|
| 3–4B | 80–120 |
| 7–8B | 45–65 |
| 13–14B | 25–35 |
| 22–27B | 12–20 |
| 32B | 8–12 |

MLX builds: add ~30–60%.

---

## 14. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ollama: command not found` | Service not in PATH | `brew link ollama` or reopen terminal |
| Model loads then macOS freezes / swaps | Model too big for free RAM | Drop quant (Q5→Q4), lower context, close apps |
| Garbled / repeating output | Quant too aggressive (Q2) or wrong chat template | Use Q4+, ensure runner knows the model's template |
| Slow first token, then fast | Cold load from disk | Normal; keep model resident with `OLLAMA_KEEP_ALIVE` |
| `out of memory` mid-generation | KV cache grew with context | Lower `--ctx-size` / `OLLAMA_CONTEXT_LENGTH` |
| Tool/function calls ignored | Model doesn't support them or runner doesn't forward | Use Llama 3.1, Qwen 2.5, or Mistral; check runner docs |
| Hugging Face download stuck | Auth / rate limits | `huggingface-cli login`, retry |

---

## 15. Privacy & security notes

- Models running locally **do not call home** — your prompts stay on your disk and RAM.
- Some runners (LM Studio) send anonymous telemetry; disable in settings if needed.
- Open weights are **not "safe" by default** — they can be jailbroken, hallucinate, and generate harmful content. Add your own guardrails for any user-facing product.
- Treat downloaded weights like any binary: pull from official Hugging Face / Ollama registries, verify SHA256s for production use.

---

## 16. Recommended setup for *this* workspace (SanskaTots)

Given the workspace is full of business strategy, Instagram reels, and Indic-flavoured marketing content, the highest-leverage local stack is:

1. **Ollama** as the daemon.
2. Three models pulled:
	- `llama3.1:8b` — general drafting, structured outputs, fast.
	- `qwen2.5-coder:14b` — coding inside VS Code (Continue / Cline).
	- `gemma3:12b` — Hindi/Indic content for reel scripts and captions.
3. `nomic-embed-text` for any RAG over the `.md` strategy docs.
4. **Continue** extension in VS Code, configured with all three models above.

Disk budget: ~25 GB total. RAM: only one model is hot at a time — easily fits.

Sample one-liner setup:

```bash
brew install ollama && brew services start ollama && \
ollama pull llama3.1:8b && \
ollama pull qwen2.5-coder:14b && \
ollama pull gemma3:12b && \
ollama pull nomic-embed-text
```

---

## 17. Going further

- **RAG over your own files:** [LlamaIndex](https://www.llamaindex.ai) or [LangChain](https://www.langchain.com) → both work with Ollama out of the box.
- **Fine-tuning on your data:** [Apple MLX-LM LoRA](https://github.com/ml-explore/mlx-examples/tree/main/llms), [Unsloth](https://unsloth.ai) (NVIDIA), [Axolotl] (NVIDIA).
- **Agent frameworks:** [CrewAI], [AutoGen], [LangGraph] — all accept an OpenAI-compatible base URL, so point them at Ollama.
- **Benchmark your own machine:** `llama-bench -m <model.gguf>` (from llama.cpp) gives reproducible tok/sec numbers.

---

## 18. One-page summary

```
HARDWARE          M4 Pro, 24 GB unified memory  →  7B–14B easy, 22–27B works
RUNNER            Ollama (default) | LM Studio (GUI) | MLX (fastest)
DEFAULT MODELS    llama3.1:8b · qwen2.5-coder:14b · gemma3:12b · nomic-embed-text
QUANT             Q4_K_M (always start here)
CONTEXT           8k default; raise only when needed
API               http://localhost:11434/v1  (OpenAI-compatible)
VS CODE           Continue or Cline extension, point at Ollama
LICENSE WATCH     Codestral = non-commercial; everything else above = OK
```

That's the whole game. Pick a runner, pull a model, point your tools at `localhost`, and you're running open-weight AI locally with zero data leaving your laptop.
