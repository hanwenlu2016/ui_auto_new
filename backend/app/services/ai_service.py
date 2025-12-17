import re
from typing import List, Dict, Any

class AIService:
    """
    Mock AI Service for generating test steps from natural language prompts.
    Uses heuristic rules and regex to interpret commands.
    """
    
    def generate_steps_from_text(self, prompt: str) -> List[Dict[str, Any]]:
        steps = []
        # Split by common delimiters: newline, comma, "and", "then" (avoiding period to protect URLs)
        sentences = re.split(r'\n|,| and | then ', prompt)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            step = self._parse_sentence(sentence)
            if step:
                steps.append(step)
                
        return steps
    
    def _parse_sentence(self, sentence: str) -> Dict[str, Any]:
        sentence = sentence.lower()
        
        # Rule 1: Navigation (open, goto, visit)
        # "open http://google.com"
        if re.search(r'\b(open|goto|visit)\b', sentence):
            # Extract URL: simple regex for http/https or just domain like "google.com"
            url_match = re.search(r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,})', sentence)
            if url_match:
                url = url_match.group(0)
                if not url.startswith('http'):
                    url = 'http://' + url
                return {"action": "goto", "value": url}

        # Rule 2: Wait (wait, sleep)
        # "wait 2 seconds"
        if re.search(r'\b(wait|sleep)\b', sentence):
            # Extract number
            num_match = re.search(r'(\d+(\.\d+)?)', sentence)
            if num_match:
                return {"action": "wait", "value": num_match.group(0)}
                
        # Rule 3: Click (click, press)
        # "click (on) Login" -> target='text=Login'
        if re.search(r'\b(click|press)\b', sentence):
            # Remove action word
            target = re.sub(r'\b(click|press|on)\b', '', sentence).strip()
            # Heuristic: if target is "login button", try to be smart, else just use text
            if "button" in target:
                 target = target.replace("button", "").strip()
            
            # Remove quotes
            target = target.replace('"', '').replace("'", "")
            
            if target:
                return {"action": "click", "target": f"text={target}"}

        # Rule 4: Fill/Type (type, enter, fill, input)
        # "type 'admin' in username" -> target='input[placeholder*="username"]' (too complex?)
        # Let's try: "type 'admin' into Username"
        if re.search(r'\b(type|enter|fill|input)\b', sentence):
            # Extract value in quotes
            value_match = re.search(r"['\"](.*?)['\"]", sentence)
            value = ""
            if value_match:
                value = value_match.group(1)
            
            # Extract target: remove action and value
            remainder = re.sub(r'\b(type|enter|fill|input)\b', '', sentence)
            remainder = re.sub(r"['\"].*?['\"]", '', remainder).strip()
            # Remove prepositions
            remainder = re.sub(r'\b(in|into|to|field|box)\b', '', remainder).strip()
            
            if remainder:
                # Guess selector
                target = f"input[placeholder~='{remainder}']" # primitive guess
                # Or just by name/id heuristic
                # Simple fallback: if remainder looks like an ID/name
                if ' ' not in remainder:
                     target = f"#{remainder}" 
                else: 
                     # use placeholder heuristic for now
                     target = f"input[placeholder*='{remainder}' i]"
                     
                return {"action": "fill", "target": target, "value": value}

        return None

ai_service = AIService()
