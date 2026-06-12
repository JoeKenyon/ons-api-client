# ONS API Client

A straightforward Python client built to interact with the Office for National Statistics API. It handles pagination, tracks dataset editions, manages historical versions, and pulls data down into clean Pandas DataFrames.

---

## What It Does

* **Paginates Automatically:** You do not have to worry about missing data rows; the client loops through API pages behind the scenes.
* **Resolves Lookups:** Translates complex nested dimension options into easy to use lookup structures.
* **Silent Logging:** Uses standard Python library logging best practices so it stays completely quiet unless you explicitly turn it on in your own scripts.

---

## Getting Started

### Prerequisites

You will need Python installed along with a couple of external libraries for data handling and API requests.

```bash
pip install pandas requests urllib3
```

### File Structure

Keep your files organized like this:

* `ons_client.py` - Contains the main client code and dataclasses.
* `test.py` - The script to run tests, configure logs, and pull data.

---

## How to Run the Test Script

The test script automatically contacts the live API, queries the Consumer Price Inflation dataset, and builds folder outputs.

To run it, execute:

```bash
python test.py
```

### Generated Outputs

When you run the test, it creates a new folder named `ons_test_outputs` and populates it with the following files:

* `ons_all_datasets_list.json` - A full index of every dataset hosted on the platform.
* `target_dataset_profile.json` - Metadata for the selected dataset.
* `dataset_editions.json` - Available editions for the dataset.
* `edition_versions.json` - Complete release history of the selected edition.
* `version_dimensions.json` - All structural categories and lookup filters for that specific data snapshot.
* `observations_output.csv` - The actual data matrix filtered and loaded directly into a tabular file.
* `observations_metadata.json` - A snapshot tracking the exact API recipe used to pull the CSV.

---

## Controlling Logs

By default, the client is completely silent when imported. If you want to see the client's inner thoughts while running your scripts, initialize the log stream inside your main execution file:

```python
import logging

client_logger = logging.getLogger("ons_client")
client_logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
client_logger.addHandler(handler)
```
