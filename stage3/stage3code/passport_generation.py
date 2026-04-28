import csv
import random
import string
from datetime import date



country_ids = []
with open("data/country_sql.csv", "r", encoding="utf-8-sig", newline="") as f:
	reader = csv.DictReader(f)
	for row in reader:
		country_ids.append(row["iso_alpha3"].strip())


users = []
with open("data/users_fake.csv", "r", encoding="utf-8-sig", newline="") as f:
	reader = csv.DictReader(f)
	for row in reader:
		users.append(row["user"].strip())




twops = set(random.sample(users, 100))

nums = set()

with open("data/passports_fake.csv", "w", encoding="utf-8", newline="") as f:
	writer = csv.writer(f)
	writer.writerow([
		"passport_number",
		"user_id",
		"issuing_country_id",
		"expiry_date",
		"created_at"
	])

	total_passports = 0

	for user_id in users:
		num_passports = random.choice([1,1,1,1,1,1,1,1,1,2])
		
		chosen_countries = random.sample(country_ids, num_passports)
			

		today = date(2026, 3, 29)
		expiry = date(2036, 3, 28)
		
		for country_id in chosen_countries:

			passport_number = "P" + "".join(random.choices(string.digits, k=8))
			while passport_number in nums:
				passport_number = "P" + "".join(random.choices(string.digits, k=8))

			nums.add(passport_number)
			writer.writerow([
				passport_number,
				user_id,
				country_id,
				expiry.isoformat(),
				today.isoformat()
			])
