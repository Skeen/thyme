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

## TODO

- Add support for other time tracking backends
- Rewrite in Rust, lol 🦀