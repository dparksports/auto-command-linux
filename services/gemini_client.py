"""Gemini AI client — port of GeminiClient.cs."""
import requests
import config


def analyze_threat(event_description):
    """Send a security event to Gemini for AI analysis."""
    api_key = config.GEMINI_API_KEY
    if not api_key:
        return {"error": "GEMINI_API_KEY not configured"}

    prompt = f"""You are a Linux security analyst. Analyze this security event and provide:
1. Threat level (Low/Medium/High/Critical)
2. What happened
3. Recommended action

Event: {event_description}
"""
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            return {"analysis": text}
        return {"error": f"API error: {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}
