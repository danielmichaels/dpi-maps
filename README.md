# DPI Maps

> Retrieve maps and species reports from the Department of Prime Industries

## Setup

`pip install dpi-maps`

To login you will need to provide either an environment variable, or use the flags.

Environment variables which can be set to login:

`DPI_USERNAME` and `DPI_PASSWORD`.

Alternatively, use `--username` and `--password` flag for each invocation of the command.

By default, all maps and report are downloaded to `/tmp/dpi`. Use `--directory` or `DPI_DIRECTORY`
to override this behaviour.

## Usage

![default.png](_docs%2Fdefault.png)

To view the available commands run `dpi-maps`

### Retrieve all maps

![scrape.png](_docs%2Fscrape.png)

`dpi-maps scrape` will retrieve all the most recent maps available.

This will get both `kmz` and `pdf`. Use `--map-type=pdf` or `--map-type=kmz`
to get only that type.

### Get the latest species report

![reports.png](_docs%2Freports.png)

`dpi-maps reports` will collect the latest species report.
