"""Playwright 供应商报价抓取模块"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from shared.config_loader import SupplierEntry
from shared.crypto import decrypt_value
from shared.logger import get_logger

logger = get_logger("browser_scraper")


@dataclass
class QuoteResult:
    """单个供应商对某 SKU 的报价"""
    supplier_name: str
    sku: str
    unit_price: Optional[float] = None
    currency: str = "CNY"
    delivery_days: Optional[int] = None
    min_order_qty: Optional[int] = None
    quote_url: str = ""
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and self.unit_price is not None


class BaseScraper(ABC):
    """供应商爬虫基类"""

    def __init__(self, supplier_config: SupplierEntry):
        self.config = supplier_config
        self.name = supplier_config.name

    @abstractmethod
    async def scrape_price(self, page, sku: str, product_name: str) -> QuoteResult:
        """在已登录的页面上抓取指定 SKU 的价格"""
        ...

    async def login(self, page) -> bool:
        """登录供应商后台"""
        sel = self.config.selectors
        password = decrypt_value(self.config.password_encrypted)

        try:
            await page.goto(self.config.login_url, wait_until="networkidle")
            await page.fill(sel.username_input, self.config.username)
            await page.fill(sel.password_input, password)
            await page.click(sel.login_button)
            await page.wait_for_load_state("networkidle")
            logger.info("登录成功: %s", self.name, extra={"supplier": self.name})
            return True
        except Exception as e:
            logger.error("登录失败: %s — %s", self.name, e, extra={"supplier": self.name})
            return False


class Supplier01Scraper(BaseScraper):
    """东莞精密五金 爬虫"""

    async def scrape_price(self, page, sku: str, product_name: str) -> QuoteResult:
        sel = self.config.selectors
        try:
            price_url = self.config.url + self.config.price_page
            await page.goto(price_url, wait_until="networkidle")

            # 在价格表中搜索 SKU
            rows = await page.query_selector_all(f"{sel.price_table} tr")
            for row in rows:
                text = await row.inner_text()
                if sku in text or product_name in text:
                    price_el = await row.query_selector(sel.price_cell)
                    delivery_el = await row.query_selector(sel.delivery_cell)

                    price_text = await price_el.inner_text() if price_el else "0"
                    delivery_text = await delivery_el.inner_text() if delivery_el else "0"

                    return QuoteResult(
                        supplier_name=self.name,
                        sku=sku,
                        unit_price=float(price_text.replace("¥", "").replace(",", "").strip()),
                        delivery_days=int("".join(filter(str.isdigit, delivery_text)) or "0"),
                        quote_url=price_url,
                    )

            return QuoteResult(
                supplier_name=self.name, sku=sku,
                error=f"未找到 SKU {sku} 的报价",
            )
        except Exception as e:
            return QuoteResult(
                supplier_name=self.name, sku=sku, error=str(e),
            )


class Supplier02Scraper(BaseScraper):
    """上海标准件 爬虫"""

    async def scrape_price(self, page, sku: str, product_name: str) -> QuoteResult:
        sel = self.config.selectors
        try:
            price_url = self.config.url + self.config.price_page
            await page.goto(price_url, wait_until="networkidle")

            rows = await page.query_selector_all(f"{sel.price_table} tr")
            for row in rows:
                text = await row.inner_text()
                if sku in text or product_name in text:
                    price_el = await row.query_selector(sel.price_cell)
                    delivery_el = await row.query_selector(sel.delivery_cell)

                    price_text = await price_el.inner_text() if price_el else "0"
                    delivery_text = await delivery_el.inner_text() if delivery_el else "0"

                    return QuoteResult(
                        supplier_name=self.name,
                        sku=sku,
                        unit_price=float(price_text.replace("¥", "").replace(",", "").strip()),
                        delivery_days=int("".join(filter(str.isdigit, delivery_text)) or "0"),
                        quote_url=price_url,
                    )

            return QuoteResult(
                supplier_name=self.name, sku=sku,
                error=f"未找到 SKU {sku} 的报价",
            )
        except Exception as e:
            return QuoteResult(
                supplier_name=self.name, sku=sku, error=str(e),
            )


# Scraper 注册表
SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "Supplier01Scraper": Supplier01Scraper,
    "Supplier02Scraper": Supplier02Scraper,
}


async def scrape_all_suppliers(
    alert_items,
    suppliers_config,
    max_concurrent: int = 3,
) -> dict[str, list[QuoteResult]]:
    """对所有低库存 SKU 向所有供应商抓取报价

    Args:
        alert_items: AlertItem 列表
        suppliers_config: SuppliersConfig
        max_concurrent: 最大并发浏览器数

    Returns:
        dict[sku, list[QuoteResult]]
    """
    from playwright.async_api import async_playwright

    results: dict[str, list[QuoteResult]] = {item.sku: [] for item in alert_items}
    semaphore = asyncio.Semaphore(max_concurrent)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)

        async def _scrape_supplier(supplier_key: str, supplier_entry: SupplierEntry):
            async with semaphore:
                scraper_cls = SCRAPER_REGISTRY.get(supplier_entry.scraper_class)
                if not scraper_cls:
                    logger.warning("未注册的爬虫类: %s", supplier_entry.scraper_class)
                    return

                scraper = scraper_cls(supplier_entry)
                context = await browser.new_context()
                page = await context.new_page()

                try:
                    if not await scraper.login(page):
                        for item in alert_items:
                            results[item.sku].append(QuoteResult(
                                supplier_name=supplier_entry.name,
                                sku=item.sku,
                                error="登录失败",
                            ))
                        return

                    for item in alert_items:
                        quote = await scraper.scrape_price(page, item.sku, item.name)
                        results[item.sku].append(quote)
                        logger.info(
                            "报价: %s @ %s = %s",
                            item.sku, supplier_entry.name,
                            f"¥{quote.unit_price}" if quote.success else quote.error,
                            extra={"sku": item.sku, "supplier": supplier_entry.name},
                        )
                finally:
                    await context.close()

        tasks = [
            _scrape_supplier(key, entry)
            for key, entry in suppliers_config.suppliers.items()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        await browser.close()

    return results
