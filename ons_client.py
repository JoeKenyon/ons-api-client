import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@dataclass
class ONSDataset:
    id: str
    title: str
    description: str
    editions_url: str
    latest_version_url: Optional[str] = None

    @classmethod
    def from_json(cls, data: dict) -> "ONSDataset":
        links = data.get("links", {})
        return cls(
            id=data["id"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            editions_url=links.get("editions", {}).get("href", ""),
            latest_version_url=links.get("latest_version", {}).get("href"),
        )


@dataclass
class ONSEdition:
    id: str
    edition: str
    latest_version_url: str
    versions_url: str

    @classmethod
    def from_json(cls, data: dict) -> "ONSEdition":
        links = data.get("links", {})
        return cls(
            id=data["id"],
            edition=data["edition"],
            latest_version_url=links.get("latest_version", {}).get("href", ""),
            versions_url=links.get("versions", {}).get("href", "")
        )


@dataclass
class ONSOption:
    id: str
    label: str


@dataclass
class ONSDimension:
    id: str
    name: str
    label: str
    options_url: str
    options: List[ONSOption] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict) -> "ONSDimension":
        links = data.get("links", {})
        return cls(
            id=links.get("code_list").get("id"),
            name=data.get("name"),
            label=data.get("label", ""),
            options_url=links.get("options", {}).get("href", ""),
        )

    @property
    def options_map(self) -> Dict[str, str]:
        """Handy dict to quickly look up an option's label using its ID."""
        return {opt.id: opt.label for opt in self.options}


@dataclass
class ONSVersion:
    version_number: int
    release_date: str
    version_url: str

    @classmethod
    def from_json(cls, data: dict) -> "ONSVersion":
        links = data.get("links", {})
        return cls(
            version_number=data["version"],
            release_date=data.get("release_date", ""),
            version_url=links.get("self", {}).get("href", ""),
        )


@dataclass
class ONSObservationResult:
    dataframe: pd.DataFrame
    dimensions_queried: Dict[str, str]


class ONSApiClient:
    BASE_URL = "https://api.beta.ons.gov.uk/v1"

    def __init__(self):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

    def get_all_datasets(self) -> List[ONSDataset]:
        """Grabs every single dataset by looping through the API pages."""
        datasets = []
        offset, limit = 0, 50

        while True:
            logger.info(f"fetching datasets from offset {offset}...")
            response = self.session.get(
                f"{self.BASE_URL}/datasets",
                params={"offset": offset, "limit": limit},
            )
            response.raise_for_status()
            items = response.json().get("items", [])
            
            for item in items:
                datasets.append(ONSDataset.from_json(item))

            if len(items) < limit:
                break

            offset += len(items)

        logger.info(f"successfully retrieved {len(datasets)} total datasets.")
        return datasets

    def get_dataset_by_id(self, target_id: str) -> Optional[ONSDataset]:
        """Looks up a specific dataset by its ID. Returns None if it can't find it."""
        try:
            logger.info(f"requesting dataset profile for '{target_id}'...")
            response = self.session.get(f"{self.BASE_URL}/datasets/{target_id}")
            response.raise_for_status()
            logger.info(f"successfully resolved dataset '{target_id}'")
            return ONSDataset.from_json(response.json())
        except requests.exceptions.HTTPError:
            logger.warning(f"no dataset found with id '{target_id}'")
            return None

    def get_editions(self, dataset: ONSDataset) -> List[ONSEdition]:
        """Finds what editions are available for a given dataset."""
        logger.info(f"fetching available editions for dataset '{dataset.id}'...")
        response = self.session.get(dataset.editions_url)
        response.raise_for_status()
        items = response.json().get("items", [])
        logger.info(f"found {len(items)} editions for dataset '{dataset.id}'")
        return [ONSEdition.from_json(item) for item in items]
    
    def get_versions(self, edition: ONSEdition) -> List[ONSVersion]:
        """Gets the history of all published versions for an edition."""
        versions = []
        offset, limit = 0, 50

        while True:
            logger.info(f"fetching versions for edition '{edition.edition}' from offset {offset}...")
            response = self.session.get(
                edition.versions_url,
                params={"offset": offset, "limit": limit}
            )
            response.raise_for_status()
            items = response.json().get("items", [])
            
            for item in items:
                versions.append(ONSVersion.from_json(item))

            if len(items) < limit:
                break

            offset += len(items)

        logger.info(f"found {len(versions)} total historical versions for edition '{edition.edition}'")
        return versions

    def _fetch_dimension_options(self, dimension_name: str, options_url: str) -> List[ONSOption]:
        """Helper to loop through and grab all the choices/options for a dimension."""
        options = []
        offset, limit = 0, 100
        
        while True:
            response = self.session.get(
                options_url, 
                params={"offset": offset, "limit": limit}
            )
            response.raise_for_status()
            items = response.json().get("items", [])

            for item in items:
                options.append(ONSOption(id=item["option"], label=item["label"]))

            if len(items) < limit:
                break
                
            offset += len(items)
            
        logger.info(f"resolved {len(options)} total filtering options for dimension '{dimension_name}'")
        return options

    def get_dimensions(self, version: ONSVersion) -> List[ONSDimension]:
        """Pulls down the dimensions for a version and fills in all their options."""
        logger.info(f"fetching dimensions from version endpoint...")
        response = self.session.get(f"{version.version_url}/dimensions")
        response.raise_for_status()

        dimensions = [
            ONSDimension.from_json(d) for d in response.json().get("items", [])
        ]

        logger.info(f"identified dimensions: {[[d.name] for d in dimensions]}. getting options...")
        for dim in dimensions:
            dim.options = self._fetch_dimension_options(dim.name, dim.options_url)

        return dimensions

    def get_observations(self, version: ONSVersion, query_filters: Dict[str, str]) -> ONSObservationResult:
        """Queries the data matching your filters and dumps it into a clean Pandas DataFrame."""
        logger.info(f"requesting observation query matrix using filters: {query_filters}...")
        response = self.session.get(
            f"{version.version_url}/observations", 
            params=query_filters
        )
        response.raise_for_status()

        rows = []
        payload = response.json()
        observations = payload.get("observations", [])
        
        for obs in observations:
            row_data = {"observation": obs.get("observation")}
            for dim_name, dim_info in obs.get("dimensions", {}).items():
                row_data[dim_name.lower()] = dim_info.get("id")
            rows.append(row_data)

        logger.info(f"successfully parsed {len(rows)} data rows into observation dataframe")
        return ONSObservationResult(
            dataframe=pd.DataFrame(rows), 
            dimensions_queried=query_filters
        )