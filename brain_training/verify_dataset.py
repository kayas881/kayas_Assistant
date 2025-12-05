#!/usr/bin/env python
"""Comprehensive dataset verification script"""
import json
import os
import sys

print('🔍 VERIFICATION: mega_brain_dataset_20k.jsonl')
print('=' * 70)

try:
    # 1. File size and line count
    file_size_mb = os.path.getsize('mega_brain_dataset_20k.jsonl') / 1024 / 1024
    
    with open('mega_brain_dataset_20k.jsonl', 'r') as f:
        lines = f.readlines()
    
    print(f'✅ File size: {file_size_mb:.2f} MB')
    print(f'✅ Total lines: {len(lines)}')
    
    if len(lines) != 20000:
        print(f'❌ ERROR: Expected 20000 lines, got {len(lines)}')
        sys.exit(1)
    
    # 2. Check JSONL format and structure
    print(f'\n✅ Checking JSONL format...')
    invalid_count = 0
    missing_structure = 0
    
    for i, line in enumerate(lines):
        try:
            entry = json.loads(line)
            
            # Verify structure
            if 'messages' not in entry:
                missing_structure += 1
                continue
            
            if not isinstance(entry['messages'], list) or len(entry['messages']) != 3:
                missing_structure += 1
                continue
            
            # Check roles
            if entry['messages'][0]['role'] != 'system':
                missing_structure += 1
            if entry['messages'][1]['role'] != 'user':
                missing_structure += 1
            if entry['messages'][2]['role'] != 'assistant':
                missing_structure += 1
                
        except json.JSONDecodeError:
            invalid_count += 1
    
    if invalid_count == 0 and missing_structure == 0:
        print(f'   ✅ All 20000 entries valid JSON')
        print(f'   ✅ All entries have correct structure (system/user/assistant)')
    else:
        print(f'   ❌ Invalid entries: {invalid_count}')
        print(f'   ❌ Missing structure: {missing_structure}')
        sys.exit(1)
    
    # 3. Sample entries verification
    print(f'\n✅ Sampling entries...')
    e1 = json.loads(lines[0])
    print(f'   Entry 1 (start):')
    print(f'      User: {e1["messages"][1]["content"][:60]}...')
    
    e5000 = json.loads(lines[4999])
    print(f'   Entry 5000 (middle):')
    print(f'      User: {e5000["messages"][1]["content"][:60]}...')
    
    e20000 = json.loads(lines[19999])
    print(f'   Entry 20000 (end):')
    print(f'      User: {e20000["messages"][1]["content"][:60]}...')
    
    # 4. Tool coverage
    print(f'\n✅ Checking tool coverage...')
    tool_categories = {
        'cv': 0, 'filewatcher': 0, 'ocr': 0, 'clipboard': 0, 'process': 0,
        'desktop': 0, 'uia': 0, 'perception': 0, 'browser': 0, 'filesystem': 0,
        'email': 0, 'slack': 0, 'spotify': 0, 'network': 0
    }
    
    for i, line in enumerate(lines):
        entry = json.loads(line)
        assistant_msg = entry['messages'][2]['content']
        try:
            steps = json.loads(assistant_msg)
            for step in steps:
                tool = step.get('tool', '')
                if '.' in tool:
                    category = tool.split('.')[0]
                    if category in tool_categories:
                        tool_categories[category] += 1
        except:
            pass
    
    print(f'   Tool categories found: {sum(1 for v in tool_categories.values() if v > 0)}/14')
    for cat, count in sorted(tool_categories.items()):
        if count > 0:
            print(f'      {cat:15} = {count:5} uses')
    
    # 5. NEW TOOLS specifically
    print(f'\n✅ NEW TOOLS verification:')
    new_tools = {
        'filewatcher.wait_for_file': 0,
        'ocr.read_region': 0,
        'process.monitor_process': 0,
        'clipboard.monitor': 0,
        'cv.find_image': 0,
        'cv.click_image': 0,
        'cv.wait_for_image': 0,
        'cv.screenshot': 0
    }
    
    for line in lines:
        entry = json.loads(line)
        assistant_msg = entry['messages'][2]['content']
        try:
            steps = json.loads(assistant_msg)
            for step in steps:
                tool = step.get('tool', '')
                if tool in new_tools:
                    new_tools[tool] += 1
        except:
            pass
    
    all_new_found = True
    for tool, count in new_tools.items():
        if count > 0:
            print(f'   ✅ {tool:30} = {count:4} examples')
        else:
            print(f'   ⚠️  {tool:30} = 0 examples')
            all_new_found = False
    
    # 6. Message content verification
    print(f'\n✅ Checking message content...')
    empty_users = 0
    empty_assistants = 0
    
    for line in lines:
        entry = json.loads(line)
        if not entry['messages'][1]['content'].strip():
            empty_users += 1
        if not entry['messages'][2]['content'].strip():
            empty_assistants += 1
    
    if empty_users == 0 and empty_assistants == 0:
        print(f'   ✅ All user messages have content')
        print(f'   ✅ All assistant messages have content')
    else:
        print(f'   ❌ Empty user messages: {empty_users}')
        print(f'   ❌ Empty assistant messages: {empty_assistants}')
        sys.exit(1)
    
    # 7. Assistant message validity (all should be JSON arrays)
    print(f'\n✅ Checking assistant message format...')
    valid_json_steps = 0
    invalid_json_steps = 0
    
    for line in lines:
        entry = json.loads(line)
        assistant_msg = entry['messages'][2]['content']
        try:
            steps = json.loads(assistant_msg)
            if isinstance(steps, list):
                valid_json_steps += 1
            else:
                invalid_json_steps += 1
        except:
            invalid_json_steps += 1
    
    print(f'   ✅ Valid JSON tool steps: {valid_json_steps}/20000')
    if invalid_json_steps > 0:
        print(f'   ❌ Invalid JSON tool steps: {invalid_json_steps}')
        sys.exit(1)
    
    # 8. Tool count distribution
    print(f'\n✅ Tool steps distribution:')
    step_counts = []
    for line in lines:
        entry = json.loads(line)
        assistant_msg = entry['messages'][2]['content']
        try:
            steps = json.loads(assistant_msg)
            step_counts.append(len(steps))
        except:
            pass
    
    if step_counts:
        avg_steps = sum(step_counts) / len(step_counts)
        min_steps = min(step_counts)
        max_steps = max(step_counts)
        print(f'   Average steps per task: {avg_steps:.1f}')
        print(f'   Min steps: {min_steps}, Max steps: {max_steps}')
    
    # Final summary
    print(f'\n' + '=' * 70)
    if all_new_found:
        print(f'✅ VERIFICATION PASSED - Dataset is READY FOR TRAINING!')
    else:
        print(f'⚠️  VERIFICATION PASSED - Some new tools not represented')
    print(f'=' * 70)
    
except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
