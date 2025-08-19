import os
import string


def load_template(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def apply_placeholders(template_str, placeholder_dict):
    # Safer substitution; leaves unknown placeholders intact
    tpl = string.Template(template_str)
    # Translate {key} to $key expected by Template
    # Simple mapping: replace {key} with $key for provided keys only
    mapped = template_str
    for key in placeholder_dict.keys():
        mapped = mapped.replace(f"{{{key}}}", f"${key}")
    return string.Template(mapped).safe_substitute({k: str(v) for k, v in placeholder_dict.items()})