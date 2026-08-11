import os

import dlt
import requests
from dotenv import load_dotenv

load_dotenv()

LOGFIRE_QUERY_URL = "https://logfire-us.pydantic.dev/v2/query"


@dlt.resource(name="records", write_disposition="replace")
def logfire_records():
    read_token = os.environ["LOGFIRE_READ_TOKEN"]

    resp = requests.post(
        LOGFIRE_QUERY_URL,
        headers={
            "Authorization": f"Bearer {read_token}",
            "Accept": "application/json",
        },
        json={
            "sql": "SELECT * FROM records ORDER BY start_timestamp",
            "min_timestamp": "2020-01-01T00:00:00Z",
            "limit": 10000,
        },
    )
    resp.raise_for_status()
    yield resp.json()["data"]


def main():
    pipeline = dlt.pipeline(
        pipeline_name="logfire_traces",
        destination="duckdb",
        dataset_name="agent_traces",
    )
    load_info = pipeline.run(logfire_records())
    print(load_info)


if __name__ == "__main__":
    main()
