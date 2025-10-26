"""
Inference helper for Kayas LoRA adapters.
Handles response parsing and validation.
"""
import json
import re
from typing import Dict, List, Optional, Any


def extract_json_from_response(raw_response: str) -> str:
    """
    Extract JSON from model response, handling common prefixes/suffixes.
    
    Args:
        raw_response: Raw text from model generation
        
    Returns:
        Cleaned JSON string
    """
    # Remove common prefixes (assistant, role markers, etc.)
    text = raw_response.strip()
    
    # Remove 'assistant' prefix if present
    if text.startswith('assistant'):
        text = text[len('assistant'):].strip()
    
    # Remove role markers like <|im_start|>assistant, <|im_end|>, etc.
    text = re.sub(r'<\|im_start\|>\w+', '', text)
    text = re.sub(r'<\|im_end\|>', '', text)
    
    # Find JSON array or object bounds
    start_idx = text.find('[')
    if start_idx == -1:
        start_idx = text.find('{')
    
    if start_idx == -1:
        return text  # No JSON found, return as-is
    
    # Find matching closing bracket
    if text[start_idx] == '[':
        end_char = ']'
    else:
        end_char = '}'
    
    # Simple bracket matching (handles nested)
    depth = 0
    end_idx = -1
    for i in range(start_idx, len(text)):
        if text[i] in '[{':
            depth += 1
        elif text[i] in ']}':
            depth -= 1
            if depth == 0:
                end_idx = i + 1
                break
    
    if end_idx == -1:
        end_idx = len(text)
    
    return text[start_idx:end_idx].strip()


def parse_tool_calls(response: str) -> Optional[List[Dict[str, Any]]]:
    """
    Parse tool calls from model response.
    
    Args:
        response: Raw or cleaned response text
        
    Returns:
        List of tool call dicts, or None if parsing failed
    """
    try:
        # Clean the response first
        json_str = extract_json_from_response(response)
        
        # Parse JSON
        parsed = json.loads(json_str)
        
        # Ensure it's a list
        if isinstance(parsed, dict):
            parsed = [parsed]
        
        # Validate structure
        if not isinstance(parsed, list):
            return None
        
        for item in parsed:
            if not isinstance(item, dict):
                return None
            if 'tool' not in item:
                return None
            # args is optional but should be dict if present
            if 'args' in item and not isinstance(item['args'], dict):
                return None
        
        return parsed
    
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"Parse error: {e}")
        return None


def validate_tool_call(tool_call: Dict[str, Any], available_tools: Optional[List[str]] = None) -> bool:
    """
    Validate a single tool call structure.
    
    Args:
        tool_call: Tool call dict with 'tool' and 'args'
        available_tools: Optional list of valid tool names
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(tool_call, dict):
        return False
    
    if 'tool' not in tool_call:
        return False
    
    tool_name = tool_call['tool']
    if not isinstance(tool_name, str):
        return False
    
    # Check against available tools if provided
    if available_tools and tool_name not in available_tools:
        return False
    
    # Validate args if present
    if 'args' in tool_call:
        if not isinstance(tool_call['args'], dict):
            return False
    
    return True


def format_tool_calls_for_display(tool_calls: List[Dict[str, Any]]) -> str:
    """
    Format tool calls as readable text.
    
    Args:
        tool_calls: List of tool call dicts
        
    Returns:
        Formatted string
    """
    lines = []
    for i, call in enumerate(tool_calls, 1):
        tool = call.get('tool', 'unknown')
        args = call.get('args', {})
        lines.append(f"{i}. {tool}")
        if args:
            for key, value in args.items():
                lines.append(f"   {key}: {value}")
    return '\n'.join(lines)


if __name__ == '__main__':
    # Test with the example from your inference
    test_response = """assistant
[
  {
    "tool": "process.start_program",
    "args": {
      "program": "notepad.exe",
      "background": true
    }
  },
  {
    "tool": "filesystem.archive_file",
    "args": {
      "filename": "todo.txt",
      "destination": "desktop/archive/"
    }
  }
]"""
    
    print("Testing response parser...")
    print("\n--- Raw Response ---")
    print(test_response)
    
    print("\n--- Cleaned JSON ---")
    cleaned = extract_json_from_response(test_response)
    print(cleaned)
    
    print("\n--- Parsed Tool Calls ---")
    tools = parse_tool_calls(test_response)
    if tools:
        print("✅ Successfully parsed!")
        print(json.dumps(tools, indent=2))
        
        print("\n--- Formatted Display ---")
        print(format_tool_calls_for_display(tools))
        
        print("\n--- Validation ---")
        for i, tool in enumerate(tools, 1):
            valid = validate_tool_call(tool)
            status = "✅" if valid else "❌"
            print(f"{status} Tool {i}: {tool.get('tool')}")
    else:
        print("❌ Failed to parse")
