#!/usr/bin/env python3
import os
import time
import socket
import signal
import subprocess
import threading
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)
from db import db
from constants import (
    STATE_UP,
    STATE_DOWN,
    STATE_UNKNOWN,
    CHECK_ICMP,
    CHECK_TCP,
    DEFAULT_TCP_PORT
)
from webui import start_http
PID_FILE = "ipmon.pid"
#
# PID LOCK
#
def create_pid_file():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(
                    f.read().strip()
                )
            os.kill(pid, 0)
            print(
                f"Already running PID={pid}"
            )
            raise SystemExit(1)
        except OSError:
            pass
    with open(PID_FILE, "w") as f:
        f.write(
            str(os.getpid())
        )
def remove_pid_file():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
#
# SETTINGS
#
def get_setting(name, default):
    row = db.query_one(
        """
        SELECT value
        FROM settings
        WHERE key=?
        """,
        (name,)
    )
    if row:
        return row["value"]
    return default
#
# EVENTS
#
def write_event(
    host_id,
    old_state,
    new_state
):
    db.execute(
        """
        INSERT INTO events(
            event_time,
            host_id,
            old_state,
            new_state
        )
        VALUES(
            strftime('%s','now'),
            ?,
            ?,
            ?
        )
        """,
        (
            host_id,
            old_state,
            new_state
        )
    )
#
# CHECKS
#
def icmp_check(ip):
    rc = subprocess.call(
        [
            "ping",
            "-c", "1",
            "-W", "1",
            ip
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return rc == 0
def tcp_check(
    ip,
    port
):
    try:
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        sock.settimeout(2)
        result = sock.connect_ex(
            (ip, port)
        )
        sock.close()
        return result == 0
    except Exception:
        return False
def check_host(row):
    host_id = row["id"]
    if row["check_type"] == CHECK_TCP:
        port = (
            row["port"]
            or DEFAULT_TCP_PORT
        )
        ok = tcp_check(
            row["ip"],
            port
        )
    else:
        ok = icmp_check(
            row["ip"]
        )
    return (
        host_id,
        ok
    )
#
# HOST UPDATE
#
def process_result(
    host,
    ok
):
    host_id = host["id"]
    state = host["state"]
    fail_count = host["fail_count"]
    success_count = host["success_count"]
    total_checks = (
        host["total_checks"] + 1
    )
    success_checks = (
        host["success_checks"]
    )
    if ok:
        success_checks += 1
    down_threshold = int(
        get_setting(
            "down_threshold",
            3
        )
    )
    up_threshold = int(
        get_setting(
            "up_threshold",
            2
        )
    )
    if ok:
        success_count += 1
        fail_count = 0
    else:
        fail_count += 1
        success_count = 0
    new_state = state
    #
    # UNKNOWN
    #
    if state == STATE_UNKNOWN:
        if ok:
            if success_count >= up_threshold:
                new_state = STATE_UP
        else:
            if fail_count >= down_threshold:
                new_state = STATE_DOWN
    #
    # UP
    #
    elif state == STATE_UP:
        if fail_count >= down_threshold:
            new_state = STATE_DOWN
    #
    # DOWN
    #
    elif state == STATE_DOWN:
        if success_count >= up_threshold:
            new_state = STATE_UP
    #
    # EVENT
    #
    if new_state != state:
        write_event(
            host_id,
            state,
            new_state
        )
        db.execute(
            """
            UPDATE hosts
            SET
                state_changed=
                    strftime('%s','now')
            WHERE id=?
            """,
            (
                host_id,
            )
        )
    #
    # SAVE
    #
    db.execute(
        """
        UPDATE hosts
        SET
            state=?,
            last_check=
                strftime('%s','now'),
            total_checks=?,
            success_checks=?,
            fail_count=?,
            success_count=?
        WHERE id=?
        """,
        (
            new_state,
            total_checks,
            success_checks,
            fail_count,
            success_count,
            host_id
        )
    )
#
# CLEANUP
#
def cleanup_old_events():
    retention = int(
        get_setting(
            "event_retention_days",
            90
        )
    )
    db.execute(
        """
        DELETE
        FROM events
        WHERE event_time
        <
        strftime('%s','now')
        - ?
        """,
        (
            retention * 86400,
        )
    )
def maintenance_thread():
    while True:
        try:
            cleanup_old_events()
        except Exception as e:
            print(
                "maintenance:",
                e
            )
        #
        # once per day
        #
        time.sleep(
            86400
        )
#
# MONITOR
#
def monitor_loop():
    max_workers = int(
        get_setting(
            "max_workers",
            50
        )
    )
    pool = ThreadPoolExecutor(
        max_workers=max_workers
    )
    while True:
        rows = db.query_all(
            """
            SELECT *
            FROM hosts
            WHERE
                last_check
                +
                interval
                <=
                strftime(
                    '%s',
                    'now'
                )
            """
        )
        futures = {}
        for row in rows:
            future = pool.submit(
                check_host,
                row
            )
            futures[
                future
            ] = row
        for future in as_completed(
            futures
        ):
            row = futures[
                future
            ]
            try:
                host_id, ok = (
                    future.result()
                )
                process_result(
                    row,
                    ok
                )
            except Exception as e:
                print(
                    row["name"],
                    e
                )
        time.sleep(1)
#
# MAIN
#
def main():
    create_pid_file()
    signal.signal(
        signal.SIGTERM,
        lambda *x:
            remove_pid_file()
    )
    signal.signal(
        signal.SIGINT,
        lambda *x:
            remove_pid_file()
    )
    http_port = int(
        get_setting(
            "http_port",
            18080
        )
    )
    threading.Thread(
        target=start_http,
        args=(http_port,),
        daemon=True
    ).start()
    threading.Thread(
        target=maintenance_thread,
        daemon=True
    ).start()
    print(
        f"HTTP port {http_port}"
    )
    print(
        "Monitor started"
    )
    monitor_loop()
if __name__ == "__main__":
    main()