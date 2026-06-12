import os
import logging
import json
from ons_client import ONSApiClient  # Assuming your client code is in client.py

# Set up logging for the client name so we can capture everything it does
client_logger = logging.getLogger("ons_client")
client_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
client_logger.addHandler(handler)

def run_test():
    client_logger.info("Setting up the ONS Client")
    client = ONSApiClient()

    # Create the output directory if it does not exist yet
    output_dir = "ons_test_outputs"
    os.makedirs(output_dir, exist_ok=True)

    # Fetch all datasets available on the ONS platform and save them
    client_logger.info("Fetching every dataset on the platform")
    all_datasets = client.get_all_datasets()
    
    all_datasets_list = [
        {
            "id": ds.id,
            "title": ds.title,
            "description": ds.description,
            "editions_url": ds.editions_url,
            "latest_version_url": ds.latest_version_url
        }
        for ds in all_datasets
    ]
    
    datasets_file_path = os.path.join(output_dir, "ons_all_datasets_list.json")
    with open(datasets_file_path, "w", encoding="utf-8") as f:
        json.dump(all_datasets_list, f, indent=2)
    client_logger.info(f"Saved datasets list to {datasets_file_path}")

    # Pick one specific dataset to drill down into (Consumer Price Inflation)
    dataset_id = "cpih01"
    client_logger.info(f"Fetching profile details for dataset {dataset_id}")
    dataset = client.get_dataset_by_id(dataset_id)
    
    if not dataset:
        client_logger.warning("Could not find the target dataset. Stopping test.")
        return

    dataset_info = {
        "id": dataset.id,
        "title": dataset.title,
        "description": dataset.description,
        "editions_url": dataset.editions_url,
        "latest_version_url": dataset.latest_version_url
    }
    profile_file_path = os.path.join(output_dir, "target_dataset_profile.json")
    with open(profile_file_path, "w", encoding="utf-8") as f:
        json.dump(dataset_info, f, indent=2)
    client_logger.info(f"Saved profile to {profile_file_path}")

    # Get and save editions for this dataset
    editions = client.get_editions(dataset)
    if not editions:
        client_logger.warning("No editions found for this dataset. Stopping test.")
        return

    editions_list = [
        {
            "id": ed.id,
            "edition": ed.edition,
            "latest_version_url": ed.latest_version_url,
            "versions_url": ed.versions_url
        }
        for ed in editions
    ]
    editions_file_path = os.path.join(output_dir, "dataset_editions.json")
    with open(editions_file_path, "w", encoding="utf-8") as f:
        json.dump(editions_list, f, indent=2)
    client_logger.info(f"Saved editions to {editions_file_path}")

    # Grab the first available edition to move forward
    target_edition = editions[0]

    # Get and save all historical versions for this edition
    versions = client.get_versions(target_edition)
    if not versions:
        client_logger.warning("No versions found for this edition. Stopping test.")
        return

    versions_list = [
        {
            "version_number": v.version_number,
            "release_date": v.release_date,
            "version_url": v.version_url
        }
        for v in versions
    ]
    versions_file_path = os.path.join(output_dir, "edition_versions.json")
    with open(versions_file_path, "w", encoding="utf-8") as f:
        json.dump(versions_list, f, indent=2)
    client_logger.info(f"Saved versions to {versions_file_path}")

    # Grab the latest published version
    latest_version = versions[0]

    # Get and save dimensions and all their nested lookup options
    dimensions = client.get_dimensions(latest_version)
    
    dimensions_list = [
        {
            "id": dim.id,
            "name": dim.name,
            "label": dim.label,
            "options_url": dim.options_url,
            "options": [{"id": opt.id, "label": opt.label} for opt in dim.options]
        }
        for dim in dimensions
    ]
    dimensions_file_path = os.path.join(output_dir, "version_dimensions.json")
    with open(dimensions_file_path, "w", encoding="utf-8") as f:
        json.dump(dimensions_list, f, indent=2)
    client_logger.info(f"Saved dimensions to {dimensions_file_path}")

    # Auto-build query filters and pull down actual data rows
    query_filters = {}
    for dim in dimensions:
        if dim.options:
            # Match the first valid filter option ID for each dimension
            query_filters[dim.name] = dim.options[0].id

    client_logger.info(f"Applying built filters: {query_filters}")
    result = client.get_observations(latest_version, query_filters)

    # Save data table straight to CSV inside the folder
    csv_file_path = os.path.join(output_dir, "observations_output.csv")
    result.dataframe.to_csv(csv_file_path, index=False)
    client_logger.info(f"Saved data rows to {csv_file_path}")

    # Save the exact recipe used to fetch this data table
    metadata = {
        "dataset_id": dataset_id,
        "version_used": latest_version.version_number,
        "filters_applied": result.dimensions_queried
    }
    metadata_file_path = os.path.join(output_dir, "observations_metadata.json")
    with open(metadata_file_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    client_logger.info(f"Saved metadata to {metadata_file_path}")

    client_logger.info("Test runner finished executing")

if __name__ == "__main__":
    run_test()