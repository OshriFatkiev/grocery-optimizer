# Grocery Optimizer

A Python tool to find the cheapest supermarkets for a list of groceries.
It scrapes prices from [chp.co.il](https://chp.co.il), optimizes for the lowest price per item, and can notify you via Telegram.

---

## Features

- Scrapes product prices from multiple stores
- Finds the cheapest store for each grocery item
- Exports results to YAML, CSV, or TXT
- Sends notifications via Telegram
- Ready for future features:
  - Fuzzy product matching
  - Multi-store route optimization
  - Price history tracking
  - Web interface (Flask)

---

## Project Structure

```

grocery\_optimizer/
│
├── input/
│   └── groceries.txt        # Your grocery list input
│
├── scraper/
│   ├── __init__.py
│   ├── base\_scraper.py      # Generic HTTP/session helpers
│   └── supermarket\_scraper.py # Logic to query chp.co.il
│
├── optimizer/
│   ├── __init__.py
│   └── price\_optimizer.py   # Chooses cheapest store per item
│
├── utils/
│   ├── __init__.py
│   ├── parser.py            # price parsing, text cleaning
│   ├── exporter.py          # YAML/CSV/TXT export
│   └── notifier.py          # Telegram bot notification
│
├── notebooks/
│   └── exploration.ipynb    # your current Jupyter work
│
├── main.py                  # entry point for CLI run
├── requirements.txt
├── .env
└── .gitignore

````

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/grocery_optimizer.git
cd grocery_optimizer
````

2. Create a virtual environment:

```bash
python -m venv venv
# macOS/Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up your `.env` file:

```
BOT_TOKEN=your-telegram-bot-token
CHAT_ID=your-chat-id
```

---

## Usage

Run the main script with desired options:

```bash
python main.py --formats yaml csv txt --notify
```

### CLI Options

* `-i, --input`              Path to grocery list (default: `input/groceries.txt`)
* `-f, --formats`            Output formats (choose one or more: yaml, csv, txt)
* `--delay`                  Seconds to wait between requests (default: 3.0)
* `--notify`                 Send results to Telegram
* `-v, --verbose`            Enable debug logging
* `-c, --compare-to-shfsl`   Create a grocery list from Shufersal for price comparison

---

## Contributing

1. Fork the repository
2. Create a feature branch:

   ```bash
   git checkout -b feature-name
   ```
3. Make your changes and commit:

   ```bash
   git commit -m "describe changes"
   ```
4. Push to your branch:

   ```bash
   git push origin feature-name
   ```
5. Open a Pull Request

---

## License

MIT License
