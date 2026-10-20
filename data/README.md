# The 311 snapshot

`311_cases.csv.gz` holds every San Francisco 311 service request opened from October 12 to 18, 2026: 17,399 rows.

| Column | Meaning |
| --- | --- |
| `service_request_id` | The request's ID. |
| `requested_datetime` | When the request was opened, in San Francisco local time. |
| `closed_date` | When it was closed. Empty while the request is open. |
| `status_description` | `Open` or `Closed`. |
| `agency_responsible` | The city team that owns the request. |
| `service_name`, `service_subtype` | What the request is about, such as `Graffiti Public`. |
| `address` | Where the problem is. |
| `analysis_neighborhood` | One of the city's 41 official neighborhoods. |
| `neighborhoods_sffind_boundaries` | The name people use for the area, such as `Lower Nob Hill`. One name can span several official neighborhoods. |
| `source` | How it was filed: `Mobile`, `Web`, `Phone`, and others. |

## Source and license

The data comes from DataSF's [311 Cases](https://data.sf.gov/d/vw6y-z8j6) dataset, published by the City and County of San Francisco under the [Open Data Commons Public Domain Dedication and License](http://opendatacommons.org/licenses/pddl/1.0/).
The DataSF [terms of use](https://www.sf.gov/reports--april-2017--datasf-terms-use) forbid using the data to identify or contact people.
That is why Exercise 3 masks addresses.

Rows filed as `Test` are removed.
Photo links and free-text notes are left out.
To rebuild the file, run `python3 scripts/fetch_snapshot.py 2026-10-12 2026-10-19`.
