import re
import typing
import regex
from datetime import datetime
import os
import requests
import zipfile
from urllib.parse import urlparse


def get_url_file_name(url: str) -> str:
    parsed_url = urlparse(url)
    path = parsed_url.path
    filename = path[path.rfind('/') + 1:]
    return filename


def download_file_if_not_exists(url: str, local_filename: str) -> None:
    if not os.path.isfile(local_filename):
        print(f'Downloading {url} ...', end='')
        response = requests.get(url)
        if response.status_code == 200:
            with open(local_filename, 'wb') as f:
                f.write(response.content)
            print(f'Done.')
        else:
            raise RuntimeError(f'Failed to download {url}. Status code: {response.status_code}')
    else:
        print(f'{local_filename} already exists.')


def traverse_nesting(kana: str, kanji: str, tail: str, line: str, file: typing.TextIO) -> None:
    splitter = ', '
    kana_list = kana.split(splitter)
    kanji_list = kanji.split(splitter)
    kana_length = len(kana_list)
    kanji_length = len(kanji_list)
    if kana_length > 1 and kanji_length > 1 and kana_length != kanji_length:
        raise RuntimeError('Nesting error: ' + line)
    if kana_length >= kanji_length:
        for i in range(kana_length):
            traverse_reading(kana_list[i], kanji_list[i if i < kanji_length else kanji_length - 1], tail, line, file)
    else:
        for i in range(kanji_length):
            traverse_reading(kana_list[i if i < kana_length else kana_length - 1], kanji_list[i], tail, line, file)


def traverse_reading(kana: str, kanji: str, tail: str, line: str, file: typing.TextIO) -> None:
    splitter = '･'
    kana_list = kana.split(splitter)
    kanji_list = kanji.split(splitter)
    kana_length = len(kana_list)
    kanji_length = len(kanji_list)
    if kana_length > 1 and kanji_length > 1 and kana_length != kanji_length:
        raise RuntimeError('Nesting reading error: ' + line)
    if kana_length >= kanji_length:
        for i in range(kana_length):
            process_word(kana_list[i], kanji_list[i if i < kanji_length else kanji_length - 1], tail, line, file)
    else:
        for i in range(kanji_length):
            process_word(kana_list[i if i < kana_length else kana_length - 1], kanji_list[i], tail, line, file)


def process_word(kana: str, kanji: str, tail: str, line: str, file: typing.TextIO) -> None:
    kana = kana.strip()
    kanji = kanji.strip()

    if is_japanese(kana):
        kana = remove_i(kana)
    if is_japanese(kanji):
        kanji = remove_i(kanji)

    prefix = kana.endswith('…') or kanji.endswith('…')
    suffix = kana.startswith('…') or kanji.startswith('…')
    if prefix and suffix:
        marker = '<инфикс>'
    elif prefix:
        marker = '<префикс>'
    elif suffix:
        marker = '<суффикс>'
    else:
        marker = ''
    tail = re.sub(r'(%MARKER%)', marker, tail)

    kana = remove_ellipsis(kana)
    kanji = remove_ellipsis(kanji)
    if kana == '':
        raise RuntimeError(f'No kana: [{kanji}]: {line}')

    if kanji == '':
        file.write(f'{kana} /{tail}\n')
    else:
        file.write(f'{kanji} [{kana}] /{tail}\n')


def is_japanese(word: str) -> bool:
    if regex.search(r'\p{Hiragana}', word):
        return True  # is hiragana
    if regex.search(r'\p{Katakana}', word):
        return True  # is katakana
    if regex.search(r'\p{Han}', word):
        return True  # is kanji
    return False


def remove_i(word: str) -> str:
    rv = re.sub(r'I+$', '', word)
    # if rv != word:
    #     print(f'{word} -> {rv}')
    return rv


def remove_ellipsis(word: str) -> str:
    rv = word.replace('…', '')
    # if rv != word:
    #     print(f'{word} -> {rv}')
    return rv


def format_number_1(s: str) -> str:
    pattern = r'^(\d+)\.'
    match = re.match(pattern, s)
    if match:
        number = match.group(1)
        return '{' + number + '}' + s[len(number) + 1:]
    else:
        return s


def format_number_2(s: str) -> str:
    pattern = r'^(\d+)\)'
    match = re.match(pattern, s)
    if match:
        number = match.group(1)
        return '(' + number + ')' + s[len(number) + 1:]
    else:
        return s


def main():
    url = 'https://www.warodai.ru/download/warodai_txt.zip'
    file_name = get_url_file_name(url)
    download_file_if_not_exists(url, file_name)
    print('Extracting...', end='')
    with zipfile.ZipFile(file_name, 'r') as zip_ref:
        zip_ref.extractall('.')
    print('Done.')

    # read input Warodai file
    with open('warodai.txt', 'r', encoding='utf-16-le') as infile:
        record_list = infile.read().split('\n\n')

    print('Converting, please wait...')
    # format output EDICT file
    with open('output.txt', 'w', encoding='utf-8') as outfile:
        for r, record in enumerate(record_list):
            if r == 0:
                now = datetime.today().strftime("%Y.%m.%d")
                outfile.write(f'　？？？ /EDICT, WARODAI Japanese-Russian Electronic Dictionary/Created: {now}/\n')
                continue
            line_list = record.split('\n')

            # часть кана+кандзи и остаточный хвост
            match_kana = re.match(r'^(.+)\(', line_list[0])
            if not match_kana:
                raise RuntimeError('No kanakanji part: ' + line_list[0])
            kanakanji_part = match_kana.group(1)
            tail_part = line_list[0][len(kanakanji_part):]

            # части кана и кандзи
            kanji_part = ''
            match_kanji = re.search(r'【(.+)】', line_list[0])
            if match_kanji:
                kanji_part = match_kanji.group(1)
                match_kana = re.match(r'^(.+)【', line_list[0])
                if not match_kana:
                    raise RuntimeError('No kana part: ' + line_list[0])
                kana_part = match_kana.group(1)
            else:
                kana_part = kanakanji_part

            # определение слова
            definition = f'{tail_part}%MARKER%'
            for i, line in enumerate(line_list):
                if i == 0:
                    continue
                # Чистка строк...
                # главные номера 1.
                line = format_number_1(line)
                # второстепенные номера 1)
                line = format_number_2(line)
                # теги
                line = line.replace('<i>', '(').replace('</i>', ')')
                line = line.replace('<a href="', '〔').replace('">', ' ').replace('</a>', '〕')
                # точки в конце
                line = re.sub(r'\.$', '', line)
                # скобки которые стирает TA
                line = line.replace('【', '[').replace('】', ']')
                definition += line + '/'

            # гнездование
            traverse_nesting(kana_part, kanji_part, definition, line_list[0], outfile)
    print('-> output.txt (utf-8)\nDone.')


if __name__ == '__main__':
    main()
