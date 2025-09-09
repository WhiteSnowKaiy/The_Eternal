# config/transcript_config.py
async def createHeader(nameOfTranscript: str):
    header = f"""<!doctype html>
<html lang="en">
<head> 
  <meta charset="UTF-8"> 
  <meta name="viewport" content="width=device-width, initial-scale=1.0"> 
  <title>Transcript of {nameOfTranscript}</title> 
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap');

    :root {{
      --dark-bg: #36393f;
      --dark-primary: #2f3136;
      --text: #dcddde;
      --muted: #b9bbbe;
      --link: #00aff4;
      --radius: 10px;
    }}

    * {{ box-sizing: border-box; }}
    html, body {{ height: 100%; }}
    body {{
      margin: 0;
      background: var(--dark-bg);
      color: var(--text);
      font: 14px/1.4 'Roboto', system-ui, -apple-system, Segoe UI, sans-serif;
    }}

    .transcript {{
      max-width: 900px;
      margin: 0 auto;
      padding: 24px 16px 80px;
    }}

    .title {{
      font-size: 18px;
      font-weight: 500;
      margin-bottom: 16px;
      color: #fff;
    }}

    /* Single message row */
    .message {{
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 10px 12px;
    }}

    .message:hover {{ background: rgba(255,255,255,0.02); }}

    .avatar {{
      width: 40px;
      height: 40px;
      border-radius: 50%;
      flex: 0 0 40px;
      object-fit: cover;
      background: #232428;
    }}

    .content {{
      display: flex;
      flex-direction: column;
      min-width: 0; /* allows text to wrap properly */
      flex: 1 1 auto;
    }}

    .header {{
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 2px;
      white-space: nowrap;
    }}

    .username {{
      font-weight: 500;
    }}

    .message-body {{
      white-space: pre-wrap; /* preserve newlines */
      word-wrap: break-word;
      overflow-wrap: anywhere;
    }}

    /* Code blocks you already generate as <pre> */
    pre {{
      background: var(--dark-primary);
      color: #f8f8f2;
      padding: 10px 12px;
      border-radius: var(--radius);
      margin: 6px 0 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      font-size: 13px;
      overflow-x: auto;
    }}

    /* Inline images (custom emoji) */
    .message-body img.emoji {{
      width: 22px;
      height: 22px;
      vertical-align: -4px;
    }}

    /* Attachments block under the message */
    .attachments {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 6px;
    }}

    .attachments .attachment {{
      background: #202225;
      border-radius: var(--radius);
      padding: 6px;
      max-width: 520px;
    }}

    .attachments .attachment img {{
      display: block;
      max-width: 500px;
      width: 100%;
      height: auto;
      border-radius: 6px;
    }}

    a {{ color: var(--link); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <main class="transcript">
    <div class="title">Transcript of {nameOfTranscript}</div>
"""
    return header
