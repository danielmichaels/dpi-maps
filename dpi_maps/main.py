"""
DPI map scraper.
"""
import asyncio
import os
import traceback
from dataclasses import dataclass

import structlog
import typer as typer

from dpi_maps.scrapers import MapType, ReportScraper

DOMAIN = "https://hunting.dpi.nsw.gov.au/licencing/dbnet.aspx?ac=rd&dbpage=glu-gchuntingportallogin"
USERNAME = os.getenv("DPI_USERNAME")
PASSWORD = os.getenv("DPI_PASSWORD")
logger = structlog.get_logger(__name__)
app = typer.Typer()


@dataclass
class GlobalVars:
    """
    Global CLI variables which all commands can utilize.
    """

    directory: str
    verbose: bool


async def scraper_event_loop_start(
    map_type: MapType = MapType.all.name,
    username: str = USERNAME,
    password: str = PASSWORD,
    domain: str = DOMAIN,
    download_directory: str = None,
):
    """
    Entrypoint with NATS and database connections.
    """
    from dpi_maps.scrapers import MapScraper

    if download_directory is None:
        typer.echo("no download directory specified")
        raise typer.Exit()
    scraper = MapScraper(
        domain=domain,
        username=username,
        password=password,
        map_type=map_type,
        download_directory=download_directory,
    )
    await scraper.start()


async def reports_event_loop_start(
    username: str = USERNAME,
    password: str = PASSWORD,
    domain: str = DOMAIN,
    download_directory: str = None,
):
    """
    Entrypoint with NATS and database connections.
    """
    if download_directory is None:
        typer.echo("no download directory specified")
        raise typer.Exit()
    scraper = ReportScraper(
        domain=domain,
        username=username,
        password=password,
        download_directory=download_directory,
    )
    await scraper.start()


@app.callback()
def cli(
    ctx: typer.Context,
    directory: str = typer.Option(
        "/tmp/dpi", envvar="DPI_DIRECTORY", help="Directory of downloaded maps"
    ),
    verbose: bool = typer.Option(False, envvar="DPI_VERBOSE", help="Verbose output"),
):
    """
    DPI Map Scaper.

    This application retrieves all the maps from the DPI website. It
    requires a valid login to the portal. Use at own risk.
    """
    ctx.obj = GlobalVars(directory=directory, verbose=verbose)


@app.command(name="scan")
def scan(
    ctx: typer.Context,
    filename: str,
):
    """
    Scan downloaded DPI previously harvested PDF and.
    """
    print(f"now scanning '{ctx.obj.directory}/{filename}'")


@app.command(name="reports")
def reports(
    ctx: typer.Context,
    username: str = typer.Option(
        "", envvar="DPI_USERNAME", help="DPI Portal username/license number"
    ),
    password: str = typer.Option("", envvar="DPI_PASSWORD", help="DPI Portal password/pin"),
):
    """
    Scan downloaded DPI previously harvested PDF and.
    """
    if username == "" or password == "":
        typer.echo("username and password must be supplied. exiting...")
        raise typer.Exit()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            reports_event_loop_start(
                username=username,
                password=password,
                download_directory=ctx.obj.directory,
            )
        )
        loop.close()
    except Exception as exc:  # nosec
        logger.exception("error executing event loop", error=traceback.format_exc(), exec_info=True)
        raise typer.Exit() from exc


@app.command(name="scrape")
def scrape(
    ctx: typer.Context,
    map_type: MapType = typer.Option(MapType.all.name, help="Map type to download"),
    username: str = typer.Option(
        "", envvar="DPI_USERNAME", help="DPI Portal username/license number"
    ),
    password: str = typer.Option("", envvar="DPI_PASSWORD", help="DPI Portal password/pin"),
):
    """
    Scrape the DPI State Forest maps from the portal.

    Maps are downloaded to the --directory, $DPI_DIRECTORY or to the
    default of '/tmp/dpi'. Username and Password must be present.
    --map-target refers to the type of map to download (default: pdf
    and kmz)
    """
    if username == "" or password == "":
        typer.echo("username and password must be supplied. exiting...")
        raise typer.Exit()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            scraper_event_loop_start(
                username=username,
                password=password,
                map_type=map_type,
                download_directory=ctx.obj.directory,
            )
        )
        loop.close()
    except Exception as exc:  # nosec
        logger.exception("error executing event loop", error=traceback.format_exc(), exec_info=True)
        raise typer.Exit() from exc
