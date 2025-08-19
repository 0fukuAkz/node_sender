from faker import Faker
import uuid

faker = Faker()

def generate_identity():
    first, last = faker.first_name(), faker.last_name()
    full = f"{first} {last}"
    company = faker.company().replace(',', '')
    domain = company.replace(' ', '').lower() + '.com'
    email = f"{first.lower()}.{last.lower()}@{domain}"
    return {
        'full_name': full,
        'email': email,
        'company': company,
        'from_field': f'"{full}" <{email}>',
        'uuid': str(uuid.uuid4())  # ← Added
    }