import re
import orjson
import string
import unicodedata
from bs4 import BeautifulSoup

PUNCTUATION_TRANSLATOR = str.maketrans('', '', string.punctuation)

def create_json_file(path_file: str, data: dict):
    with open(path_file, mode="wb") as f:
        f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))


def clean_text(text: str) -> str:
    cleaned_text = text.strip().translate(PUNCTUATION_TRANSLATOR).lower()
    return re.sub(r'[^a-zа-яё0-9]+', '', cleaned_text)


def get_clean_sorted_text_list(text: str):
    cleaned_text = text.strip().translate(PUNCTUATION_TRANSLATOR).lower()
    text_list = cleaned_text.split(' ')
    while '' in text_list:
        text_list.remove('')
    text_list.sort()
    return text_list

def get_file_type(extension: str) -> str:
    if extension in ('jpg', 'jpeg', 'png'):
        file_type = 'photo'
    elif extension in ('mov', 'mp4'):
        file_type = 'video'
    elif extension in ('mp3', 'ogg', 'wav', 'aac'):
        file_type = 'audio'
    else:
        file_type = 'document'
    return file_type




def clean_from_html(text: str) -> str:
    allowed_tags = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "span", "tg-spoiler",
                    "code", "pre", "a"}
    allowed_attrs = {"href"}


    soup = BeautifulSoup(text, "html.parser")

    for tag in soup.find_all():
        if tag.name not in allowed_tags:
            tag.unwrap()
        else:
            attrs = {key: value for key, value in tag.attrs.items() if key in allowed_attrs}
            tag.attrs = attrs

    cleaned_text = str(soup)
    cleaned_text = unicodedata.normalize("NFKC", cleaned_text).replace("\xa0", " ")

    return cleaned_text


def clean_from_html_v2(text: str) -> str:
    allowed_tags = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "span", "tg-spoiler",
                    "code", "pre", "a"}
    allowed_attrs = {"href"}

    soup = BeautifulSoup(text, "html.parser")

    for br in soup.find_all("br"):
        br.replace_with("\n")

    for tag in soup.find_all():
        if tag.name not in allowed_tags:
            tag.unwrap()
        else:
            tag.attrs = {key: value for key, value in tag.attrs.items() if key in allowed_attrs}

    cleaned_text = str(soup)

    cleaned_text = unicodedata.normalize("NFKC", cleaned_text)
    cleaned_text = cleaned_text.replace("\xa0", " ")
    cleaned_text = cleaned_text.replace("\r", " ").replace("\t", " ")
    cleaned_text = " ".join(cleaned_text.split())

    return cleaned_text


def clean_from_html_v3(text: str) -> str:
    allowed_tags = {
        "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
        "span", "tg-spoiler", "code", "pre", "a"
    }
    allowed_attrs = {"href"}

    soup = BeautifulSoup(text, "html.parser")

    for br in soup.find_all("br"):
        br.replace_with("\n")

    for tag in soup.find_all():
        if tag.name not in allowed_tags:
            tag.unwrap()
        else:
            tag.attrs = {key: value for key, value in tag.attrs.items() if key in allowed_attrs}

    cleaned_text = str(soup)

    cleaned_text = unicodedata.normalize("NFKC", cleaned_text)
    cleaned_text = cleaned_text.replace("\xa0", " ")  # неразрывный пробел

    return cleaned_text


