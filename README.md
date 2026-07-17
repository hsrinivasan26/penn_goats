# Penn Goats

Team PENN GOATS Research and Design project for Glassman Penn Scholars 2026.

**Penn Goats** is a free, browser-based financial-literacy game. You start with your
first real paycheck and get five in-game years to go from broke new hire to a real
savings buffer — learning about take-home pay, taxes, investing, debt, and the
work–life balance that keeps you from burning out along the way.

## Run the demo

The demo is the Streamlit web app. You'll need **Python 3.10 or newer**.

From the project root:

```bash
pip install -r ui/requirements.txt   # install the app's dependencies
streamlit run ui/app.py              # launch the game
```

Streamlit opens the game in your browser (usually at http://localhost:8501).
That's it — click **Start** and play.

Prefer to keep things isolated? Create a virtual environment first with
`python -m venv .venv` and activate it (`source .venv/bin/activate` on macOS/Linux,
`.venv\Scripts\activate` on Windows), then run the two commands above.

## AI features (optional)

Two parts of the game use Google's Gemini model: the **Money quiz**, which generates
fresh questions, and the end-of-run **coach**, which writes you a short debrief. Both
read a `GEMINI_API_KEY` from a `.env` file in the project root:

```
GEMINI_API_KEY=your-key-here
```

Without a key the game still runs perfectly — the quiz falls back to a built-in
question bank and the coach uses written debriefs. Nothing in the core game requires it.

## Play in the terminal

There's also a no-frills terminal version that drives the same game engine:

```bash
python play.py                     # interactive, Path A, seed 0
python play.py --path B --seed 7   # interactive, Path B
python play.py --auto 60           # headless: auto-play and print a summary
```

## Run the tests

```bash
pip install -r requirements.txt    # just pytest
python -m pytest
```

## Where things live

Game rules and balance live in `game/` and `config.py`; the web UI is in `ui/`; the
terminal game is `play.py`; and design notes and specs are in `docs/`.
