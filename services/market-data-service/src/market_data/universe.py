from .domain import Exchange, SecurityId

SSE_A_SHARE_PREFIXES = ("600", "601", "603", "605", "688")
SZSE_A_SHARE_PREFIXES = ("000", "001", "002", "003", "300", "301")


def is_stage03_cn_a_equity(security_id: SecurityId) -> bool:
    """首期股票池仅含沪深普通A股，明确排除指数、基金/ETF及北交所。"""
    if security_id.exchange is Exchange.SSE:
        return security_id.symbol.startswith(SSE_A_SHARE_PREFIXES)
    if security_id.exchange is Exchange.SZSE:
        return security_id.symbol.startswith(SZSE_A_SHARE_PREFIXES)
    return False
