# ipmon
1 Первичная инициализация
mkdir /opt/ipmon
cd /opt/ipmon
cp *.py .
cp schema.sql .
python3 -c "from db import db; db.initialize()"
python3 cli.py config http_port 18080

2 Добавить узлы
python3 cli.py add Router 192.168.1.1 30
python3 cli.py add RDP-PC 192.168.1.100 60 TCP
python3 cli.py add WEB 192.168.1.10 30 TCP 443

3.1 Запуск вручную
python3 agent.py

3.2 Запуск как сервис
cp ipmon.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ipmon
stemctl start ipmon

4 Проверка
python3 cli.py config
python3 cli.py list
python3 cli.py summary
python3 cli.py events

http://SERVER:18080/
http://SERVER:18080/api/status
http://SERVER:18080/events

Перед внедрением я бы ещё рекомендовал исправить одну архитектурную проблему:
 сейчас при каждом обновлении узла agent.py открывает новое соединение SQLite
 через db.execute(). На десятках узлов это нормально, но на сотнях лучше держать
 одно соединение на поток и выполнять пакетные обновления. Это уже версия 2.1,
 но прирост производительности будет очень заметным.

5 Команды интерфейса
Добавить ICMP 
python3 cli.py add Router 192.168.1.1 30

Добавить TCP с портом по умолчанию 3389
python3 cli.py add RDP-PC 192.168.1.100 30 TCP

Добавить TCP с портом
python3 cli.py add WEB 192.168.1.10 30 TCP 443

Добавить описание и группу
python3 cli.py add PBX 192.168.1.5 30 ICMP --group Asterisk --desc "Main PBX"

Удалить
python3 cli.py del 192.168.1.10

Список
python3 cli.py list

Фильтрация
python3 cli.py list --group Asterisk

Поиск
python3 cli.py list --match PBX

Подробно
python3 cli.py list --detail

События
python3 cli.py events

Настройки
python3 cli.py config

Изменить порт HTTP
python3 cli.py config http_port 18080

Изменить количество потоков
python3 cli.py config max_workers 100

Экспорт
cli.py export report.csv
cli.py export-json report.json

Сводка по узлам монитора
cli.py summary

ipmon2/
+-- agent.py
+-- cli.py
+-- webui.py
+-- db.py
+-- schema.sql
+-- ipmon.service
+-- templates/
¦   +-- status.html
¦   L-- events.html
L-- README.md

Python 3.9+
SQLite WAL
ThreadPoolExecutor
ICMP
TCP (3389 по умолчанию)
встроенный HTTP-сервер
JSON API
группы
описания
экспорт CSV/JSON
PID lock
systemd unit
журнал событий
цветной HTML
