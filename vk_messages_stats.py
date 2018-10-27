import requests
import os
import json
import time
from importlib import import_module
from jinja2 import Environment, FileSystemLoader
import re
from threading import Thread, RLock, Lock
import sys
import itertools


class VkStats:
    message_list = []
    message_list_user1 = []
    message_list_user2 = []

    texts = []
    texts_user1 = []
    texts_user2 = []

    words = []
    words_user1 = []
    words_user2 = []

    user1_id = -1
    user1_name = ''
    user1_photo = ''

    user2_id = -1
    user2_name = ''
    user2_photo = ''

    template_globals = {}

    settings = {'max_entry_on_page': 2000}

    base_dir = '.'

    _stat_list = []
    _normalized_word_re = re.compile('[^a-zA-Zа-яА-Я]')

    _timer = 0

    def _post_progress(self, frac):
        print("{}%".format(frac*100))

    # can be replaced with another function
    def _post_message(self, message):
        print(message, end='')

    def post_message(self, message):
        self._timer = time.clock()
        self._post_message(">" + message)

    def done_message(self):
        delta = time.clock()-self._timer
        self._post_message('done in {:.3f}s\n'.format(round(delta, 3)))

    def get_normalized_word(self, word):
        """
            Нормализует слово: убирает все не буквы, заменяет Ё на Е, переводит в нижней регистр
        :param word:
        :return word: Возвращает нормализованное слово или пустую строку.
        """
        word = word.replace('ё', 'е').replace('Ё', 'Е')
        word = self._normalized_word_re.sub('', word)
        word = word.lower()
        return word

    def _get_messages(self, access_token, user_id, history_file_name):

        if history_file_name:
            ind = history_file_name.rfind('.')
            history_file_name = history_file_name[:ind] + str(user_id) + history_file_name[ind:]

        if history_file_name and os.path.exists(history_file_name):

            _msg("Found cached messages. Looking for new messages: ")

            msg_list = json.load(open(history_file_name, 'r', encoding='utf-8'), encoding='utf-8')
            start_id = msg_list[-1]['id']
            url = "https://api.vk.com/method/messages.getHistory?" +\
                  "v=5.78&user_id={user_id}&access_token={}&count={count}&start_message_id={start_message_id}&offset={offset}"
            r = requests.get(url.format(access_token, user_id=user_id, count=1, start_message_id=start_id, offset=0))
            js = r.json()
            if 'skipped' in js['response']:
                cnt = r.json()['response']['skipped']
                for offset in range(-200, -cnt, -200):
                    start = time.clock()

                    r = requests.get(url.format(access_token, user_id=user_id, count=200, start_message_id=start_id, offset=offset))
                    l = r.json()['response']['items']
                    l.reverse()
                    msg_list.extend(l)
                    # print('{}%'.format(round((min(-offset + 200, cnt)) / cnt * 100, 2)))

                    taken = time.clock() - start
                    if taken < 0.3:
                        time.sleep(0.4 - taken)
                n_cnt = cnt % 200
                offset = -cnt
                r = requests.get(url.format(access_token, user_id=user_id, count=n_cnt, start_message_id=start_id, offset=offset))
                l = r.json()['response']['items']
                l.reverse()
                msg_list.extend(l)
                try:
                    json.dump(msg_list, open(history_file_name, "w", encoding='utf-8'), ensure_ascii=False, indent=2)
                except Exception:
                    print("Can't cache messages")
            else:
                cnt = 0

            _done()
            _msg("Added {} messages\n".format(cnt))
            return msg_list

        else:
            print("Can't find cached messages. Downloading all messages:")
            start_all = time.clock()
            os.makedirs(os.path.split(history_file_name)[0], exist_ok=True)
            url = "https://api.vk.com/method/messages.getHistory?" \
                  "v=5.78&user_id={user_id}&access_token={}&count={count}&offset={offset}&rev=1"
            r = requests.get(url.format(access_token, user_id=user_id, offset=0, count=1))
            cnt = r.json()['response']['count']
            msg_list = []
            for offset in range(0, cnt+1, 200):
                start = time.clock()

                while True:
                    r = requests.get(url.format(access_token, user_id=user_id, offset=offset, count=200))
                    js = r.json()
                    if 'response' in js:
                        msg_list.extend(js['response']['items'])
                        self._post_progress(round((min(offset+200, cnt))/cnt, 2))
                        break
                    else:
                        print("error: {}".format(js['error']))
                        time.sleep(0.3)

                taken = time.clock() - start
                if taken < 0.4:
                    time.sleep(0.4-taken)
            if history_file_name:
                try:
                    json.dump(msg_list, open(history_file_name, "w", encoding='utf-8'), ensure_ascii=False, indent=2)
                except Exception:
                    print("Can't cache messages")
            _msg("Done in {}s.\n".format(round(time.clock()-start_all, 3)))
            _msg("Got {} messages.\n".format(len(msg_list)))
            return msg_list

    def stat_decorator(self, name="Stat name", filename=None):

        def dec(func):
            self._stat_list.append(
                {
                    "func": func,
                    'name': name,
                    'filename': filename.replace(' ', '_').lower() + ".html" if filename else name.replace(' ', '_').lower() + ".html"
                })
            return func

        return dec

    def _setup(self, access_token, user_id):
        _msg('Getting info about users: ')
        start = time.clock()

        url = "https://api.vk.com/method/users.get?v=5.78&access_token={access_token}&fields=photo_200".format(
            access_token=access_token)

        ans = requests.get(url).json()['response'][0]
        self.user1_id = ans['id']
        self.user1_name = ans['first_name'] + ' ' + ans['last_name']
        self.user1_photo = ans['photo_200']

        self.user2_id = user_id
        url = url + "&user_id=" + str(self.user2_id)
        ans = requests.get(url).json()['response'][0]
        self.user2_name = ans['first_name'] + ' ' + ans['last_name']
        self.user2_photo = ans['photo_200']

        self.template_globals['user1_name'] = self.user1_name
        self.template_globals['user2_name'] = self.user2_name
        self.template_globals['user1_photo'] = self.user1_photo
        self.template_globals['user2_photo'] = self.user2_photo

        _done()

        # message_stuff

        self.message_list = self._get_messages(access_token, user_id, "messages_cache/messages.json")

    def _prepare_data(self):
        _msg('Preparing basic data set: ')

        for msg in self.message_list:
            if msg['from_id'] == self.user1_id:
                self.message_list_user1.append(msg)
            if msg['from_id'] == self.user2_id:
                self.message_list_user2.append(msg)

        self.texts = list(map(lambda x: x['body'], self.message_list))
        self.texts_user1 = list(map(lambda x: x['body'], self.message_list_user1))
        self.texts_user2 = list(map(lambda x: x['body'], self.message_list_user2))

        for txts, res in ((self.texts, self.words), (self.texts_user1, self.words_user1), (self.texts_user2, self.words_user2)):
            for text in txts:
                for w in map(self.get_normalized_word, text.split()):
                    if w:
                        res.append(w)

        _done()

    def make_stats(self, access_token, user_id, stat_libs, result_folder='result',
                   post_message_func=None, post_progress_func=None, callback=None):

        if post_message_func:
            self._post_message = post_message_func
        if post_progress_func:
            self._post_progress = post_progress_func


        self._setup(access_token, user_id)

        start_time = time.clock()
        self._prepare_data()

        _msg("Generating main statistics: ")
        main_stat = self.main_stat()
        _done()

        for lib in stat_libs:
            import_module(lib)

        os.makedirs(os.path.join(result_folder, 'stat'), exist_ok=True)
        page_list = []

        for stat in self._stat_list:
            _msg('Running "{}" stat module: '.format(stat['name']))
            res = ''
            if stat['name'] == "График времени сообщений":
                pass
            res = stat['func']()
            if res:
                filename = stat['filename']
                n = os.path.join(result_folder, 'stat', filename)
                page_list.append({'name': stat['name'], 'link': os.path.join('stat', filename)})
                open(n, "w", encoding='utf-8').write(res)
            _done()

        env = Environment(loader=FileSystemLoader(os.path.join(self.base_dir, 'vk_basic_stats')))
        env.globals = self.template_globals

        res = env.get_template('main_template.html').render(
            {
                'stat_pages': page_list,
                'main_stat_list': main_stat['list'],
                'vars': main_stat
            })

        open(os.path.join(result_folder, 'result.html'), "w", encoding='utf-8').write(res)

        _msg("Statistics is done in {}s.\n".format(round(time.clock()-start_time, 3)))

        if callback:
            callback()

    def main_stat(self):
        ans = {}
        res = []

        # ------message_num-------
        res.append({
            'name': "Колчичество сообщений",
            'data': (len(self.message_list_user1), len(self.message_list), len(self.message_list_user2))
        })

        # ------word_num----------
        res.append({
            'name': "Колчичество слов",
            'data': (len(self.words_user1), len(self.words), len(self.words_user2))
        })

        # ------unique_word_num-----
        res.append({
            'name': "Колчичество уникальных слов",
            'data': (len(set(self.words_user1)), len(set(self.words)), len(set(self.words_user2)))
        })

        res.append({
            'name': "Колчичество букв",
            'data': (sum(map(len, self.words_user1)), sum(map(len, self.words)), sum(map(len, self.words_user2)))
        })

        res.append({
            'name': "Слов в сообщение (в среднем)",
            'data': (len(self.words_user1) / len(self.texts_user1), len(self.words) / len(self.texts),
                     len(self.words_user2) / len(self.texts_user2))
        })

        res.append({
            'name': "Уникальных слов в сообщение (в среднем)",
            'data': (
                len(set(self.words_user1))/len(self.texts_user1),
                len(set(self.words))/len(self.texts),
                len(set(self.words_user2))/len(self.texts_user2)
                     )
        })

        res.append({
            'name': "Средняя длинна слова",
            'data': (
                sum(map(len, self.words_user1))/len(self.words_user1),
                sum(map(len, self.words))/len(self.words),
                sum(map(len, self.words_user2))/len(self.words_user2))
        })

        worc_comp_count = []
        wcc = {}
        for texts in (self.texts_user1, self.texts, self.texts_user2):
            for i in texts:
                l_temp = list(map(self.get_normalized_word, i.split()))
                for i in range(0, len(l_temp)-1):
                    s = ' '.join((l_temp[i], l_temp[i+1]))
                    wcc[s] = wcc.get(s, 0) + 1

            worc_comp_count.append(max(wcc.items(), key=lambda x: x[1]))
            wcc.clear()

        res.append({
            'name': "Самое популярное сочетание из 2 слов",
            'data': (
                '{} ({})'.format(*worc_comp_count[0]),
                '{} ({})'.format(*worc_comp_count[1]),
                '{} ({})'.format(*worc_comp_count[2])
            )
        })

        cnt1 = 0
        for msg in self.message_list_user1:
            if "fwd_messages" in msg:
                cnt1 += len(msg["fwd_messages"])
        cnt2 = 0
        for msg in self.message_list_user2:
            if "fwd_messages" in msg:
                cnt2 += len(msg["fwd_messages"])

        res.append({
            'name': "Количество пересланных сообщений",
            'data': (
                cnt1,
                cnt1+cnt2,
                cnt2)
        })

        att_types = {"photo", 'video', 'audio', 'doc', 'audio_doc', 'audio_message', 'sticker'}
        u1_attach = {"photo": 0, 'video': 0, 'audio': 0, 'doc': 0, 'audio_doc': 0, 'sticker': 0}
        u2_attach = {"photo": 0, 'video': 0, 'audio': 0, 'doc': 0, 'audio_doc': 0, 'sticker': 0}
        cnts = []
        sticker_list = []
        sticker_links = {}
        for msg_list, attach_dict in ((self.message_list_user1, u1_attach), (self.message_list_user2, u2_attach)):
            cnt = 0
            stikers = {}
            for msg in msg_list:
                if "attachments" in msg:
                    cnt += len(msg["attachments"])
                    for att in msg['attachments']:
                        if att['type'] in att_types:
                            if att['type'] == 'doc':
                                if 'preview' in att['doc'] and 'audio_msg' in att['doc']['preview']:
                                    attach_dict['audio_doc'] += 1
                                else:
                                    attach_dict['doc'] += 1
                            elif att['type'] == 'audio_message':
                                attach_dict['audio_doc'] += 1
                            elif att['type'] == 'sticker':
                                attach_dict['sticker'] += 1
                                sticker_name = '_'.join([str(att['sticker']['product_id']), str(att['sticker']['sticker_id'])])
                                sticker_links[sticker_name] = att['sticker']['images_with_background'][2]['url']  # 256x256 image
                                stikers[sticker_name] = stikers.get(sticker_name, 0) + 1
                            else:
                                attach_dict[att['type']] += 1
            cnts.append(cnt)
            sticker_list.append(stikers)

        cnt1, cnt2 = cnts
        for msg in self.message_list_user2:
            if "attachments" in msg:
                cnt2 += len(msg["attachments"])

        res.append({
            'name': "Количество вложений",
            'data': (
                cnt1,
                cnt1 + cnt2,
                cnt2
            ),
            'attachments': True
        })
        ans['attach_graph_data'] = {
            'user1': u1_attach,
            'user2': u2_attach
        }

        # stickers
        res.append({
            'name': "Самый популярный стикер",
            'stickers': True,
            'user1_sticker': sticker_links[max(sticker_list[0].items(), key=lambda x: x[1])[0]],
            'user2_sticker': sticker_links[max(sticker_list[1].items(), key=lambda x: x[1])[0]]
        })

        for i in res:
            if 'data' in i:
                i['data'] = [round(x, 3) if type(x) == float else x for x in i['data']]

        ans['list'] = res

        return ans


stats = VkStats()

if getattr(sys, 'frozen', False):
    stats.base_dir = sys._MEIPASS
else:
    stats.base_dir = os.path.dirname(os.path.abspath(__file__))


# shortcut
def _msg(message):
    stats.post_message(message)


# shortcut
def _done():
    stats.done_message()