@app.post("/summarize")
async def handle_summarize(req: SummarizeRequest):
    # Prompt harus minta JSON keys yang sesuai sama kode di bawah
    prompt = f"""
    Analyze this text for a Web3/Wisdom library.
    Return ONLY a JSON object with:
    1. "title": Catchy title (max 5 words).
    2. "points": An array of strings (the summary points).
    
    Text: {req.content}
    """
    
    try:    
        # 1. OpenAI Call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"} # Fix typo tanda petik
        )    

        import json
        # response.choices (pake 's')
        res_data = json.loads(response.choices[0].message.content)
        gpt_title = res_data.get("title", "New Entry")
        points = res_data.get("points", [])
        
        final_title = req.title if req.title and req.title.strip() else gpt_title
        date_iso = datetime.now().strftime("%Y-%m-%d")

        # 2. Setup blocks buat Notion
        content_blocks = [
            {
                "object": "block", # Fix: bukan blocks
                "type": "heading_3",
                "heading_3": {"rich_text": [{"text": {"content": "💡 Key Takeaways"}}]}
            }
        ]

        # 3. Loop points
        for p in points: # Pake 'p' biar beda sama 'points'
            content_blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": { # Kasih tanda petik
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": p} # 'content' huruf kecil
                        }
                    ]
                }
            })

        # 4. Send to Notion
        headers = {
            "Authorization": f"Bearer {os.environ.get('NOTION_TOKEN')}", # Tambah spasi setelah Bearer
            "Content-Type": "application/json", # Pake dash '-', bukan underscore '_'
            "Notion-Version": "2022-06-28"
        }

        data = {
            "parent": {"database_id": os.environ.get("DATABASE_ID")},
            "properties": {
                "Name": {"title": [{"text": {"content": final_title}}]},
                "Category": {"select": {"name": req.category}},
                "Date": {"date": {"start": date_iso}}            
            },
            "children": content_blocks
        }

        # requests.post (bukan .pos)
        res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)

        if res.status_code != 200:
            return {"status": "error", "message": res.json()}

        return {"status": "success", "notion_res": res.json()}

    except Exception as e:
        return {"status": "error", "message": str(e)}