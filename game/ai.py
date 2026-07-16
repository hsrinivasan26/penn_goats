#Prisha Roy
import argparse
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# prompt + parsing / quiz helpers from the mcq module
from game.mcq import build_prompt, parse_bank, Quiz, verdict_message

# load environment variables from .env file
load_dotenv()

# --- Pick the topic at runtime ----------------------------------------------
# Category CODE -> the full category name the generator expects as its "scope".
CATEGORIES = {
    "INC": "INCOME",
    "INV": "INVESTING",
    "TAX": "TAXES",
    "DEBT": "DEBT & CREDIT",
    "BUD": "BUDGETING & CASH FLOW",
    "NW": "NET WORTH & GOALS",
    "WELL": "WELLBEING & BEHAVIOR",
    "RISK": "RISK & LIFE EVENTS",
}

parser = argparse.ArgumentParser(description="PENN GOATS financial-literacy quiz.")
parser.add_argument(
    "-c", "--category", default="ALL",
    help="Topic to quiz on: " + ", ".join(CATEGORIES) + ", or ALL for every category. "
         "Default: ALL (every category).",
)
parser.add_argument(
    "-n", "--count", type=int, default=5,
    help="Questions per subtopic (default: 5).",
)
args = parser.parse_args()

# Resolve the chosen category to a scope the generator understands.
cat = args.category.strip().upper()
if cat == "ALL":
    scope = None                       # every category (bigger/slower; may truncate)
elif cat in CATEGORIES:
    scope = CATEGORIES[cat]            # a code like INV -> "INVESTING"
elif cat in CATEGORIES.values():
    scope = cat                        # a full name like "INVESTING"
else:
    options = ", ".join(list(CATEGORIES) + ["ALL"])
    print(f"Unknown category '{args.category}'. Choose one of: {options}")
    raise SystemExit(2)

# --- configure the client for the Gemini API --------------------------------
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment variables. Please set it in the .env file.")
    raise SystemExit(1)
client = genai.Client(api_key=api_key)

# --- Generate the question bank ---------------------------------------------
print(f"Generating {scope or 'ALL categories'} questions")
prompt = build_prompt(scope=scope, questions_per_subtopic=args.count)

try:
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    bank = parse_bank(response.text)   # rejects any question that doesn't have 4-6 options
except Exception as e:
    print(f"Could not generate questions, go home for today: {e}")
    raise SystemExit(1)

# --- Run the quiz, easy -> medium -> hard -----------------------------------
quiz = Quiz(bank, sort_by_difficulty=True)
print("=" * 50)
print(f"LET'S GET TO WORK!  {quiz.total} questions, easy to hard. Type 'quit' to stop early.")
print("=" * 50)

while not quiz.finished:
    q = quiz.current_prompt()
    choices = [opt["id"] for opt in q["options"]]      # this question's real 4-6 letters

    print(f"\nQ{q['number']}/{q['total']}  [{q['category']} - {q['difficulty']}]")
    print(q["stem"])
    for opt in q["options"]:
        print(f"  {opt['id']}) {opt['text']}")

    # keep asking until we get one of THIS question's letters (or 'quit')
    while True:
        choice = input(f"Your answer ({'/'.join(choices)}), or 'quit': ").strip().upper()
        if choice == "QUIT" or choice in choices:
            break
        print(f"  Invalid - type one of: {', '.join(choices)}")

    if choice == "QUIT":
        print("Have a great day! Keep putting in the work!")
        break

    # local grading, no extra API call
    result = quiz.submit_answer(choice)
    if result["correct"]:
        print("  Correct!")
    else:
        print(f"  Not quite - the correct answer was {result['correct_option_id']}.")
    print(f"  {result['explanation']}")

# --- Final score, printed once ----------------------------------------------
summary = quiz.results()
print("\n" + "=" * 50)
print(f"Final score: {summary['score']}/{summary['total']} ({summary['percent']}%)")
print(verdict_message(summary["percent"]))
print("=" * 50)
