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

grocery_optimizer/
│
├── input/
│   └── groceries.txt           # Your grocery list input in Hebrew
│
├── scraper/
│   ├── __init__.py
│   ├── base_scraper.py         # Generic HTTP/session helpers
│   └── supermarket_scraper.py  # Logic to query chp.co.il
│
├── optimizer/
│   ├── __init__.py
│   └── price_optimizer.py      # Chooses cheapest store per item
│
├── utils/
│   ├── __init__.py
│   ├── parser.py               # price parsing, text cleaning
│   ├── exporter.py             # YAML/CSV/TXT export
│   ├── notifier.py             # Telegram bot notification
│   └── convert_bycode.py       # Convert CBS .xlsx locality codes into JSON
│
├── notebooks/
│   └── exploration.ipynb       # your current Jupyter work
│
├── main.py                     # entry point for CLI run
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
conda create -n venv python=3.13
conda activate venv
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
* `--compare-to-shfsl`       Create a grocery list from Shufersal for price comparison
* `--city`                   Specify the city to look up available stores in
* `--max-stores`             Limit the optimizer to the cheapest combination of up to N stores
* `--use-found-names`        Replace input item names with the product names returned by the site
* `--add-brand`              Append manufacturer/brand information to each item when available

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
