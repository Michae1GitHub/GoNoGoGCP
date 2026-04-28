import csv
import random
from datetime import datetime, timedelta

OUTPUT_FILE = "data/users_fake.csv"

first_names = [
    "Jeny", "Akshay", "John", "Michael", 
    "Emma", "Olivia", "Ava", "Sophia", "Isabella", "Mia", "Charlotte", "Amelia",
    "Harper", "Evelyn", "Abigail", "Emily", "Ella", "Elizabeth", "Camila", "Luna",
    "Sofia", "Avery", "Mila", "Aria", "Scarlett", "Penelope", "Layla", "Chloe",
    "Victoria", "Madison", "Eleanor", "Grace", "Nora", "Riley", "Zoey", "Hannah",
    "Hazel", "Lily", "Ellie", "Violet", "Lillian", "Zoe", "Stella", "Aurora",
    "Natalie", "Emilia", "Everly", "Leah", "Aubrey", "Willow", "Addison", "Lucy",
    "Audrey", "Bella", "Nova", "Brooklyn", "Paisley", "Savannah", "Claire", "Skylar",
    "Isla", "Genesis", "Naomi", "Elena", "Caroline", "Eliana", "Anna", "Maya",
    "Valentina", "Ruby", "Kennedy", "Ivy", "Ariana", "Aaliyah", "Cora", "Madelyn",
    "Alice", "Kinsley", "Hailey", "Gabriella", "Allison", "Gianna", "Serenity", "Samantha",
    "Sarah", "Autumn", "Quinn", "Eva", "Piper", "Sophie", "Sadie", "Delilah",
    "Josephine", "Nevaeh", "Adeline", "Arya", "Emery", "Lydia", "Clara", "Vivian",
    "Madeline", "Peyton", "Julia", "Rylee"
]

last_names = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
    "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
    "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
    "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
    "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza",
    "Ruiz", "Hughes", "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers",
    "Long", "Ross", "Foster", "Jimenez"
]

domains = ["gmail.com", "thisisanemail.com", "outlook.com", "idunno.com", "icloud.com"]


with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["user","email", "password_hash", "created_at"])

    for i in range(1, 1003):
        first = random.choice(first_names).lower()
        last = random.choice(last_names).lower()
        domain = random.choice(domains)

        email = f"{first}.{last}{i}@{domain}"
        user = f"{first}{last}{i}"


        password_hash = str(random.randint(10000000, 99999999))
        

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        

        writer.writerow([user,email, password_hash, created_at])
