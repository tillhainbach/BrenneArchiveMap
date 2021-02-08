"""Parse excel file into geoJson."""

import os
import sys
from typing import List, Tuple
import json
import geojson
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim


class Locator:
    """Locate Coordinates for Addresses."""

    latitude = 'latitude'
    longitude = 'longitude'

    def __init__(self, locator: Nominatim):
        """Initiate Locator."""
        self.geolocator = locator

    def _geocode(
        self,
        df: pd.DataFrame,
        address_columns: List[str]
    ) -> Tuple[float, float]:
        return self.geolocator.geocode(
            df.loc[address_columns].apply(str).str.cat(sep=" "))[1]

    def parse_address(
        self,
        df: pd.DataFrame,
        address_columns: List[str]
    ) -> pd.DataFrame:
        """Add Coordinates for addresses in DataFrame."""
        df[['latitude', 'longitude']] = df.apply(
            self._geocode,
            address_columns=address_columns,
            axis=1,
            result_type='expand'
        )

        return df

    @staticmethod
    def get_coordinate_column_names() -> List[str]:
        """Return column names containing coordinates."""
        return [Locator.latitude, Locator.longitude]


def clean_up_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Make dataframe json-parseable."""
    # Replace null values with np.nan
    df.replace("N.N.", "", inplace=True)
    df.replace("./.", "", inplace=True)
    df.fillna("", inplace=True)

    # Convert pandas.Timestamp to string
    df = df.applymap(
        lambda x: x.strftime("%d.%m.%Y") if isinstance(x, pd.Timestamp) else x
    )

    # convert PLZ to int
    df.loc[:, "PLZ"] = df.loc[:, "PLZ"].apply(int)

    return df


def pandas_to_geojson(pandas_df: pd.DataFrame) -> geojson.FeatureCollection:
    """Convert pandas DataFrame to geojson."""
    features = pandas_df.apply(
        lambda df: geojson.Feature(
            geometry=geojson.Point(
                coordinates=df[Locator.get_coordinate_column_names()].to_list()
            ),
            properties=df.drop(Locator.get_coordinate_column_names()).to_dict()
        ),
        axis=1
    )

    return geojson.FeatureCollection(features.to_list())


def main(excel_file_path):
    """Run Main Program."""
    # Read data and clean up
    data = pd.read_excel("data/data.xlsx").dropna(how="all")
    data = clean_up_dataframe(data)

    # convert addresses to locations
    locator = Locator(Nominatim(user_agent='coordinateMaker', timeout=10))
    data = locator.parse_address(
        data,
        ['STRASSE + NR.', 'PLZ', 'STADT - BEZIRK']
    )

    feature_collection = pandas_to_geojson(data)
    filename = os.path.splitext(excel_file_path)[0]
    with open(filename + ".geojson", "w") as geojson_file:
        geojson.dump(
            feature_collection,
            geojson_file,
            indent=2
        )


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:\n\tpython parse_excel_file.py excel_file_path")
        sys.exit(0)

    main(sys.argv[1])
