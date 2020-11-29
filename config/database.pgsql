CREATE TABLE IF NOT EXISTS guild_settings(
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(30),
    gold_prefix VARCHAR(30),
    allow_incest BOOLEAN DEFAULT FALSE,
    max_family_members INTEGER DEFAULT 500,
    gifs_enabled BOOLEAN DEFAULT TRUE
);


DO $$ BEGIN
    CREATE TYPE direction AS ENUM('TB', 'LR');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;
-- Tree directions


CREATE TABLE IF NOT EXISTS user_settings(
    user_id BIGINT PRIMARY KEY,
    edge INTEGER,
    node INTEGER,
    font INTEGER,
    highlighted_font INTEGER,
    highlighted_node INTEGER,
    background INTEGER,
    direction direction
);
-- User settings - mostly tree customisations


CREATE TABLE IF NOT EXISTS role_list(
    guild_id BIGINT,
    role_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, role_id, key)
);
-- Unlikely to be used in MarriageBot


CREATE TABLE IF NOT EXISTS channel_list(
    guild_id BIGINT,
    channel_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, channel_id, key)
);
-- Unlikely to be used in MarriageBot


CREATE TABLE IF NOT EXISTS role_perks(
    role_id BIGINT PRIMARY KEY,
    value INTEGER
);
INSERT INTO role_perks (role_id, value) VALUES (0, 491589) ON CONFLICT DO NOTHING;
-- A roles vs role permission set of values
-- The integer gets shoved into our perk handler


CREATE TABLE IF NOT EXISTS blacklisted_guilds(
    guild_id BIGINT PRIMARY KEY
);
-- A list of blacklisted guild IDs


CREATE TABLE IF NOT EXISTS guild_specific_families(
    guild_id BIGINT PRIMARY KEY,
    purchased_by BIGINT
);
-- A big ol' list of guild IDs of people who've paid


CREATE TABLE IF NOT EXISTS blocked_user(
    user_id BIGINT,
    blocked_user_id BIGINT,
    PRIMARY KEY (user_id, blocked_user_id)
);
-- A user and how they're blocked ie user_id is the person who blocks blocked_user_id


CREATE TABLE IF NOT EXISTS disabled_commands(
    command_name VARCHAR(50) NOT NULL,
    guild_id BIGINT NOT NULL,
    disabled BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (command_name, guild_id)
);
-- You should be able to disable the simulation commands inside of the bot


CREATE TABLE IF NOT EXISTS redirects(
    code VARCHAR(50) PRIMARY KEY,
    location VARCHAR(2000)
);
-- Redirects for the website wew let's go gamers


CREATE TABLE IF NOT EXISTS blog_posts(
    url VARCHAR(50) PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP,
    author_id BIGINT
);
-- Some markdown based blog posts for the website to display
