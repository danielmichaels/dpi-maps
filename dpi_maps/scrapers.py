import enum
import os
import pathlib
import time

import httpx
import structlog
import typer as typer
from fake_useragent import UserAgent
from playwright.async_api import Playwright, async_playwright

logger = structlog.get_logger(__name__)

DOMAIN = "https://hunting.dpi.nsw.gov.au/licencing/dbnet.aspx?ac=rd&dbpage=glu-gchuntingportallogin"
USERNAME = os.getenv("DPI_USERNAME")
PASSWORD = os.getenv("DPI_PASSWORD")


class MapType(enum.Enum):
    """
    Valid map_type options.
    """

    all = "all"
    kmz = "kmz"
    pdf = "pdf"


class Scraper:
    """
    Scraper class from which everything inherits from.
    """

    page = None
    browser = None
    context = None

    def __init__(
        self,
        domain: str,
        username: str,
        password: str,
        download_directory: str,
        *args,
        **kwargs,
    ):
        self.download_directory = download_directory
        self.domain = domain
        self.username = username
        self.password = password

    async def start(self):
        """
        Start an async playwright scraper.
        """
        try:
            async with async_playwright() as p:
                return await self.run_scraper(p)
        except Exception as exc:
            raise exc

    async def run_scraper(self, playwright: Playwright):
        """
        Method with implements the running fo the scraper.
        """
        raise NotImplementedError

    async def scrape(self):
        """
        Method which implements the scraper.
        """
        raise NotImplementedError


class MapScraper(Scraper):
    """
    Scrape maps from DPI portal.
    """

    maps = None

    def __init__(self, map_type: MapType, *args, **kwargs):
        self.map_type = map_type
        super().__init__(*args, **kwargs)

    async def run_scraper(self, playwright: Playwright):
        """
        Run playwright; entrypoint for all scrapers.
        """
        ua = UserAgent(browsers=["edge", "chrome", "firefox"])
        useragent = ua.random
        logger.info("starting browser", useragent=useragent, domain=self.domain)
        self.browser = await playwright.webkit.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=useragent,
        )
        self.page = await self.context.new_page()
        await self.page.goto(self.domain)
        logger.info("attempting scrape DPI", domain=self.domain)
        await self.page.locator("#licno").fill(self.username)
        time.sleep(0.5)
        await self.page.locator("#pin").fill(self.password)
        time.sleep(1)
        await self.page.locator("#loginBtn").click()
        time.sleep(1)
        await self.scrape()
        await self.retrieve_maps_runner()

    async def scrape(self):
        """
        Scrape DPI maps and download them to local filesystem
        :return:
        """
        await self.page.locator("#btnGps").click()
        time.sleep(1)
        await self.page.locator("#selArea").click()

        # get all options
        dropdowns = []
        dropdown = await self.page.query_selector_all("#selArea > option")
        for item in dropdown:
            txt = await item.inner_text()
            val = await item.get_attribute("value")
            if val is None:
                continue
            dropdowns.append({"name": txt, "value": val})

        result = []
        for option in dropdowns[5:7]:
            await self.page.get_by_label("Hunting Area").select_option(option.get("name"))
            pdf = await self.page.query_selector(
                "#areasList > table > tbody > tr:nth-child(3) > td:nth-child(1) > a"
            )
            kmz = await self.page.query_selector(
                "#areasList > table > tbody > tr:nth-child(4) > td:nth-child(1) > a"
            )
            time.sleep(1)
            if pdf is None or kmz is None:
                continue
            pdf_href = await pdf.get_attribute("href") if pdf else None
            kmz_href = await kmz.get_attribute("href") if kmz else None
            option.update({"pdf": pdf_href, "kmz": kmz_href})
            logger.info("new map added", map=option.get("name"), kmz=kmz_href, pdf=pdf_href)
            result.append(option)

        if os.getenv("DEBUG"):
            for r in result:
                print(r)

        await self.page.wait_for_timeout(500)
        await self.context.close()
        await self.browser.close()
        logger.info(
            "finished scraping DPI: shutting down browser",
            domain=self.domain,
            maps_found=len(result),
        )
        self.maps = result

    async def retrieve_maps_runner(self):
        """
        Execute retrieve_maps based on the map type selected.
        """
        if self.map_type.name == "all":
            await self.retrieve_maps("pdf", download_path=self.download_directory)
            await self.retrieve_maps("kmz", download_path=self.download_directory)
        if self.map_type.name == "kmz":
            await self.retrieve_maps("kmz", download_path=self.download_directory)
        if self.map_type.name == "pdf":
            await self.retrieve_maps("pdf", download_path=self.download_directory)

    async def retrieve_maps(self, map_type: str, download_path: str):
        """
        Download all the maps.
        """
        if download_path == "":
            typer.echo("no download path specified.")
            raise typer.Exit()
        path = pathlib.Path(f"{download_path}/{map_type}")
        path.mkdir(parents=True, exist_ok=True)
        for m in self.maps:
            try:
                r = httpx.get(m.get(map_type), timeout=20)
                file = path / f"{m.get('name')}.{map_type}"
                file.write_bytes(data=r.content)
                logger.info(
                    "downloaded map",
                    map_name=m.get("name"),
                    download_path=download_path,
                    map_type=map_type,
                )
            except Exception:  # nosec
                logger.error(
                    "failed to download map",
                    map_name=m.get("name"),
                    map_type=map_type,
                )


class ReportScraper(Scraper):
    """
    Scraper which retrieves the species reports.
    """

    reports = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def run_scraper(self, playwright: Playwright):
        """
        Run playwright; entrypoint for all scrapers.
        """
        ua = UserAgent(browsers=["edge", "chrome", "firefox"])
        useragent = ua.random
        logger.info("starting browser", useragent=useragent, domain=self.domain)
        self.browser = await playwright.webkit.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=useragent,
        )
        self.page = await self.context.new_page()
        await self.page.goto(self.domain)
        logger.info("attempting scrape DPI", domain=self.domain)
        await self.page.locator("#licno").fill(self.username)
        time.sleep(0.5)
        await self.page.locator("#pin").fill(self.password)
        time.sleep(1)
        await self.page.locator("#loginBtn").click()
        time.sleep(1)
        await self.scrape()

    async def scrape(self):
        """
        Scrapes the report.
        """
        await self.page.locator("#btnSpeciesReport").click()
        time.sleep(2)

        result = []
        last = await self.page.query_selector(
            "#pastSpeciesReport > table > tbody > tr:nth-child(1) > td > a"
        )
        title = await last.inner_text() if last else None
        time.sleep(1.5)
        link = await last.get_attribute("href") if last else None
        if link is None:
            # try again naive approach
            time.sleep(1.5)
            last = await self.page.query_selector(
                "#pastSpeciesReport > table > tbody > tr:nth-child(1) > td > a"
            )
            time.sleep(1.5)
            link = await last.get_attribute("href")
        report = {"title": title, "href": link}
        result.append(report)

        await self.page.wait_for_timeout(500)
        await self.context.close()
        await self.browser.close()
        logger.info(
            "finished scraping DPI: shutting down browser",
            reports=result,
            reports_retrieved=len(result),
        )
        self.reports = result

        await self.retrieve_reports(self.download_directory)

    async def retrieve_reports(self, download_path: str):
        """
        Download all the maps.
        """
        if download_path == "":
            typer.echo("no download path specified.")
            raise typer.Exit()

        path = pathlib.Path(f"{download_path}/reports")
        path.mkdir(parents=True, exist_ok=True)
        for report in self.reports:
            try:
                r = httpx.get(report.get("href"), timeout=20)
                title = f'{report.get("title")}'.replace("/", "_")
                file = path / f"{title}.pdf"
                file.write_bytes(data=r.content)
                logger.info(
                    "downloaded species report",
                    report_name=report.get("title"),
                    report_url=report.get("href"),
                    download_path=download_path,
                )
            except Exception:  # nosec
                logger.error(
                    "failed to download map",
                    report_name=report.get("title"),
                    report_url=report.get("href"),
                )


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
