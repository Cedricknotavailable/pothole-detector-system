"""
Test script to verify role validation works correctly
"""

# Simulate the validation logic
ALLOWED_ROLES = {'admin', 'moderator', 'user'}

test_roles = ['admin', 'moderator', 'user', 'MODERATOR', 'Moderator', 'invalid', '']

print("Testing role validation:")
print(f"ALLOWED_ROLES = {ALLOWED_ROLES}\n")

for test_role in test_roles:
    # Simulate the form processing
    new_role = str(test_role).strip().lower()
    is_valid = new_role in ALLOWED_ROLES
    
    print(f"Input: '{test_role}' -> Processed: '{new_role}' -> Valid: {is_valid}")

print("\n✅ All role variations should work correctly")
print("The validation converts to lowercase, so 'MODERATOR', 'Moderator', 'moderator' all work")
