import json
import requests
import pandas as pd
import numpy as np
import time as time_lb



feeds_standings = ['-']
names_standings = ['-']
ready_league_count = 1

def read_st_and_teams():
    """
    Обновляет списки feeds_standings, names_standings и переменную ready_league_count
    """
    global feeds_standings, names_standings, ready_league_count
    ready_league_count = len(names_standings)
    df_st = pd.read_excel('all_standings.xlsx')
    feeds_standings = df_st['feed_st']
    names_standings = df_st['name_st']

read_st_and_teams()



def get_data(feed):
    """
    Получает данные с Flashscore API и парсит их из кастомного формата.
    :param feed: Идентификатор данных
    :return: list[dict]: Список словарей с данными
    """

    bl_res = False
    response = None
    max_attempts = 20
    attempt = 0
    while not bl_res:

        sleep_time = np.random.randint(2, 6)
        time_lb.sleep(sleep_time)
        url = f'https://global.flashscore.ninja/2/x/feed/{feed}'

        try:
            response = requests.get(url=url, headers={"x-fsign": "SW9D1eZo"})
            bl_res = True
        except:
            if attempt > max_attempts:
                print('что-то не так, проверьте подключение или впн')
            attempt += 1
            # print('произошла ошибка, но все збс')


    data = response.text.split('¬')

    data_list = [{}]

    for item in data:
        key = item.split('÷')[0]
        value = item.split('÷')[-1]

        if '~' in key:
            data_list.append({key: value})
        else:
            data_list[-1].update({key: value})

    return data_list




def get_all_feeds(num):
    """
    Собирает feed-ы всех игр футбольной лиги на сайте flashscore и сохраняет их в excel-файл. Но игнорирует игры с участием команд игравшими более чем 40 сезонов назад
    :param num: индекс лиги в excel-файле all_standings
    """

    def get_response(url_):
        """
        Возвращает ответ от сервера по url. Используется для получения http или json файлов с flashscore api
        :param url_: Url для запроса
        :return: Response object
        """
        response_ = None
        bl_ = True
        while bl_:
            sleep_time = np.random.randint(2, 6)
            time_lb.sleep(sleep_time)
            try:
                response_ = requests.get(url_, headers={"x-fsign": "SW9D1eZo"})
                bl_ = False
            except:
                pass
        return response_


    # перебираем все feed-ы лиг и по ним находим все feed-ы прошлых сезонов этих лиг
    standings = []
    feed_standings = feeds_standings[num]
    feed1 = feed_standings.split('_')[1]
    feed2 = feed_standings.split('_')[2]


    url = 'https://2.ds.lsapp.eu/pq_graphql?_hash=lph&tournamentId=' + feed1 + '&tournamentStageId=' + feed2 + '&projectId=2' # для каждой лиги запрашиваем json-файл с информацией об старых сезонах
    response = get_response(url)
    data = response.json()
    data = data.get('data').get('getTournamentSeasons')
    data = data.get('other')

    for el in data: # убрав все лишнее, вытаскиваем составные части feed-а лиги и собираем из него сам feed
        feed1_ = el.get('tournamentId')
        feed2_ = el.get('tournamentStages').get('other')[0].get('id')
        feed_standings_ = 'to_' + feed1_ + '_' + feed2_ + '_'
        standings.append(feed_standings_)


    print(names_standings[num] + ' finish get st feeds')

    # сбираем все команды сезонов из списка standings
    teams = []
    urls_teams = []
    for st in standings:
        if standings.index(st) > 40: # матчи с играми команд игравшими в лиге более чем 40 сезонов назад игнорируем
            break
        data_list = get_data(st + '1') # по feed-у лиги собираем названия команд и ссылки на них
        for el in data_list:
            if '~TR' in el.keys():
                team = el.get('TN')
                url_t = el.get('TIU')
                if team not in teams:
                    teams.append(team)
                    urls_teams.append(url_t)

    print('teams: ', teams)



    feeds_match = {} # для каждой команды мы в этом словаре запишем список feed-ов ее игр
    for i in range(len(urls_teams) - 1): # перебираем команды(ссылки на них)
        for j in range(i + 1, len(urls_teams)):

            url_team_1 = urls_teams[i][6:-1].replace('/', '-')
            url_team_2 = urls_teams[j][6:-1].replace('/', '-')


            url = f'https://www.flashscore.com/match/football/{url_team_1}/{url_team_2}/?' # составляем ссылку на матч и вычленяем в полученном html файле feed этого матча
            response = get_response(url)

            data = response.text.split('<script>\n    ')

            feed_match = None # вытягиваем feed матча
            for el in data:
                if 'window.environment = {"event_id_c":' in el:
                    feed_match = el[36:44]
                    break

            if feed_match is None:
                continue

            data = get_data('df_hh_1_' + feed_match)

            for el in data[105:]: # проходимся по всем совместным играм этих команд
                if '~KA' in el.keys() and el.get('KF') != names_standings[num].split(' ')[-1].replace('_', ' '):
                    break
                team1 = el.get('FH')
                team2 = el.get('FK')
                time = int(el.get('~KC'))
                feed = el.get('KP')

                for team in [team1, team2]: # и заносим их в словарь (время и feed)
                    if team not in feeds_match.keys():
                        feeds_match |= {team : [[time, feed]]}
                    else:
                        feeds_match[team].append([time, feed])

            # print(teams[i], teams[j])

    for team in feeds_match.keys():  # проходимся по всем столбцам
        list_ = feeds_match[team]
        # print(list_)

        list_.sort(reverse=True)  # сортируем по датам

        for i in range(len(list_)):  # и стираем даты
            list_[i] = list_[i][1]
        feeds_match[team] = list_

    max_l = 0
    for el in feeds_match:  # равняем словарь, что бы переконвертировать в Dataframe, а затем в excel-таблицу
        if max_l < len(feeds_match[el]):
            max_l = len(feeds_match[el])
    for el in feeds_match:
        feeds_match[el] += [float('nan')] * (max_l - len(feeds_match[el]))

    df = pd.DataFrame(feeds_match) # сохраняем таблицу
    df.to_excel('all_feeds_qwerty' + names_standings[num].replace(' ', '_') + '.xlsx', index=False)
    print(names_standings[num] + ' finish get_feeds_match\n')

for i in range(ready_league_count):
    get_all_feeds(0)
