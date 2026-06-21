#!/usr/bin/env python3
import csv
import json
import sys
from datetime import datetime
from db import db
from constants import (
    CHECK_ICMP,
    CHECK_TCP,
    DEFAULT_TCP_PORT,
    availability,
    tier,
    state_to_text
)
def usage():
    print("""
Commands:
add NAME IP INTERVAL [ICMP|TCP] [PORT]
del IP
list
list --detail
list --group GROUP
events
summary
config
config KEY VALUE
export FILE.csv
export-json FILE.json
""")
#
# ADD
#
def cmd_add():
    if len(sys.argv) < 5:
        usage()
        return
    name = sys.argv[2]
    ip = sys.argv[3]
    interval = int(sys.argv[4])
    check_type = CHECK_ICMP
    port = None
    if len(sys.argv) >= 6:
        check_type = sys.argv[5].upper()
    if check_type == CHECK_TCP:
        if len(sys.argv) >= 7:
            port = int(sys.argv[6])
        else:
            port = DEFAULT_TCP_PORT
    db.execute("""
        INSERT INTO hosts(
            name,
            ip,
            interval,
            check_type,
            port
        )
        VALUES(
            ?,?,?,?,?
        )
    """,
    (
        name,
        ip,
        interval,
        check_type,
        port
    ))
    print("Added")
#
# DEL
#
def cmd_del():
    db.execute(
        "DELETE FROM hosts WHERE ip=?",
        (sys.argv[2],)
    )
    print("Deleted")
#
# LIST
#
def cmd_list():
    detail = "--detail" in sys.argv
    group = None
    if "--group" in sys.argv:
        idx = sys.argv.index(
            "--group"
        )
        group = sys.argv[idx + 1]
    sql = """
    SELECT *
    FROM hosts
    """
    params = ()
    if group:
        sql += """
        WHERE group_name=?
        """
        params = (group,)
    sql += """
    ORDER BY name
    """
    rows = db.query_all(
        sql,
        params
    )
    if detail:
        for row in rows:
            av = availability(
                row["total_checks"],
                row["success_checks"]
            )
            print()
            print(
                f"NAME           : {row['name']}"
            )
            print(
                f"IP             : {row['ip']}"
            )
            print(
                f"TYPE           : {row['check_type']}"
            )
            print(
                f"PORT           : {row['port'] or '-'}"
            )
            print(
                f"STATE          : {state_to_text(row['state'])}"
            )
            if row["state_changed"]:
                ts = datetime.fromtimestamp(
                    row["state_changed"]
                )
                print(
                    f"LAST CHANGE    : {ts}"
                )
            print(
                f"AVAILABILITY   : {av:.4f}%"
            )
            print(
                f"TIER           : {tier(av)}"
            )
            print(
                f"TOTAL CHECKS   : {row['total_checks']}"
            )
            print(
                f"SUCCESS CHECKS : {row['success_checks']}"
            )
            print(
                "-" * 60
            )
        return
    #
    # one line output
    #
    print(
        f"{'NAME':20}"
        f"{'IP':16}"
        f"{'ST':8}"
        f"{'CHAN':21}"
        f"{'AVAIL':12}"
        f"TIER"
    )
    for row in rows:
        av = availability(
            row["total_checks"],
            row["success_checks"]
        )
        changed = "-"
        if row["state_changed"]:
            changed = datetime.fromtimestamp(
                row["state_changed"]
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        print(
            f"{row['name'][:19]:20}"
            f"{row['ip']:16}"
            f"{state_to_text(row['state']):8}"
            f"{changed:21}"
            f"{av:10.4f}%  "
            f"{tier(av)}"
        )
#
# EVENTS
#
def cmd_events():
    rows = db.query_all("""
        SELECT
            e.event_time,
            h.name,
            e.old_state,
            e.new_state
        FROM events e
        JOIN hosts h
            ON h.id=e.host_id
        ORDER BY e.event_time DESC
        LIMIT 100
    """)
    for row in rows:
        ts = datetime.fromtimestamp(
            row["event_time"]
        )
        print(
            ts,
            row["name"],
            state_to_text(
                row["old_state"]
            ),
            "->",
            state_to_text(
                row["new_state"]
            )
        )
#
# SUMMARY
#
def cmd_summary():
    rows = db.query_all(
        "SELECT * FROM hosts"
    )
    total = len(rows)
    up = 0
    down = 0
    unknown = 0
    tier1 = 0
    tier2 = 0
    tier3 = 0
    tier4 = 0
    for row in rows:
        if row["state"] == 1:
            up += 1
        elif row["state"] == 0:
            down += 1
        else:
            unknown += 1
        av = availability(
            row["total_checks"],
            row["success_checks"]
        )
        t = tier(av)
        if t == "I":
            tier1 += 1
        elif t == "II":
            tier2 += 1
        elif t == "III":
            tier3 += 1
        else:
            tier4 += 1
    print()
    print("Hosts total :", total)
    print()
    print("UP          :", up)
    print("DOWN        :", down)
    print("UNKNOWN     :", unknown)
    print()
    print("Tier IV     :", tier4)
    print("Tier III    :", tier3)
    print("Tier II     :", tier2)
    print("Tier I      :", tier1)
#
# CONFIG
#
def cmd_config():
    if len(sys.argv) == 2:
        rows = db.query_all("""
            SELECT *
            FROM settings
            ORDER BY key
        """)
        for row in rows:
            print(
                f"{row['key']}="
                f"{row['value']}"
            )
        return
    key = sys.argv[2]
    value = sys.argv[3]
    db.execute("""
        INSERT OR REPLACE
        INTO settings(
            key,
            value
        )
        VALUES(
            ?,?
        )
    """,
    (
        key,
        value
    ))
    print("Saved")
#
# EXPORT CSV
#
def cmd_export():
    filename = sys.argv[2]
    rows = db.query_all(
        "SELECT * FROM hosts"
    )
    with open(
        filename,
        "w",
        newline=""
    ) as f:
        w = csv.writer(f)
        w.writerow([
            "Name",
            "IP",
            "Type",
            "Port",
            "Availability",
            "Tier"
        ])
        for row in rows:
            av = availability(
                row["total_checks"],
                row["success_checks"]
            )
            w.writerow([
                row["name"],
                row["ip"],
                row["check_type"],
                row["port"],
                av,
                tier(av)
            ])
    print(filename)
#
# EXPORT JSON
#
def cmd_export_json():
    filename = sys.argv[2]
    rows = db.query_all(
        "SELECT * FROM hosts"
    )
    result = []
    for row in rows:
        av = availability(
            row["total_checks"],
            row["success_checks"]
        )
        result.append({
            "name":
                row["name"],
            "ip":
                row["ip"],
            "type":
                row["check_type"],
            "port":
                row["port"],
            "availability":
                av,
            "tier":
                tier(av)
        })
    with open(
        filename,
        "w"
    ) as f:
        json.dump(
            result,
            f,
            indent=2
        )
    print(filename)
#
# MAIN
#
def main():
    if len(sys.argv) < 2:
        usage()
        return
    cmd = sys.argv[1]
    if cmd == "add":
        cmd_add()
    elif cmd == "del":
        cmd_del()
    elif cmd == "list":
        cmd_list()
    elif cmd == "events":
        cmd_events()
    elif cmd == "summary":
        cmd_summary()
    elif cmd == "config":
        cmd_config()
    elif cmd == "export":
        cmd_export()
    elif cmd == "export-json":
        cmd_export_json()
    else:
        usage()
if __name__ == "__main__":
    main()