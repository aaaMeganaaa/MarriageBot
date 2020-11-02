CREATE TABLE IF NOT EXISTS guild_settings(
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(30)
);


CREATE TABLE IF NOT EXISTS user_settings(
    user_id BIGINT PRIMARY KEY
);


CREATE TABLE IF NOT EXISTS role_list(
    guild_id BIGINT,
    role_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, role_id, key)
);


CREATE TABLE IF NOT EXISTS channel_list(
    guild_id BIGINT,
    channel_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, channel_id, key)
);


CREATE TABLE IF NOT EXISTS marriages(
    user_id BIGINT,
    partner_id BIGINT,
    timestamp TIMESTAMP,
    PRIMARY KEY (user_id, partner_id)
);


CREATE TABLE IF NOT EXISTS parents(
    parent_id BIGINT,
    child_id BIGINT,
    timestamp TIMESTAMP,
    PRIMARY KEY (user_id, partner_id)
);
