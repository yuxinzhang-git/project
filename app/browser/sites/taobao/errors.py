class TaobaoError(RuntimeError):
    """Base error for Taobao operations."""


class TaobaoPageStructureError(TaobaoError):
    pass


class TaobaoLoginRequiredError(TaobaoError):
    pass


class TaobaoRiskControlError(TaobaoError):
    pass


class TaobaoBrowserError(TaobaoError):
    pass
