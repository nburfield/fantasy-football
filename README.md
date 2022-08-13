# Fantasy Football


# Setup
1. Create the Python Virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements
    ```

2. **optional** Collect the additional player rankings


# Data Source

## ADP
The ADP data is pulled by the script for every run. The source data is provided by this site.
- https://fantasyfootballcalculator.com/adp

## Player Rankings - Fantasy Footballers Data

**This is optional data.**

The player rankings must be downloaded manually. Go to the page and select rankings at the top.
Go to each position, input the valid parameters for scoring format, and export as CSV.
**Save the CSV files in a folder local to project named `ffrd/<scoring-format>` (Ex. `ffrd/half-ppr`)**
- https://www.thefantasyfootballers.com/


# Running Script
`python make_draft_board.py -sf <scoring_format> -pc <player_count>`
- scoring_format Options:
  - ppr: Full Points Per Reception
  - half-ppr: Half Points Per Reception
  - standard: Standard Scoring (ie. No PPR)
- player_count Options: *The ADP Source Only Has These Available*
  - 8
  - 10
  - 12
  - 14
