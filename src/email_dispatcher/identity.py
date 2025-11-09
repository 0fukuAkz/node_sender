from faker import Faker
import uuid
from typing import Dict

faker = Faker()


def generate_identity() -> Dict[str, str]:
    """
    Generate random identity for email sending.
    
    Returns:
        Dictionary with identity fields:
        - full_name: Random full name
        - email: Generated email address
        - company: Random company name
        - from_field: Formatted from field
        - uuid: Unique identifier
    """
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
        'uuid': str(uuid.uuid4())
    }