def read_lines(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def log_line(path, content):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(content + '\n')

def clear_file(path):
    open(path, 'w').close()