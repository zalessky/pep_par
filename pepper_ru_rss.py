import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import time
import os
import datetime

# Настройки
BASE_URL = "https://www.pepper.ru/new"
INTERVAL = 1  # интервал в минутах
NUM_ENTRIES = 50  # количество записей в фиде
MAX_PAGES = 20  # Увеличенное максимальное количество страниц
RSS_FILE = "pepper_ru_rss.xml"  # файл для RSS-фида

# Селекторы
SELECTOR_ARTICLE = "article.deal-card"
SELECTOR_TITLE = ".custom-card-title a"
SELECTOR_DESCRIPTION = 'div[class*="md:text-sm"]'
SELECTOR_AUTHOR = 'div[class*="text-sm"].text-primary-text-light'
SELECTOR_IMAGE = 'img[src*="cdn"]'

def get_entries(soup):
    entries = []
    for article in soup.find_all("article", class_="deal-card"):
        try:
            title_link = article.find("a", class_="group-hover:!text-primary")
            title = title_link.text.strip() if title_link else ""
            link = title_link["href"] if title_link else ""

            description = article.find("div", class_=lambda x: x and "md:text-sm" in x).text.strip() if article.find("div", class_=lambda x: x and "md:text-sm" in x) else ""

            author_element = article.find("div", class_=lambda x: x and "text-sm" in x and "text-primary-text-light" in x)
            author = author_element.text.strip() if author_element else ""

            img_element = article.find("img", src=lambda x: x and x.startswith("https://cdn"))
            image = img_element["src"] if img_element else ""

            if title and link:
                entries.append({
                    'title': title,
                    'link': link,
                    'description': description,
                    'author': author,
                    'image': image
                })
        except (AttributeError, KeyError, TypeError) as e:
            print(f"Ошибка парсинга элемента: {e}")
            continue
    return entries

def fetch_all_entries(base_url):
    all_entries = []
    page_num = 1
    while len(all_entries) < NUM_ENTRIES and page_num <= MAX_PAGES:
        url = base_url if page_num == 1 else f"{base_url}?page={page_num}"
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status() #Проверка на ошибки HTTP (4xx или 5xx)
            soup = BeautifulSoup(response.content, 'html.parser')
            entries = get_entries(soup)
            if entries is None:
                print(f"\033[91mНе удалось найти данные на странице {page_num}\033[0m")
                break
            added_entries = 0
            for entry in entries:
                if len(all_entries) < NUM_ENTRIES:
                    all_entries.append(entry)
                    added_entries += 1
            print(f"\033[92mОбработана страница {page_num}: добавлено {added_entries} записей\033[0m")
            page_num += 1
        except requests.exceptions.RequestException as e:
            print(f"\033[91mОшибка HTTP-запроса на странице {page_num}: {e}\033[0m")
            break
        except AttributeError as e:
            print(f"\033[91mОшибка парсинга на странице {page_num}: {e}\033[0m")
            break
        except Exception as e:
            print(f"\033[91mПроизошла другая ошибка на странице {page_num}: {e}\033[0m")
            break

    return all_entries[:NUM_ENTRIES]

def fetch_first_page(base_url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status() #Проверка на ошибки HTTP (4xx или 5xx)
        soup = BeautifulSoup(response.content, 'html.parser')
        entries = get_entries(soup)
        return entries
    except requests.exceptions.RequestException as e:
        print(f"Ошибка HTTP-запроса на первой странице: {e}")
    except AttributeError as e:
        print(f"Ошибка парсинга на первой странице: {e}")
    except Exception as e:
        print(f"Произошла другая ошибка на первой странице: {e}")

def generate_rss(entries):
    fg = FeedGenerator()
    fg.title('Pepper.ru')
    fg.link(href=BASE_URL)
    fg.description('Новости с Pepper.ru')

    for entry in entries:
        fe = fg.add_entry()
        fe.title(entry['title'])
        fe.link(href=entry['link'])
        fe.description(entry['description'])
        fe.author({'name': entry['author']})
        now = datetime.datetime.now()
        fe.pubDate(now.strftime('%a, %d %b %Y %H:%M:%S GMT'))
        fe.guid(entry['link'])
        fe.enclosure(url=entry['image'], type='image/jpeg')

    return fg.rss_str(pretty=True).decode('utf-8')

def main():
    while True:
        try:
            first_page_entries = fetch_first_page(BASE_URL)
            if first_page_entries:
                if os.path.exists(RSS_FILE):
                    with open(RSS_FILE, 'r', encoding='utf-8') as f:
                        old_rss = f.read()
                        old_entries = []
                        try:
                            old_soup = BeautifulSoup(old_rss, 'xml')
                            for item in old_soup.find_all('item'):
                                old_entries.append(item.find('title').text)
                        except Exception as e:
                            print(f"\033[91mОшибка при разборе старого RSS: {e}\033[0m")
                    if len(first_page_entries) > 0:
                        new_first_title = first_page_entries[0]['title']
                        if new_first_title not in old_entries:
                            print("\033[93mОбнаружены изменения. Обрабатываю все страницы...\033[0m")
                            all_entries = fetch_all_entries(BASE_URL)
                            rss = generate_rss(all_entries)
                            with open(RSS_FILE, 'w', encoding='utf-8') as f:
                                f.write(rss)
                            print("\033[92mRSS-фид успешно обновлен.\033[0m")
                        else:
                            print("\033[94mИзменений не обнаружено.\033[0m")
                else:
                    print("\033[93mRSS-фид не существует. Обрабатываю все страницы...\033[0m")
                    all_entries = fetch_all_entries(BASE_URL)
                    rss = generate_rss(all_entries)
                    with open(RSS_FILE, 'w', encoding='utf-8') as f:
                        f.write(rss)
                    print("\033[92mRSS-фид создан.\033[0m")
            else:
                print("\033[91mНе удалось получить первую страницу.\033[0m")
        except requests.exceptions.RequestException as e:
            print(f"\033[91mОшибка HTTP-запроса: {e}\033[0m")
        except Exception as e:
            print(f"\033[91mПроизошла ошибка: {e}\033[0m")
        finally:
            time.sleep(INTERVAL * 60)

if __name__ == '__main__':
    main()
