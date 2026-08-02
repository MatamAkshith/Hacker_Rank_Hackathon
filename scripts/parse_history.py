import re
from pathlib import Path

def parse():
    log_path = Path("/Users/ashu/hackerrank_orchestrate_august26/log.txt")
    if not log_path.exists():
        print("Log file not found at", log_path)
        return

    content = log_path.read_text(encoding="utf-8")
    
    # Split by ## [TIMESTAMP] headers
    blocks = re.split(r'## \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\+\d{2}:\d{2}|Z)?\s+', content)
    
    sprints = []
    sprint_idx = 1
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
            
        # Extract title (first line)
        lines = block.splitlines()
        title = lines[0].strip()
        
        # Check if onboarding header
        if "ONBOARDING COMPLETE" in title:
            continue
            
        # Parse User Prompt
        prompt_match = re.search(r'User Prompt \(verbatim, secrets redacted\):\s*(.*?)\s*(?=Agent Response Summary:|$)', block, re.DOTALL)
        # Parse Agent Response
        response_match = re.search(r'Agent Response Summary:\s*(.*?)\s*(?=Actions:|$)', block, re.DOTALL)
        
        if prompt_match and response_match:
            prompt = prompt_match.group(1).strip()
            response = response_match.group(1).strip()
            
            # Determine agent name based on block text or metadata
            agent = "Gemini (Antigravity)"
            if "tool=" in block:
                tool_match = re.search(r'tool=(\w+)', block)
                if tool_match:
                    t_name = tool_match.group(1)
                    if t_name.lower() in ("claude", "cursor"):
                        agent = "Cursor"
                    elif t_name.lower() in ("gemini", "antigravity"):
                        agent = "Gemini (Antigravity)"
                    else:
                        agent = t_name
            
            sprints.append(f"""==============================
Sprint {sprint_idx}
Agent: {agent}
==============================

Prompt:
{prompt}

Response:
{response}
""")
            sprint_idx += 1

    out_path = Path("/Users/ashu/Documents/VMEG/Hackathons/HackerRank/hackerrank-orchestrate-august26/sprint_history.txt")
    out_path.write_text("\n".join(sprints), encoding="utf-8")
    print(f"Successfully generated {sprint_idx - 1} sprint entries in {out_path}")

if __name__ == "__main__":
    parse()
