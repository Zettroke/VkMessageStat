from vk_messages_stats import stats
import requests
import os
import webbrowser
import sys
import traceback

from vk_basic_stats import vk_base_stats


def get_user_data():
    def get_access_token():
        print(
            '''
    Сейчас будет открыт браузер, где будет необходимо дать разрешение приложению VkMessageStat читать ваши сообщения.
    
    После того как разрешите доступ, вас перенаправить на другой адрес, где будет написано, о том что вы не должны копировать данные из адресной строки.
    Скопируйте данные из адресной строки :) и вставте в программу, после нажав Enter.
    
    -----------------------------------------------------------------
    Ключ доступа к вашему аккаунту храниться у вас же на компьютере, в файле access_token. Также как и сообщения.
    Программа их никуда не отправляет. 
    Вы можете в этом убедится посмотрев исходный код программы https://github.com/Zettroke/VkMessageStat
    Поэтому ваш аккаунт в полной безопасности
            ''')
        webbrowser.open("https://oauth.vk.com/authorize?client_id=6731752&scope=4096&response_type=token&v=5.87")
        s = input("Скопируйте сюда содержимое адресной строки браузера: ")
        if 'https://' in s:
            params = s.split('#')[1]
            pairs = params.split('&')
            for p in pairs:
                k, v = p.split('=')
                if k == 'access_token':
                    return v

    access_token = ''
    if os.path.exists('access_token'):
        access_token = open('access_token', 'r').read()
        r = requests.get(
            "https://api.vk.com/method/users.get?v=5.78&access_token={access_token}".format(access_token=access_token)
        )
        if 'response' not in r.json().keys():
            access_token = get_access_token()
            open('access_token', 'w').write(access_token)
    else:
        access_token = get_access_token()
        open('access_token', 'w').write(access_token)

    if not access_token:
        print("No access_token")
        exit(-1)

    requests.get("https://api.vk.com/method/stats.trackVisitor?access_token=" + access_token)

    if len(sys.argv) == 1:
        user_id = int(input('User_id: '))
    else:
        user_id = int(sys.argv[1])
    return access_token, user_id

try:

    access_token, user_id = get_user_data()
    history_file_name = "messages/messages.json"
    stat_libs = ['vk_basic_stats.vk_base_stats']

    out = open('out.txt', "w", encoding='utf-8')
    stats.make_stats(access_token, user_id, stat_libs)

    out.close()

    webbrowser.open('file:///' + os.path.abspath('result/result.html'))
    # p = input("Press any key to exit....")

except Exception as e:
    traceback.print_exception(tb=sys.exc_info()[2], etype=type(e), value=e)


# webbrowser.open('file:///' + os.path.abspath('result/result.html'))
