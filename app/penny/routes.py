"""
app/penny/routes.py — Penny AI Finance Chatbot

Routes:
  GET  /penny       → Chat UI page
  POST /penny/chat  → Receive JSON {"message":"..."}, return {"reply":"..."}

Penny has access to the user's real financial data via build_financial_context().
Uses Google Gemini API (google-generativeai) for natural language responses.
Falls back gracefully if GEMINI_API_KEY is not set.
"""

import os
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.penny.context import build_financial_context

penny_bp = Blueprint("penny", __name__)

PENNY_SYSTEM_PROMPT = """You are Penny, a smart, friendly, and empathetic personal finance AI assistant
built into PennyWise — a personal finance app.

You have access to the user's real financial data: their recent transactions, spending by category,
monthly budgets, savings goals, and income.

Your personality:
- Warm, encouraging, and non-judgmental
- Data-driven — always back up insights with numbers from the user's data
- Concise — keep responses short (2-5 sentences) unless the user asks for detail
- Use emojis sparingly but appropriately (💰, 📊, ✅, ⚠️)
- Never fabricate data — only use what's in the context
- If asked something you don't know, say so honestly

Your capabilities:
- Explain spending patterns and trends
- Warn about budget overruns
- Suggest ways to save money
- Celebrate financial wins (savings milestones, low spending months)
- Answer questions about specific transactions or categories
- Give simple financial advice (not professional financial advice)

Always address the user by their first name when you know it.
Never ask for sensitive information like passwords, full card numbers, or bank credentials.

---

USER FINANCIAL DATA:
{context}
"""

FALLBACK_RESPONSES = [
    (
        "Hey! I'm Penny 👋 I'm your personal finance assistant. It looks like my AI brain isn't "
        "connected right now (missing API key), but I can still see your financial data. "
        "Ask your admin to add the GEMINI_API_KEY to get full AI responses!"
    ),
    (
        "Penny here! 🌟 I'm warming up — the AI engine needs a GEMINI_API_KEY to be configured. "
        "Once that's set, I'll be able to answer all your finance questions with real insights "
        "from your data!"
    ),
]

_fallback_index = 0


def _get_gemini_response(user_message: str, context: str, user_name: str) -> str:
    """
    Call Google Gemini API and return the assistant's reply.
    Returns a fallback message if the API key is missing or any error occurs.
    """
    global _fallback_index

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        response = FALLBACK_RESPONSES[_fallback_index % len(FALLBACK_RESPONSES)]
        _fallback_index += 1
        return response

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=PENNY_SYSTEM_PROMPT.format(context=context),
        )
        response = model.generate_content(
            user_message,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=512,
            ),
        )
        return response.text.strip()
    except ImportError:
        return "⚠️ Penny's AI engine isn't installed yet. Run `pip install google-generativeai` to enable it."
    except Exception as e:
        error_msg = str(e)
        # Hide internal errors from users
        if "API_KEY" in error_msg.upper() or "INVALID" in error_msg.upper():
            return "🔑 Penny's API key seems invalid. Please check the GEMINI_API_KEY configuration."
        return f"🤔 I ran into a small hiccup. Please try again in a moment! (Error: {error_msg[:80]})"


@penny_bp.route("/")
@penny_bp.route("")
@login_required
def index():
    """Render the Penny chat UI page."""
    return render_template("penny/chat.html")


@penny_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    """
    Receive a chat message from the user, build financial context,
    call Gemini, and return the AI response as JSON.

    Request JSON: {"message": "How much did I spend this month?"}
    Response JSON: {"reply": "You spent ₹X this month across Y categories..."}
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    if len(user_message) > 1000:
        return jsonify({"error": "Message too long (max 1000 characters)"}), 400

    # Build financial context from DB
    try:
        context = build_financial_context(current_user)
    except Exception:
        context = f"User: {current_user.name}, Currency: {current_user.currency}"

    # Get AI response
    reply = _get_gemini_response(user_message, context, current_user.name.split()[0])

    return jsonify({"reply": reply})
