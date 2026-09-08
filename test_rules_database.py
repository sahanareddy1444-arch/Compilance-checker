import json

RULE_FILE = "compliance_rules/legal_rules.json"

with open(RULE_FILE, "r", encoding="utf-8") as file:
    database = json.load(file)

print("\n========================================")
print("LEGAL RULE DATABASE")
print("========================================")

print("Database:", database["database_name"])
print("Version:", database["version"])
print("Last updated:", database["last_updated"])

print("\nTotal rules:", len(database["rules"]))

print("\nRules:")

for rule in database["rules"]:
    print(
        rule["rule_id"],
        "→",
        rule["name"]
    )