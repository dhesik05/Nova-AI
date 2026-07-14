"""
Suggest route — returns a random set of dynamic starter prompts.
Used by the welcome screen to show fresh suggestions on every visit.
"""
import random
from fastapi import APIRouter

router = APIRouter(prefix="/api/suggest", tags=["suggest"])

# A curated pool of contextually diverse starter prompts
_PROMPT_POOL = [
    # Coding
    {"icon": "🐍", "title": "Python script",         "desc": "Generate production-ready code",              "prompt": "Write a Python script that reads a CSV file and computes descriptive statistics for each column."},
    {"icon": "🔧", "title": "Debug my code",          "desc": "Spot the bug and explain the fix",            "prompt": "Help me debug this code and explain what's wrong:"},
    {"icon": "🌐", "title": "REST API design",        "desc": "Best practices and example schema",           "prompt": "Design a RESTful API for a task management app with users, projects, and tasks."},
    {"icon": "⚡", "title": "Optimize performance",   "desc": "Find bottlenecks and suggest improvements",   "prompt": "What are the most effective techniques to optimize a slow Python web application?"},
    {"icon": "🧪", "title": "Write unit tests",       "desc": "TDD approach with pytest examples",           "prompt": "Show me how to write comprehensive unit tests for a Python function using pytest."},
    {"icon": "🏗️", "title": "System design",         "desc": "Architecture for scalable systems",           "prompt": "Walk me through designing a scalable URL shortener service from scratch."},
    # Science & Learning
    {"icon": "⚛️", "title": "Quantum computing",     "desc": "Clear, jargon-free explanation",              "prompt": "Explain quantum computing in simple terms with a practical analogy."},
    {"icon": "🧬", "title": "Explain DNA",            "desc": "From genes to proteins",                      "prompt": "Explain how DNA encodes proteins and why mutations matter."},
    {"icon": "🌌", "title": "Black holes",            "desc": "Physics without the equations",               "prompt": "How do black holes form and what happens at the event horizon?"},
    {"icon": "📐", "title": "Linear algebra",         "desc": "Core concepts with visuals",                  "prompt": "Explain eigenvalues and eigenvectors with a real-world example."},
    # Writing & Creativity
    {"icon": "✍️", "title": "Write an essay",        "desc": "Structured argument with clear prose",        "prompt": "Write a compelling 500-word essay on why critical thinking is the most important skill in the AI era."},
    {"icon": "📧", "title": "Professional email",     "desc": "Polished, concise and effective",             "prompt": "Write a professional email requesting a project extension due to unexpected technical challenges."},
    {"icon": "🎨", "title": "Creative story",         "desc": "Vivid characters and narrative",              "prompt": "Write the opening chapter of a sci-fi thriller where an AI achieves consciousness."},
    {"icon": "📝", "title": "Summarise text",         "desc": "Extract key points concisely",                "prompt": "Summarise the following text into 5 bullet points:"},
    # Career & Productivity
    {"icon": "💼", "title": "Interview prep",         "desc": "Mock questions + ideal answers",              "prompt": "Give me 10 behavioural interview questions for a senior software engineer role with ideal STAR-format answers."},
    {"icon": "🚀", "title": "Startup ideas",          "desc": "Validate and evaluate concepts",              "prompt": "Generate 5 viable AI startup ideas for 2025 with a brief market analysis for each."},
    {"icon": "📊", "title": "Data analysis plan",     "desc": "Step-by-step analytical approach",            "prompt": "Walk me through a data analysis plan for understanding customer churn in a SaaS product."},
    {"icon": "🤝", "title": "Negotiation tactics",    "desc": "Evidence-based persuasion strategies",        "prompt": "What are the most effective salary negotiation strategies backed by psychology research?"},
    # Tech & AI
    {"icon": "🤖", "title": "Explain transformers",  "desc": "Attention mechanism made simple",             "prompt": "Explain how the transformer architecture and self-attention work in plain language."},
    {"icon": "🔌", "title": "REST vs GraphQL",        "desc": "Compare API design approaches",               "prompt": "Summarise the key differences between REST and GraphQL with pros and cons for each."},
    {"icon": "🛡️", "title": "Security hardening",   "desc": "OWASP top 10 and beyond",                     "prompt": "What are the most critical security measures for a new web application in 2025?"},
    {"icon": "☁️", "title": "Cloud architecture",    "desc": "AWS / Azure / GCP patterns",                  "prompt": "Compare serverless, containers, and VMs — when should I use each on AWS?"},
]


@router.get("/prompts")
def get_prompts(count: int = 4):
    """Return *count* random starter prompts (max 8)."""
    count = min(max(count, 1), 8)
    chosen = random.sample(_PROMPT_POOL, min(count, len(_PROMPT_POOL)))
    return {"prompts": chosen}
