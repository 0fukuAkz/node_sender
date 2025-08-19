import base64

def encode_attachment(path, obfuscate=False):
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')
    if obfuscate:
        half = len(b64) // 2
        return b64[:half][::-1] + b64[half:][::-1]
    return b64