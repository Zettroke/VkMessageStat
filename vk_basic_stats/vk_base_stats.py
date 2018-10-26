import itertools
import re
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import os
from vk_messages_stats import stats

print("template paths:", [os.path.join(stats.base_dir, 'vk_basic_stats/vk_base_templates'),
                                           os.path.join(stats.base_dir, 'vk_basic_stats')])

env = Environment(loader=FileSystemLoader([os.path.join(stats.base_dir, 'vk_basic_stats/vk_base_templates'),
                                           os.path.join(stats.base_dir, 'vk_basic_stats')]))
env.globals = stats.template_globals


def get_word_count(words):
    word_map = {}

    for word in words:
        word_map[word] = word_map.get(word, 0) + 1

    word_count = list(word_map.items())
    word_count.sort(key=lambda x: x[1], reverse=True)
    # pprint.pprint(word_count, indent=2)
    return word_count


@stats.stat_decorator(name="Частота слов", filename="word_count")
def stat_get_word_count():
    max_entrys = stats.settings['max_entry_on_page']

    word_count = get_word_count(stats.words)
    total_words = sum(map(lambda x: x[1], word_count[:max_entrys]))
    tags = []
    mlt = total_words / word_count[0][1]
    cnt = 0
    for wc in word_count:
        cnt += 1
        if cnt > max_entrys:
            break
        tags.append({'word': wc[0], 'count': wc[1], 'width': mlt * wc[1] / total_words * 100})

    res = env.get_template('word_count.html').render(data=tags)

    return res


@stats.stat_decorator(name="Частота слов у пользователей", filename="Word count by user")
def stat_get_word_count_by_user():
    max_entrys = stats.settings['max_entry_on_page']

    word_count1 = get_word_count(stats.words_user1)
    word_count2 = get_word_count(stats.words_user2)

    total_words1 = sum(map(lambda x: x[1], word_count1[:max_entrys]))
    total_words2 = sum(map(lambda x: x[1], word_count2[:max_entrys]))

    mlt1 = total_words1 / word_count1[0][1]
    mlt2 = total_words2 / word_count2[0][1]

    words1 = []
    words2 = []
    norm = max(total_words1, total_words2)

    cnt = 0
    for wc in word_count1:
        cnt += 1
        if cnt > max_entrys:
            break
        words1.append({'word': wc[0], 'count': wc[1], 'width': mlt1 * wc[1] / total_words1 * 100, 'normalized': str(round(wc[1]/total_words1*norm, 1))})

    cnt = 0
    for wc in word_count2:
        cnt += 1
        if cnt > max_entrys:
            break
        words2.append({'word': wc[0], 'count': wc[1], 'width': mlt2 * wc[1] / total_words2 * 100, 'normalized': str(round(wc[1]/total_words2*norm, 1))})

    return env.get_template("word_count_by_user.html").render(user1=words1, user2=words2)


@stats.stat_decorator(name="Частота слов у пользователей (сгруппированна по слову)", filename="Word count by user (group by word)")
def stat_get_word_count_by_user_group_by_word():
    max_entrys = stats.settings['max_entry_on_page']

    word_count1 = get_word_count(stats.words_user1)
    word_count2 = get_word_count(stats.words_user2)

    total_words = {}
    for w in word_count1:
        total_words[w[0]] = [w[1]]
    for w in word_count2:
        if w[0] in total_words.keys():
            total_words[w[0]] = total_words[w[0]] + [w[1]]
        else:
            total_words[w[0]] = [0, w[1]]
    for w in total_words.values():
        if len(w) < 2:
            w.append(0)
    wrds = list(total_words.items())
    wrds.sort(key=lambda x: sum(x[1]), reverse=True)

    total_words1 = sum(map(lambda x: x[1], word_count1[:max_entrys]))
    total_words2 = sum(map(lambda x: x[1], word_count2[:max_entrys]))

    mlt1 = total_words1 / word_count1[0][1]
    mlt2 = total_words2 / word_count2[0][1]

    words1 = []
    words2 = []
    cnt = 0
    norm = max(total_words1, total_words2)
    for wc in wrds:
        cnt += 1
        if cnt > max_entrys:
            break
        words1.append({'word': wc[0], 'count': wc[1][0], 'width': mlt1 * wc[1][0] / total_words1 * 100, 'normalized': str(round(wc[1][0]/total_words1*norm, 1))})
        words2.append({'word': wc[0], 'count': wc[1][1], 'width': mlt2 * wc[1][1] / total_words2 * 100, 'normalized': str(round(wc[1][1]/total_words2*norm, 1))})

    return env.get_template("word_count_by_user.html").render(user1=words1, user2=words2)


@stats.stat_decorator(name="Частота пар слов у пользователей", filename="Word pair count by user")
def stat_get_word_pair_count_by_user():
    max_entrys = stats.settings['max_entry_on_page']

    wcc = {}
    for t in stats.texts_user1:
        l_temp = list(map(stats.get_normalized_word, t.split()))
        for t in range(0, len(l_temp) - 1):
            s = ' '.join((l_temp[t], l_temp[t + 1]))
            wcc[s] = wcc.get(s, 0) + 1
    word_comb1 = sorted(wcc.items(), key=lambda x: x[1], reverse=True)[:max_entrys]

    wcc.clear()
    for t in stats.texts_user2:
        l_temp = list(map(stats.get_normalized_word, t.split()))
        for t in range(0, len(l_temp) - 1):
            s = ' '.join((l_temp[t], l_temp[t + 1]))
            wcc[s] = wcc.get(s, 0) + 1
    word_comb2 = sorted(wcc.items(), key=lambda x: x[1], reverse=True)[:max_entrys]

    total_comb1 = sum(map(lambda x: x[1], word_comb1))
    total_comb2 = sum(map(lambda x: x[1], word_comb1))

    mlt1 = total_comb1/word_comb1[0][1]
    mlt2 = total_comb2/word_comb2[0][1]

    res1, res2 = [], []
    for i in range(max_entrys):
        wc = word_comb1[i]
        res1.append({'word': wc[0], 'count': wc[1], 'width': mlt1 * wc[1] / total_comb1 * 100})

        wc = word_comb2[i]
        res2.append({'word': wc[0], 'count': wc[1], 'width': mlt2 * wc[1] / total_comb2 * 100})

    return env.get_template("word_count_by_user.html").render(user1=res1, user2=res2)


@stats.stat_decorator(name="График времени сообщений", filename="Message time graph")
def stat_message_time_graph():

    user1_list = [0]*24
    user2_list = [0]*24

    for msg in stats.message_list_user1:
        t = datetime.fromtimestamp(msg['date'])
        h = round(t.hour + t.minute/60 + t.second/3600) % 24
        user1_list[h] += 1

    for msg in stats.message_list_user2:
        t = datetime.fromtimestamp(msg['date'])
        h = round(t.hour + t.minute/60 + t.second/3600) % 24
        user2_list[h] += 1

    return env.get_template("message_time_graph.html").render(user1_list=user1_list, user2_list=user2_list)



