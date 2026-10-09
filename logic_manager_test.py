from dictionary import MEASUREMENT_UNITS
import json

# Load the AI response from the test script
with open('AI_response_test_script.json', 'r') as f:
    ai_response = json.load(f)

with open('User_input_test_script.json', 'r') as f:
    user_response = json.load(f)
