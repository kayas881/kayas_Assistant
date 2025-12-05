#!/usr/bin/env python3
"""
IMPLEMENTATION CHECKLIST - Deep UI Workflows

Verify all deep UI workflow features have been added correctly.
"""

def check_implementation():
    """Verify all deep UI workflows are properly integrated"""
    
    from expand_to_mega_dataset import (
        generate_messaging_workflows,
        generate_spotify_workflows,
        generate_browser_deep_workflows,
        generate_text_editor_workflows,
        generate_system_admin_workflows,
        get_all_scenarios,
    )
    
    results = {}
    
    print("\n" + "="*80)
    print(" DEEP UI WORKFLOWS - IMPLEMENTATION VERIFICATION")
    print("="*80 + "\n")
    
    # Check 1: Messaging workflows
    print("[1/5] Messaging Workflows...")
    try:
        workflows = generate_messaging_workflows()
        whatsapp = len([w for w in workflows if "WhatsApp" in w[0]])
        discord = len([w for w in workflows if "Discord" in w[0]])
        slack = len([w for w in workflows if "Slack" in w[0]])
        
        print(f"      [OK] WhatsApp: {whatsapp} scenarios")
        print(f"      [OK] Discord:  {discord} scenarios")
        print(f"      [OK] Slack:    {slack} scenarios")
        print(f"      [OK] TOTAL:    {len(workflows)} scenarios\n")
        results["messaging"] = len(workflows)
    except Exception as e:
        print(f"      [FAIL] {e}\n")
        results["messaging"] = 0
    
    # Check 2: Spotify workflows
    print("[2/5] Spotify Workflows...")
    try:
        workflows = generate_spotify_workflows()
        search = len([w for w in workflows if "play" in w[0].lower() and "by" in w[0]])
        playlist = len([w for w in workflows if "playlist" in w[0].lower()])
        control = len([w for w in workflows if any(x in w[0].lower() for x in ["pause", "skip", "previous"])])
        
        print(f"      [OK] Search & Play:    {search} scenarios")
        print(f"      [OK] Playlists:        {playlist} scenarios")
        print(f"      [OK] Playback Control: {control} scenarios")
        print(f"      [OK] TOTAL:            {len(workflows)} scenarios\n")
        results["spotify"] = len(workflows)
    except Exception as e:
        print(f"      [FAIL] {e}\n")
        results["spotify"] = 0
    
    # Check 3: Browser deep workflows
    print("[3/5] Browser Deep Workflows...")
    try:
        workflows = generate_browser_deep_workflows()
        google = len([w for w in workflows if "google" in w[0].lower()])
        github = len([w for w in workflows if "github" in w[0].lower()])
        amazon = len([w for w in workflows if "amazon" in w[0].lower()])
        youtube = len([w for w in workflows if "youtube" in w[0].lower()])
        
        print(f"      [OK] Google Search:    {google} scenarios")
        print(f"      [OK] GitHub:           {github} scenarios")
        print(f"      [OK] Amazon Shopping:  {amazon} scenarios")
        print(f"      [OK] YouTube:          {youtube} scenarios")
        print(f"      [OK] TOTAL:            {len(workflows)} scenarios\n")
        results["browser"] = len(workflows)
    except Exception as e:
        print(f"      [FAIL] {e}\n")
        results["browser"] = 0
    
    # Check 4: Text editor workflows
    print("[4/5] Text Editor Workflows...")
    try:
        workflows = generate_text_editor_workflows()
        vscode = len([w for w in workflows if "VSCode" in w[0]])
        notepad = len([w for w in workflows if "Notepad" in w[0]])
        
        print(f"      [OK] VSCode: {vscode} scenarios")
        print(f"      [OK] Notepad: {notepad} scenarios")
        print(f"      [OK] TOTAL: {len(workflows)} scenarios\n")
        results["editors"] = len(workflows)
    except Exception as e:
        print(f"      [FAIL] {e}\n")
        results["editors"] = 0
    
    # Check 5: System admin workflows
    print("[5/5] System Admin Workflows...")
    try:
        workflows = generate_system_admin_workflows()
        monitor = len([w for w in workflows if "resources" in w[0].lower()])
        backup = len([w for w in workflows if "backup" in w[0].lower()])
        cleanup = len([w for w in workflows if "cleanup" in w[0].lower()])
        
        print(f"      [OK] Monitoring: {monitor} scenarios")
        print(f"      [OK] Backup:     {backup} scenarios")
        print(f"      [OK] Cleanup:    {cleanup} scenarios")
        print(f"      [OK] TOTAL:      {len(workflows)} scenarios\n")
        results["system"] = len(workflows)
    except Exception as e:
        print(f"      [FAIL] {e}\n")
        results["system"] = 0
    
    # Summary
    total = sum(results.values())
    
    print("="*80)
    print(" SUMMARY")
    print("="*80 + "\n")
    
    print(f"Messaging:   {results['messaging']:3d} scenarios")
    print(f"Spotify:     {results['spotify']:3d} scenarios")
    print(f"Browser:     {results['browser']:3d} scenarios")
    print(f"Editors:     {results['editors']:3d} scenarios")
    print(f"System:      {results['system']:3d} scenarios")
    print("-" * 30)
    print(f"TOTAL:       {total:3d} scenarios\n")
    
    if total >= 240:
        print("[SUCCESS] All deep UI workflows implemented!")
        print(f"          Generated {total} scenarios across 5 categories\n")
        return True
    else:
        print(f"[WARNING] Only {total}/242 scenarios found. Check implementation.\n")
        return False
    
    # Check get_all_scenarios integration
    print("\nChecking integration with get_all_scenarios()...\n")
    
    try:
        all_scenarios = get_all_scenarios()
        print(f"[OK] get_all_scenarios() working")
        print(f"     Total unique scenarios: {len(all_scenarios)}\n")
        
        # Sample scenarios
        print("Sample scenarios generated:")
        for i, (text, tools) in enumerate(all_scenarios[:5]):
            print(f"  {i+1}. {text[:60]}... ({len(tools)} steps)")
        
        print("\n[SUCCESS] Dataset generation pipeline verified!\n")
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}\n")
        return False


if __name__ == "__main__":
    success = check_implementation()
    exit(0 if success else 1)
