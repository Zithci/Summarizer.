from fastapi import FastAPI
from pydantic import BaseModel
import os, requests
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SummarizeRequest(BaseModel):
    content: str
    title: str = None
    category: str = "Web3"

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Summarizer</title>
        <style>
            body { font-family: -apple-system, sans-serif; padding: 20px; background: #000; color: #fff; display: flex; flex-direction: column; align-items: center; }
            .container { width: 100%; max-width: 500px; }
            h3 { text-align: center; color: #0070f3; }
            textarea, input, select { width: 100%; margin-bottom: 15px; padding: 12px; border-radius: 8px; border: 1px solid #333; background: #111; color: #fff; box-sizing: border-box; font-size: 16px; }
            button { width: 100%; padding: 16px; background: #0070f3; color: #fff; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 16px; }
            button:disabled { background: #333; cursor: not-allowed; }
            #status { margin-top: 20px; text-align: center; font-size: 0.9em; color: #888; }
        </style>
    </head>
    <body>
        <div class="container">
            <h3>Web3 Summarizer</h3>
            <input type="text" id="title" placeholder="Title (Optional)">
            
            <label style="display:block; margin-bottom:5px; font-size:0.8em; color:#888;">Category:</label>
            <select id="category">
                <option value="Web3">Web3</option>
                <option value="Wisdom">Wisdom</option>
            </select>

            <textarea id="content" rows="10" placeholder="Paste content here..."></textarea>
            <button id="btn" onclick="send()">Send to Notion</button>
            <div id="status"></div>
        </div>

        <script>
            async function send() {
                const btn = document.getElementById('btn');
                const status = document.getElementById('status');
                const content = document.getElementById('content').value;
                const category = document.getElementById('category').value;
                
                if(!content) { alert("Paste content first!"); return; }
                
                btn.disabled = true;
                status.innerText = "⏳ Processing...";

                try {
                    const res = await fetch('/summarize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            content: content,
                            title: document.getElementById('title').value,
                            category: category
                        })
                    });
                    const data = await res.json();
                    if (data.status === "success") {
                        status.innerText = "✅ Success! Added to Notion.";
                        document.getElementById('content').value = "";
                        document.getElementById('title').value = "";
                    } else {
                        status.innerText = "❌ Error: " + (data.notion_res?.message || "Failed");
                    }
                } catch (e) {
                    status.innerText = "❌ Connection failed.";
                } finally {
                    btn.disabled = false;
                }
            }
        </script>
    </body>
    </html>
    """

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