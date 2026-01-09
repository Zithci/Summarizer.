from fastapi import FastAPI
from pydantic import BaseModel
import os, requests
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

class SummarizeRequest(BaseModel):
    content: str
    title: str = None
    category: str = "General"

    
# JANGAN pake load_dotenv() di Vercel
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ambil langsung dari Env Vercel
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Tambahkan route "/" biar Vercel gak bingung pas lo akses URL utama
@app.get("/")
async def root():
    return {"status": "Backend Live"}

@app.post("/summarize")
async def handle_summarize(req: SummarizeRequest):
    prompt = f"""
    Analyze this text for a Web3/Wisdom library.
    1. TITLE: Catchy and descriptive (max 5 words).
    2. SUMMARY: Clear bullet points.
    
    Text: {req.content}
    
    Format:
    TITLE: [title]
    SUMMARY: [summary]
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    res_text = response.choices[0].message.content
    
    try:
        gpt_title = res_text.split("TITLE:")[1].split("SUMMARY:")[0].strip()
        summary = res_text.split("SUMMARY:")[1].strip()
    except:
        gpt_title = "New Entry"
        summary = res_text

    final_title = req.title if req.title and req.title.strip() else gpt_title
    date_iso = datetime.now().strftime("%Y-%m-%d")

    headers = {
        "Authorization": f"Bearer {os.getenv('NOTION_TOKEN')}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    data = {
        "parent": {"database_id": os.getenv("DATABASE_ID")},
        "properties": {
            "Name": {"title": [{"text": {"content": final_title}}]},
            "Category": {"select": {"name": req.category}},
            "Date": {"date": {"start": date_iso}}
        },
        "children": [
            {
                "object": "block", 
                "type": "heading_3", 
                "heading_3": {"rich_text": [{"text": {"content": "Key Summary"}}]}},
            {
                "object": "block", 
                "type": "paragraph", 
                "paragraph": {"rich_text": [{"text": {"content": summary}}]}}
        ]
    }
    
    res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
    return {"status": "success", "notion_res": res.json()}

