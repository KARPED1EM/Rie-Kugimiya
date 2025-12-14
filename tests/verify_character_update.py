"""
Simple verification script to check if the update_character method exists
and has the correct signature.
"""

import inspect
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def verify_update_character_method():
    """Verify the update_character method exists in SessionClient"""
    print("Verifying update_character method...")
    
    # Read the SessionClient file content
    session_client_path = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "src", 
        "services", 
        "session", 
        "session_client.py"
    )
    
    with open(session_client_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the update_character method
    if "def update_character(self, character: Character):" in content:
        print("✓ update_character method signature found")
    else:
        print("✗ update_character method signature not found")
        return False
    
    # Check that it updates self.character
    if "self.character = character" in content:
        print("✓ Character reference update found")
    else:
        print("✗ Character reference update not found")
        return False
    
    # Check that it recreates the coordinator
    if "self.coordinator = BehaviorCoordinator(character)" in content:
        print("✓ Coordinator recreation found")
    else:
        print("✗ Coordinator recreation not found")
        return False
    
    print("\nAll checks passed! ✓")
    return True


def verify_routes_update():
    """Verify that routes.py calls update_character on SessionClient instances"""
    print("\nVerifying routes.py updates...")
    
    routes_path = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "src", 
        "api", 
        "routes.py"
    )
    
    with open(routes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for calling update_character
    if "session_client.update_character(character)" in content:
        print("✓ SessionClient.update_character() call found")
    else:
        print("✗ SessionClient.update_character() call not found")
        return False
    
    # Check for updated notification message
    if "角色配置已更新" in content:
        print("✓ Updated notification message found")
    else:
        print("✗ Updated notification message not found")
        return False
    
    # Check that it's not the old message
    if "角色配置已更新，正在重新初始化..." in content:
        print("✗ Old notification message still present")
        return False
    else:
        print("✓ Old notification message removed")
    
    print("\nAll checks passed! ✓")
    return True


if __name__ == "__main__":
    success = verify_update_character_method() and verify_routes_update()
    
    if success:
        print("\n" + "="*50)
        print("All verifications passed! ✓")
        print("="*50)
        sys.exit(0)
    else:
        print("\n" + "="*50)
        print("Some verifications failed! ✗")
        print("="*50)
        sys.exit(1)
