CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email VARCHAR(255) DEFAULT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    data_usage BIGINT NOT NULL DEFAULT 0,
    api_key VARCHAR(255) DEFAULT NULL,
    model VARCHAR(64) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO users (id, username, password_hash, role, email, status, data_usage, api_key, model, created_at) VALUES
(1, 'admin', 'TzuRioC8iSq2KWxi/bfmDQ==:6T2FcBuanxB0//rv+D7zdL5jivtNa3WNBvDjBHvwipM=', 'admin', NULL, 'active', 0, NULL, 'gemini-2.5-flash', '2026-01-20 10:13:50'),
(2, 'user1', 'XRNCzN16MShwvZaFewmO/w==:/LyZjJwimlQemOl+c6XauzFI4Q8znNggCtWikUHetbo=', 'user', NULL, 'active', 0, NULL, 'gemini-2.5-flash', '2026-01-20 10:13:50'),
(3, 'sbd', 'g43Xl67sJfIqLIf4uh0x+w==:EP7jitb00CqxwmMYFePruL2Wkj9zK+3Fp/DVaA7/aQQ=', 'user', NULL, 'active', 0, NULL, 'gemini-2.5-flash', '2026-01-20 12:27:59')
ON DUPLICATE KEY UPDATE
    username=VALUES(username),
    password_hash=VALUES(password_hash),
    role=VALUES(role),
    email=VALUES(email),
    status=VALUES(status),
    data_usage=VALUES(data_usage),
    api_key=VALUES(api_key),
    model=VALUES(model),
    created_at=VALUES(created_at);
