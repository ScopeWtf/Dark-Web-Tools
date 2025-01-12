import os
import requests
from bs4 import BeautifulSoup
import time
import re
import concurrent.futures


os.environ['LD_PRELOAD'] = '/usr/lib/x86_64-linux-gnu/torsocks/libtorsocks.so'

TOR_USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; rv:60.0) Gecko/20100101 Firefox/60.0"



onion_links_set = set()

def solve_captcha(url, session):
    global onion_links_set
    while True:
        try:
            session.headers.update({'User-Agent': TOR_USER_AGENT})

            response = session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            token = soup.find('input', {'name': '_token'})

            if not token:
                onion_link = extract_onion_link(response.text)
                if onion_link:
                    print(f"Extracted .onion link without captcha: {onion_link}")
                    onion_links_set.add(onion_link)
                return

            data = {
                '_token': token['value'],
                'pointer_event': 'on',
                'captcha_answer[1]': '4',
                'captcha_answer[2]': '2',
                'captcha_answer[3]': '3',
                'mirror_captcha_submit': ''
            }

            response = session.post(url, data=data)
            
            if "You failed to complete the captcha challenge, please try again!" in response.text:
                print(f"Captcha failed on {url}. Retrying...")
                time.sleep(1)
            elif "is now unlocked." in response.text:
                print(f"Captcha successfully solved on {url}")
                onion_link = extract_onion_link(response.text)
                if onion_link:
                    print(f"Extracted .onion link: {onion_link}")
                    onion_links_set.add(onion_link)
                break
            else:
                print(f"Captcha not solved on {url}. Retrying...")
                time.sleep(1)
        except Exception as e:
            print(f"Error solving captcha for {url}: {e}")
            time.sleep(1)
        finally:
            session.cookies.clear()

def extract_onion_link(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    mirror_url_div = soup.find('div', class_='mirror-url')
    if mirror_url_div:
        onion_link = mirror_url_div.text.strip()
        if onion_link.endswith('.onion'):
            return onion_link
    return None

def extract_unique_mirror_links(response):
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        mirror_links = set()
        for link in soup.find_all('a', href=re.compile(r'/mirror/[\w\d]+')):
            mirror_links.add(link['href'])
        return list(mirror_links)
    except Exception as e:
        print(f"Error extracting mirror links: {e}")
        return []

def save_links_to_file():
    global onion_links_set
    with open('onion_links.txt', 'w') as file:
        for link in onion_links_set:
            file.write(link + '\n')

def visit_and_solve_captchas(base_url):
    global onion_links_set
    while True:
        try:
            session = requests.Session()
            response = session.get(base_url)
            mirror_links = extract_unique_mirror_links(response)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(solve_captcha, f'https://daunt.link{link}', requests.Session()) for link in mirror_links]
                for future in concurrent.futures.as_completed(futures):
                    future.result()

            save_links_to_file()
            
            print("Waiting for 1 minute before re-checking for new mirror links...")
            time.sleep(60)
                
        except Exception as e:
            print(f"Error in visit_and_solve_captchas: {e}")

def main():
    base_url = 'https://daunt.link/view/Abacus'
    visit_and_solve_captchas(base_url)

if __name__ == "__main__":
    main()
