import os
import re
import zlib
import argparse
from datetime import datetime


def parse_object(object_hash, description=None):
    """
    Извлечь информацию из git-объекта по его хэшу.
    Каждый объект после разжатия выглядит так:
    ┌────────────────────────────────────────────────────────┐
    │ {тип объекта} {размер объекта}\x00{содержимое объекта} │
    └────────────────────────────────────────────────────────┘
    Содержимое объекта имеет разную структуру в зависимости от типа
    """

    # Полный путь к объекту по его хэшу
    object_path = os.path.join(config['repo_path'], '.git', 'objects', object_hash[:2], object_hash[2:])

    # Открываем git-объект
    with open(object_path, 'rb') as file:
        # Разжали объект, получили его сырое содержимое
        raw_object_content = zlib.decompress(file.read())
        # Разделили содержимое объекта на заголовок и основную часть
        header, raw_object_body = raw_object_content.split(b'\x00', maxsplit=1)
        # Извлекли из заголовка информацию о типе объекта и его размере
        object_type, content_size = header.decode().split(' ')

        # Словарь с данными git-объекта:
        # {
        #   'label': текстовая метка, которая будет отображаться на графе
        #   'children': список из детей этого узла (зависимых объектов)
        # }
        object_dict = {}


        # В зависимости от типа объекта используем разные функции для его разбора
        if object_type == 'commit':
            object_dict['label'] = 'commit/' + get_msg(raw_object_body)
            object_dict['children'] = parse_commit(raw_object_body)
            object_dict['hash'] = object_hash[:6]
            object_dict['message'] = get_msg(raw_object_body)
            object_dict['date'] = get_date(raw_object_body)

        elif object_type == 'tree':
            object_dict['label'] = r'[tree]\n' + object_hash[:6]
            object_dict['children'] = parse_tree(raw_object_body)

        elif object_type == 'blob':
            object_dict['label'] = r'[blob]\n' + object_hash[:6]
            object_dict['children'] = []

        # Добавляем дополнительную информацию, если она была
        #if description is not None:
        #   object_dict['label'] += r'\n' + description
        return object_dict


def parse_tree(raw_content):
    """
    Парсим git-объект дерева, который состоит из следующих строк:
    ┌─────────────────────────────────────────────────────────────────┐
    │ {режим} {имя объекта}\x00{хэш объекта в байтовом представлении} │
    │ {режим} {имя объекта}\x00{хэш объекта в байтовом представлении} │
    │ ...                                                             │
    │ {режим} {имя объекта}\x00{хэш объекта в байтовом представлении} │
    └─────────────────────────────────────────────────────────────────┘
    """

    # Дети дерева (соответствующие строкам объекта)
    children = []

    # Парсим данные, последовательно извлекая информацию из каждой строки
    rest = raw_content
    while rest:
        # Извлечение режима
        mode, rest = rest.split(b' ', maxsplit=1)
        # Извлечение имени объекта
        name, rest = rest.split(b'\x00', maxsplit=1)
        # Извлечение хэша объекта и его преобразование в 16ричный формат
        sha1, rest = rest[:20].hex(), rest[20:]
        # Добавляем потомка к списку детей
        children.append(parse_object(sha1, description=name.decode()))

    return children



def get_msg(raw_content):

    # Переводим raw_content в кодировку UTF-8 (до этого он был последовательностью байтов)
    content = raw_content.decode()
    # Делим контент на строки
    content_lines = content.split('\n')

    # Словарь с содержимым коммита
    commit_data = {}

    # Извлекаем хэш объекта дерева, привязанного к коммиту
    commit_data['tree'] = content_lines[0].split()[1]
    content_lines = content_lines[1:]

    # Список родительских коммитов
    commit_data['parents'] = []
    # Парсим всех родителей, сколько бы их ни было
    while content_lines[0].startswith('parent'):
        commit_data['parents'].append(content_lines[0].split()[1])
        content_lines = content_lines[1:]

    # Извлекаем информацию об авторе и коммитере
    while content_lines[0].strip():
        key, *values = content_lines[0].split()
        commit_data[key] = ' '.join(values)
        content_lines = content_lines[1:]

    # Извлекаем сообщение к комиту
    commit_data['message'] = '\n'.join(content_lines[1:]).strip()

    return commit_data['message']


def get_date(raw_content):

    # Переводим raw_content в кодировку UTF-8 (до этого он был последовательностью байтов)
    content = raw_content.decode()
    # Делим контент на строки
    content_lines = content.split('\n')

    # Словарь с содержимым коммита
    commit_data = {}

    # Извлекаем хэш объекта дерева, привязанного к коммиту
    commit_data['tree'] = content_lines[0].split()[1]
    content_lines = content_lines[1:]

    # Список родительских коммитов
    commit_data['parents'] = []
    # Парсим всех родителей, сколько бы их ни было
    while content_lines[0].startswith('parent'):
        commit_data['parents'].append(content_lines[0].split()[1])
        content_lines = content_lines[1:]

    # Извлекаем информацию об авторе и коммитере
    while content_lines[0].strip():
        key, *values = content_lines[0].split()
        commit_data[key] = ' '.join(values)
        content_lines = content_lines[1:]

    # Извлекаем сообщение к комиту
    commit_data['message'] = '\n'.join(content_lines[1:]).strip()

    return commit_data['committer']


def parse_commit(raw_content):
    # Переводим raw_content в кодировку UTF-8 (до этого он был последовательностью байтов)
    content = raw_content.decode()
    # Делим контент на строки
    content_lines = content.split('\n')

    # Словарь с содержимым коммита
    commit_data = {}

    # Извлекаем хэш объекта дерева, привязанного к коммиту
    commit_data['tree'] = content_lines[0].split()[1]
    content_lines = content_lines[1:]

    # Список родительских коммитов
    commit_data['parents'] = []
    # Парсим всех родителей, сколько бы их ни было
    while content_lines[0].startswith('parent'):
        commit_data['parents'].append(content_lines[0].split()[1])
        content_lines = content_lines[1:]

    # Извлекаем информацию об авторе и коммитере
    while content_lines[0].strip():
        key, *values = content_lines[0].split()
        commit_data[key] = ' '.join(values)
        content_lines = content_lines[1:]

    # Извлекаем сообщение к комиту
    commit_data['message'] = '\n'.join(content_lines[1:]).strip()

    # Возвращаем все зависимости объекта коммита (то есть его дерево и всех родителей)
    return [parse_object(commit_data['tree'])] + \
        [parse_object(parent) for parent in commit_data['parents']]


def get_last_commit():
    """Получить хэш для последнего коммита в ветке"""
    head_path = os.path.join(config['repo_path'], '.git', 'refs', 'heads', config['branch'])
    with open(head_path, 'r') as file:
        return file.read().strip()


def extract_unix_time(input_string):
    # Регулярное выражение для поиска времени в строке
    match = re.search(r'(\d{10})\s([+-]\d{4})', input_string)
    if match:
        unix_time = int(match.group(1))  # Извлекаем unix time
        # Преобразуем unix time в datetime
        dt = datetime.fromtimestamp(unix_time)
        return dt
    else:
        return None


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
        written_edges = set()  # Множество для отслеживания записанных рёбер
        recursive_write(file, tree, written_edges)
        file.write('}')



def main():
    parser = argparse.ArgumentParser(description='Генерация графа зависимостей для git-репозитория.')
    parser.add_argument('repo_path', help='Путь к анализируемому репозиторию')
    parser.add_argument('output_file', help='Путь к файлу-результату в виде кода')
    parser.add_argument('cutoff_date', help='Дата коммитов в формате YYYY-MM-DD')

    args = parser.parse_args()

    # Загрузка конфигурации
    global config
    config = {
        'repo_path': args.repo_path,
        'branch': 'master'
    }

    # Преобразование строки даты в объект datetime
    cutoff_date = datetime.strptime(args.cutoff_date, '%Y-%m-%d')

    # Генерация графа
    generate_dot(args.output_file, cutoff_date)

if __name__ == '__main__':
    main()
# dot -Tpng graph.dot -o graph.png