<!-- SPDX-FileCopyrightText: Magenta ApS -->
<!-- SPDX-License-Identifier: MPL-2.0 -->
# Thyme 🌿

Simple tool for reading timespans from [Traggo](https://traggo.net/) and sending them to Redmine.

You see, _thyme_ rhymes with _time_ and it's a _time_-tracking helper, so, it's... uhh

## Usage

Example usage, to create Redmine time entries based on today:

```
python thyme.py <REDMINE_API_KEY> <TRAGGO_API_KEY>
```

API-keys can also be set as environment variables

For a full list of options, run:

```
python thyme.py --help
```

## Docker
```
docker-compose up -d --build
```
gives a `traggo` instance on `localhost:3030`. Environment variables can be set in e.g. a `docker-compose.override.yml`

```yml
version: "3.9"
services:
  traggo:
    environment:
      TRAGGO_DEFAULT_USER_NAME: "AzureDiamond"
      TRAGGO_DEFAULT_USER_PASS: "hunter2"
  thyme:
    environment:
      REDMINE_API_KEY: a1234
      TRAGGO_API_KEY: b5678
```
then, `docker-compose run thyme` will... run `thyme`!

## TODO

- Add support for other time tracking backends
- Rewrite in Rust, lol 🦀
