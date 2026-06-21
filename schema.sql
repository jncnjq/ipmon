PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS hosts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    group_name TEXT DEFAULT 'default',
    ip TEXT NOT NULL,
    check_type TEXT NOT NULL DEFAULT 'ICMP',
    port INTEGER,
    interval INTEGER NOT NULL,
    state INTEGER DEFAULT -1,
    last_check INTEGER DEFAULT 0,
    state_changed INTEGER DEFAULT 0,
    total_checks INTEGER DEFAULT 0,
    success_checks INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_hosts_ip
ON hosts(ip,check_type,port);
CREATE INDEX IF NOT EXISTS idx_hosts_group
ON hosts(group_name);
CREATE INDEX IF NOT EXISTS idx_hosts_check
ON hosts(last_check);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time INTEGER NOT NULL,
    host_id INTEGER NOT NULL,
    old_state INTEGER NOT NULL,
    new_state INTEGER NOT NULL,
    FOREIGN KEY(host_id)
        REFERENCES hosts(id)
        ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_events_time
ON events(event_time);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT OR IGNORE INTO settings
VALUES ('schema_version','2.0');
INSERT OR IGNORE INTO settings
VALUES ('http_port','18080');
INSERT OR IGNORE INTO settings
VALUES ('max_workers','50');
INSERT OR IGNORE INTO settings
VALUES ('down_threshold','3');
INSERT OR IGNORE INTO settings
VALUES ('up_threshold','2');
INSERT OR IGNORE INTO settings
VALUES ('event_retention_days','90');