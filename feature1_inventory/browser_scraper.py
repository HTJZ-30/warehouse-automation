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


async def scrape_1688(alert_items, max_concurrent: int = 2) -> dict[str, list[QuoteResult]]:
    """从 1688 公开搜索页抓取报价 (无需登录)

    1688 有滑块验证码反爬机制，headless 浏览器可能被拦截。
    当抓取失败时自动回退到模拟报价数据，保证系统流程完整。

    Args:
        alert_items: AlertItem 列表
        max_concurrent: 最大并发数

    Returns:
        dict[sku, list[QuoteResult]]
    """
    from playwright.async_api import async_playwright
    import re

    results: dict[str, list[QuoteResult]] = {item.sku: [] for item in alert_items}
    semaphore = asyncio.Semaphore(max_concurrent)
    captcha_detected = False

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)

        async def _search_item(item):
            nonlocal captcha_detected
            async with semaphore:
                # 如果已检测到验证码，跳过后续请求
                if captcha_detected:
                    return

                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()

                try:
                    search_url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={item.name}"
                    logger.info("1688 搜索: %s (%s)", item.name, item.sku)

                    await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(3000)

                    # 检测验证码页面
                    page_text = await page.inner_text("body")
                    if "滑块" in page_text or "验证" in page_text:
                        logger.warning("1688 触发验证码，将使用模拟报价数据")
                        captcha_detected = True
                        return

                    # 滚动触发懒加载
                    await page.evaluate("window.scrollBy(0, 500)")
                    await page.wait_for_timeout(1000)

                    # 尝试多种选择器匹配 1688 搜索结果
                    offers = await page.query_selector_all(
                        '[class*="offer-list"] [class*="offer-item"], '
                        '.sm-offer-item, .card-container, '
                        '[class*="offercard"], [class*="OfferCard"]'
                    )
                    if not offers:
                        offers = await page.query_selector_all('[class*="price"]')

                    found_count = 0
                    for offer in offers[:3]:
                        try:
                            price_el = await offer.query_selector(
                                '[class*="price"], .sm-offer-priceNum, [class*="Price"]'
                            )
                            title_el = await offer.query_selector(
                                '[class*="title"], .sm-offer-title, [class*="Title"]'
                            )

                            price_text = await price_el.inner_text() if price_el else ""
                            title_text = await title_el.inner_text() if title_el else ""

                            price_match = re.search(r'(\d+\.?\d*)', price_text.replace(",", ""))
                            if price_match:
                                price = float(price_match.group(1))
                                supplier_name = f"1688商家{found_count + 1}"
                                results[item.sku].append(QuoteResult(
                                    supplier_name=supplier_name,
                                    sku=item.sku,
                                    unit_price=price,
                                    currency="CNY",
                                    quote_url=search_url,
                                ))
                                found_count += 1
                                logger.info(
                                    "  报价: %s = ¥%.2f (%s)",
                                    item.sku, price, title_text[:30],
                                    extra={"sku": item.sku, "supplier": supplier_name},
                                )
                        except Exception:
                            continue

                    if found_count == 0:
                        results[item.sku].append(QuoteResult(
                            supplier_name="1688",
                            sku=item.sku,
                            error=f"未找到 '{item.name}' 的报价",
                        ))

                except Exception as e:
                    logger.error("1688 搜索失败: %s — %s", item.sku, e)
                    results[item.sku].append(QuoteResult(
                        supplier_name="1688",
                        sku=item.sku,
                        error=str(e),
                    ))
                finally:
                    await context.close()

        tasks = [_search_item(item) for item in alert_items]
        await asyncio.gather(*tasks, return_exceptions=True)
        await browser.close()

    # 如果触发验证码或全部失败，回退到模拟报价
    all_empty = all(len(qs) == 0 or all(not q.success for q in qs) for qs in results.values())
    if captcha_detected or all_empty:
        logger.info("使用模拟报价数据（1688 反爬机制阻止了自动抓取）")
        results = _generate_demo_quotes(alert_items)

    return results


def _generate_demo_quotes(alert_items) -> dict[str, list[QuoteResult]]:
    """生成模拟报价数据，用于演示和测试

    基于产品名称生成合理的模拟价格区间。
    """
    import random

    # 产品基础价格参考（模拟）
    price_hints = {
        "螺丝": (0.05, 0.30),
        "螺母": (0.03, 0.20),
        "垫圈": (0.02, 0.10),
        "轴承": (15.0, 80.0),
        "弹簧": (0.50, 5.0),
        "密封": (1.0, 10.0),
        "胶带": (3.0, 15.0),
    }
    default_range = (1.0, 50.0)

    suppliers = ["东莞精密五金", "上海标准件", "深圳宏达金属"]
    results: dict[str, list[QuoteResult]] = {}

    for item in alert_items:
        quotes = []
        # 根据产品名匹配价格区间
        low, high = default_range
        for keyword, (lo, hi) in price_hints.items():
            if keyword in item.name:
                low, high = lo, hi
                break

        for i, supplier in enumerate(suppliers):
            price = round(random.uniform(low, high), 2)
            delivery = random.randint(3, 14)
            quotes.append(QuoteResult(
                supplier_name=f"{supplier}（模拟）",
                sku=item.sku,
                unit_price=price,
                currency="CNY",
                delivery_days=delivery,
                min_order_qty=random.choice([100, 500, 1000]),
                quote_url=f"https://demo.example.com/{item.sku}",
            ))
            logger.info(
                "  模拟报价: %s @ %s = CNY %.2f, %d天",
                item.sku, supplier, price, delivery,
                extra={"sku": item.sku, "supplier": supplier},
            )

        results[item.sku] = quotes

    return results


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
