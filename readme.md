## Running the logic-manager tests

These test files require pytest:
- test_logic_manager.py
- test_individual_rules_logic_manager.py

```powershell
python -m pip install pytest
```

Then run both test files:

```powershell
python -m pytest test_logic_manager.py test_individual_rules_logic_manager.py -q
```

Pytest is only required for these test files