import os
import re
import zlib
import argparse
from datetime import datetime

def parse_object(object_hash, description=None):
    object_path = os.path.join(config['repo_path'], '.git', 'objects', object_hash[:2], object_hash[2:])
    with open(object_path, 'rb') as file:
        raw_object_content = zlib.decompress(file.read())
        header, raw_object_body = raw_object_content.split(b'\x00', maxsplit=1)
        object_type, content_size = header.decode().split(' ')
        object_dict = {}
        if object_type == 'commit':
            object_dict['label'] = 'commit/' + get_msg(raw_object_body)
            object_dict['children'] = parse_commit(raw_object_body)
            object_dict['message'] = get_msg(raw_object_body)
            object_dict['date'] = get_date(raw_object_body)
        elif object_type == 'tree':
            object_dict['label'] = r'[tree]\n' + object_hash[:6]
            object_dict['children'] = parse_tree(raw_object_body)
        elif object_type == 'blob':
            object_dict['label'] = r'[blob]\n' + object_hash[:6]
            object_dict['children'] = []
        return object_dict

def parse_tree(raw_content):
    children = []
    rest = raw_content
    while rest:
        mode, rest = rest.split(b' ', maxsplit=1)
        name, rest = rest.split(b'\x00', maxsplit=1)
        sha1, rest = rest[:20].hex(), rest[20:]
        children.append(parse_object(sha1, description=name.decode()))
    return children

def parse_commit_data(raw_content):
    content = raw_content.decode()
    content_lines = content.split('\n')
    commit_data = {}
    commit_data['tree'] = content_lines[0].split()[1]
    content_lines = content_lines[1:]
    commit_data['parents'] = []

    while content_lines and content_lines[0].startswith('parent'):
        commit_data['parents'].append(content_lines[0].split()[1])
        content_lines = content_lines[1:]

    while content_lines and content_lines[0].strip():
        key, *values = content_lines[0].split()
        commit_data[key] = ' '.join(values)
        content_lines = content_lines[1:]

    commit_data['message'] = '\n'.join(content_lines[1:]).strip()
    return commit_data

def get_msg(raw_content):
    commit_data = parse_commit_data(raw_content)
    return commit_data['message']

def get_date(raw_content):
    commit_data = parse_commit_data(raw_content)
    return commit_data['committer']

def parse_commit(raw_content):
    commit_data = parse_commit_data(raw_content)
    return [parse_object(commit_data['tree'])] + [parse_object(parent) for parent in commit_data['parents']]


def get_last_commit():
    head_path = os.path.join(config['repo_path'], '.git', 'refs', 'heads', config['branch'])
    with open(head_path, 'r') as file:
        return file.read().strip()

def extract_unix_time(input_string):
    match = re.search(r'(\d{10})\s([+-]\d{4})', input_string)
    if match:
        unix_time = int(match.group(1))
        dt = datetime.fromtimestamp(unix_time)
        return dt
    else:
        return None

import subprocess

def generate_dot(filename, cutoff_date):
    def recursive_write(file, tree, written_edges):
        label = tree['label']
        for child in tree['children']:
            if child['label'].startswith('commit') and extract_unix_time(child['date']) < cutoff_date:
                edge = f'    "{label}" -> "{child["label"]}"\n'
                if edge not in written_edges:
                    file.write(edge)
                    written_edges.add(edge)
            recursive_write(file, child, written_edges)

    last_commit = get_last_commit()
    tree = parse_object(last_commit)
    with open(filename, 'w') as file:
        file.write('digraph G {\n')
        written_edges = set()
        recursive_write(file, tree, written_edges)
        file.write('}')

    # Создание PNG-файла из DOT-файла
    png_filename = filename.replace('.dot', '.png')
    subprocess.run(['dot', '-Tpng', filename, '-o', png_filename], check=True)
    print(f'PNG файл создан: {png_filename}')


def main():
    parser = argparse.ArgumentParser(description='Генерация графа зависимостей для git-репозитория.')
    parser.add_argument('repo_path', help='Путь к анализируемому репозиторию')
    parser.add_argument('output_file', help='Путь к файлу-результату в виде кода')
    parser.add_argument('cutoff_date', help='Дата коммитов в формате YYYY-MM-DD')

    args = parser.parse_args()

    global config
    config = {
        'repo_path': args.repo_path,
        'branch': 'master'
    }

    cutoff_date = datetime.strptime(args.cutoff_date, '%Y-%m-%d')

    generate_dot(args.output_file, cutoff_date)

if __name__ == '__main__':
    main()
