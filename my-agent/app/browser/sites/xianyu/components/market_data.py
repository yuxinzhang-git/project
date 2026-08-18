import re
from statistics import median

from ..errors import XianyuPageStructureError


class XianyuMarketData:
    """Parse public listing text and produce a conservative price summary."""

    PRICE_PATTERNS = (
        re.compile(r"(?:¥|￥|RMB)\s*([0-9]+(?:\.[0-9]+)?)\s*(万)?", re.I),
        re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(万|元)"),
    )
    CONDITION_PATTERN = re.compile(r"(全新|九五新|九成新|八成新|七成新|成色[^\s，。；;]{0,8}|\d{2,3}新)")

    @classmethod
    def parse_price(cls, text):
        for pattern in cls.PRICE_PATTERNS:
            match = pattern.search(text or "")
            if not match:
                continue
            value = float(match.group(1))
            if match.group(2) == "万":
                value *= 10_000
            if 0 < value <= 10_000_000:
                return round(value, 2)
        return None

    @classmethod
    def parse_condition(cls, text):
        match = cls.CONDITION_PATTERN.search(text or "")
        return match.group(1) if match else None

    @classmethod
    def normalize_item(cls, item):
        card_text = item.get("card_text") or item.get("text") or ""
        return {
            "title": item.get("text") or "untitled item",
            "price": cls.parse_price(card_text),
            "condition": cls.parse_condition(card_text),
            "raw_text": card_text[:500],
        }

    @staticmethod
    def _percentile(values, ratio):
        ordered = sorted(values)
        return ordered[round((len(ordered) - 1) * ratio)]

    @classmethod
    def estimate(cls, items):
        normalized = [item if "price" in item else cls.normalize_item(item) for item in items]
        priced = [item for item in normalized if isinstance(item.get("price"), (int, float)) and item["price"] > 0]
        if not priced:
            raise XianyuPageStructureError("Xianyu listing prices were not found; page structure may have changed")

        prices = [float(item["price"]) for item in priced]
        center = median(prices)
        if len(prices) >= 3:
            filtered = [item for item in priced if center * 0.25 <= item["price"] <= center * 4]
        else:
            filtered = priced
        if not filtered:
            raise XianyuPageStructureError("all Xianyu listing prices were rejected as abnormal")
        valid_prices = [float(item["price"]) for item in filtered]
        return {
            "total_count": len(normalized),
            "sample_count": len(filtered),
            "priced_count": len(priced),
            "missing_price_count": len(normalized) - len(priced),
            "outlier_count": len(priced) - len(filtered),
            "min_price": round(min(valid_prices), 2),
            "max_price": round(max(valid_prices), 2),
            "quick_sale_price": round(cls._percentile(valid_prices, 0.25) / 10) * 10,
            "recommended_price": round(median(valid_prices) / 10) * 10,
            "high_price": round(cls._percentile(valid_prices, 0.75) / 10) * 10,
            "items": filtered,
            "disclaimer": "仅基于当前公开样本估算，不代表最终成交价；请人工核验成色、配件和交易风险。",
        }
