# DEPRECATED 
Replaced by [wait-what/misskey-booru-rs](https://github.com/wait-what/misskey-booru-rs)

# Misskey Booru Image Bot Docker
Automatically post images from booru to misskey instances (and forks supporting the misskey api).

> This is a fork of [himanshugoel2797/MisskeyBooruImageBot](https://github.com/himanshugoel2797/MisskeyBooruImageBot) which does not use docker, but rather a systemd timer.

## Usage
- Clone this repo
- Copy `config_example.json` to `config.json` and edit it
    > You can specify multiple bots in one config!
- Copy `config_example.env` to `config.env` and edit it
- Run `docker compose up -d`
