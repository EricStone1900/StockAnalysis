"""阶段03-02的因子评估领域规则；所有收益标签必须晚于特征截止时间。"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from quant_research.factors import CandidateFactorRecord, FactorStatus

_PRECISION = Decimal("0.00000001")


class EvaluationWindow(BaseModel):
    """冻结的样本外评估窗口；首版不允许随机切分。"""

    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date
    cutoff_at: datetime

    @field_validator("cutoff_at")
    @classmethod
    def require_utc_cutoff(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("cutoff_at must use UTC")
        return value

    @model_validator(mode="after")
    def validate_date_range(self) -> EvaluationWindow:
        if self.end_date < self.start_date:
            raise ValueError("evaluation end_date must not precede start_date")
        if self.cutoff_at.date() != self.end_date:
            raise ValueError("evaluation cutoff_at date must equal end_date")
        return self


class TemporalSplitDefinition(BaseModel):
    """固定的时间切分；三段严格按时间递增且互不重叠。"""

    model_config = ConfigDict(frozen=True)

    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    test_start: date
    test_end: date

    @model_validator(mode="after")
    def validate_order(self) -> TemporalSplitDefinition:
        if not (
            self.train_start <= self.train_end < self.validation_start <= self.validation_end < self.test_start <= self.test_end
        ):
            raise ValueError("train, validation, and test windows must be ordered and non-overlapping")
        return self


class FactorReturnObservation(BaseModel):
    """同一截面的因子值和其后实现收益；不允许当前或未来收益充当标签。"""

    model_config = ConfigDict(frozen=True)

    security_id: str = Field(min_length=1)
    as_of_date: date
    feature_available_at: datetime
    forward_return_start: date
    forward_return_end: date
    factor_value: Decimal
    realized_return: Decimal

    @field_validator("feature_available_at")
    @classmethod
    def require_utc_available_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("feature_available_at must use UTC")
        return value

    @model_validator(mode="after")
    def reject_non_forward_label(self) -> FactorReturnObservation:
        if self.forward_return_start <= self.as_of_date:
            raise ValueError("forward return must start after the factor as_of_date")
        if self.forward_return_end < self.forward_return_start:
            raise ValueError("forward return end must not precede its start")
        return self


class TemporalSplitDataset(BaseModel):
    """已完成标签边界检查的三段数据；原始观测保持稳定排序。"""

    model_config = ConfigDict(frozen=True)

    factor_id: str
    factor_version: str
    data_version_id: str
    split: TemporalSplitDefinition
    train: tuple[FactorReturnObservation, ...]
    validation: tuple[FactorReturnObservation, ...]
    test: tuple[FactorReturnObservation, ...]
    canonical_content_hash: str


class WalkForwardConfig(BaseModel):
    """Walk-forward滚动窗口配置，单位为交易日。"""

    model_config = ConfigDict(frozen=True)

    train_size: int = Field(ge=1)
    validation_size: int = Field(ge=1)
    test_size: int = Field(ge=1)
    step_size: int = Field(ge=1)


class WalkForwardPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    trading_days: tuple[date, ...]
    config: WalkForwardConfig
    splits: tuple[TemporalSplitDefinition, ...] = Field(min_length=1)
    canonical_content_hash: str


class WalkForwardDataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    factor_id: str
    factor_version: str
    data_version_id: str
    plan: WalkForwardPlan
    windows: tuple[TemporalSplitDataset, ...]
    canonical_content_hash: str


class DailyInformationCoefficient(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of_date: date
    observation_count: int = Field(ge=2)
    information_coefficient: Decimal
    rank_information_coefficient: Decimal


class FactorEvaluationReport(BaseModel):
    """候选因子的最小可复现评估输出；尚不代表生产激活证据。"""

    model_config = ConfigDict(frozen=True)

    factor_id: str
    factor_version: str
    data_version_id: str
    evaluation_window: EvaluationWindow
    daily_information_coefficients: tuple[DailyInformationCoefficient, ...]
    canonical_content_hash: str
    eligibility: str = "RESEARCH_ONLY"


class QuantileEvaluationConfig(BaseModel):
    """分层收益的冻结配置；同值使用平均秩，因此不依赖传入行顺序。"""

    model_config = ConfigDict(frozen=True)

    quantile_count: int = Field(ge=2, le=20)


class DailyQuantilePerformance(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of_date: date
    bottom_quantile_return: Decimal
    top_quantile_return: Decimal
    long_short_return: Decimal
    top_quantile_member_count: int = Field(ge=1)
    top_quantile_replacement_rate: Decimal | None = None


class QuantileEvaluationReport(BaseModel):
    """分层收益与最高分组的相邻截面成分替换率；仅供研究候选判断。"""

    model_config = ConfigDict(frozen=True)

    factor_id: str
    factor_version: str
    data_version_id: str
    evaluation_window: EvaluationWindow
    config: QuantileEvaluationConfig
    daily_performance: tuple[DailyQuantilePerformance, ...]
    canonical_content_hash: str
    eligibility: str = "RESEARCH_ONLY"


class FactorValueObservation(BaseModel):
    """用于因子间相关性比较的同日同证券因子值。"""

    model_config = ConfigDict(frozen=True)

    security_id: str = Field(min_length=1)
    as_of_date: date
    feature_available_at: datetime
    factor_id: str = Field(min_length=1)
    factor_value: Decimal

    @field_validator("feature_available_at")
    @classmethod
    def require_utc_available_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("feature_available_at must use UTC")
        return value


class FactorCorrelation(BaseModel):
    model_config = ConfigDict(frozen=True)

    left_factor_id: str
    right_factor_id: str
    observation_count: int = Field(ge=2)
    correlation: Decimal


class FactorCorrelationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    evaluation_window: EvaluationWindow
    correlations: tuple[FactorCorrelation, ...]
    canonical_content_hash: str
    eligibility: str = "RESEARCH_ONLY"


class FactorStabilityReport(BaseModel):
    """每日 IC 的时间稳定性摘要；单日或零波动时 ICIR 保留为空。"""

    model_config = ConfigDict(frozen=True)

    factor_id: str
    factor_version: str
    data_version_id: str
    observation_day_count: int = Field(ge=1)
    mean_information_coefficient: Decimal
    information_coefficient_stddev: Decimal
    information_coefficient_ir: Decimal | None
    positive_information_coefficient_rate: Decimal
    canonical_content_hash: str
    eligibility: str = "RESEARCH_ONLY"


class FactorEvaluationError(ValueError):
    """评估输入不满足候选状态、PIT或截面完整性。"""


def evaluate_information_coefficients(
    candidate: CandidateFactorRecord,
    window: EvaluationWindow,
    observations: tuple[FactorReturnObservation, ...],
) -> FactorEvaluationReport:
    """按交易日计算 Pearson IC 与平均秩 RankIC，保持稳定排序和固定精度。"""
    if candidate.factor.status is not FactorStatus.CANDIDATE:
        raise FactorEvaluationError("only CANDIDATE factors can be evaluated")
    grouped = _group_cross_sections(candidate, window, observations)

    daily: list[DailyInformationCoefficient] = []
    for as_of_date in sorted(grouped):
        cross_section = sorted(grouped[as_of_date], key=lambda row: row.security_id)
        if len({row.security_id for row in cross_section}) != len(cross_section):
            raise FactorEvaluationError("a security may appear only once in each evaluation cross-section")
        if len(cross_section) < 2:
            raise FactorEvaluationError("each evaluation cross-section requires at least two securities")
        factor_values = [row.factor_value for row in cross_section]
        returns = [row.realized_return for row in cross_section]
        daily.append(
            DailyInformationCoefficient(
                as_of_date=as_of_date,
                observation_count=len(cross_section),
                information_coefficient=_quantize(_pearson(factor_values, returns)),
                rank_information_coefficient=_quantize(_pearson(_average_ranks(factor_values), _average_ranks(returns))),
            )
        )
    stable_daily = tuple(daily)
    canonical = json.dumps(
        {
            "factorId": candidate.factor.factor_id,
            "factorVersion": candidate.factor.version,
            "dataVersionId": candidate.data_version_id,
            "window": window.model_dump(mode="json"),
            "daily": [item.model_dump(mode="json") for item in stable_daily],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return FactorEvaluationReport(
        factor_id=candidate.factor.factor_id,
        factor_version=candidate.factor.version,
        data_version_id=candidate.data_version_id,
        evaluation_window=window,
        daily_information_coefficients=stable_daily,
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )


def split_factor_observations(
    candidate: CandidateFactorRecord,
    split: TemporalSplitDefinition,
    observations: tuple[FactorReturnObservation, ...],
) -> TemporalSplitDataset:
    """按日期切分并执行标签完整性检查；跨边界的收益窗口直接拒绝。"""
    if candidate.factor.status is not FactorStatus.CANDIDATE:
        raise FactorEvaluationError("only CANDIDATE factors can be split")
    if not observations:
        raise FactorEvaluationError("time split requires observations")
    buckets: dict[str, list[FactorReturnObservation]] = {"train": [], "validation": [], "test": []}
    for observation in observations:
        if split.train_start <= observation.as_of_date <= split.train_end:
            name, segment_end = "train", split.train_end
        elif split.validation_start <= observation.as_of_date <= split.validation_end:
            name, segment_end = "validation", split.validation_end
        elif split.test_start <= observation.as_of_date <= split.test_end:
            name, segment_end = "test", split.test_end
        else:
            raise FactorEvaluationError("observation as_of_date is outside the frozen time split")
        if observation.forward_return_end > segment_end:
            raise FactorEvaluationError("forward return label crosses a temporal split boundary")
        buckets[name].append(observation)
    if any(not values for values in buckets.values()):
        raise FactorEvaluationError("train, validation, and test splits must all contain observations")
    stable = {
        name: tuple(sorted(values, key=lambda row: (row.as_of_date, row.security_id)))
        for name, values in buckets.items()
    }
    canonical = json.dumps(
        {
            "factorId": candidate.factor.factor_id,
            "factorVersion": candidate.factor.version,
            "dataVersionId": candidate.data_version_id,
            "split": split.model_dump(mode="json"),
            "observations": {
                name: [item.model_dump(mode="json") for item in values]
                for name, values in stable.items()
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return TemporalSplitDataset(
        factor_id=candidate.factor.factor_id,
        factor_version=candidate.factor.version,
        data_version_id=candidate.data_version_id,
        split=split,
        train=stable["train"],
        validation=stable["validation"],
        test=stable["test"],
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )


def build_walk_forward_plan(
    trading_days: tuple[date, ...], config: WalkForwardConfig
) -> WalkForwardPlan:
    """从已排序交易日日历生成固定、非随机的滚动窗口。"""
    if not trading_days or tuple(sorted(set(trading_days))) != trading_days:
        raise FactorEvaluationError("trading_days must be non-empty, unique, and sorted")
    window_size = config.train_size + config.validation_size + config.test_size
    if len(trading_days) < window_size:
        raise FactorEvaluationError("trading calendar is shorter than one walk-forward window")
    splits: list[TemporalSplitDefinition] = []
    start = 0
    while start + window_size <= len(trading_days):
        train_end = start + config.train_size - 1
        validation_end = train_end + config.validation_size
        test_end = validation_end + config.test_size
        splits.append(
            TemporalSplitDefinition(
                train_start=trading_days[start],
                train_end=trading_days[train_end],
                validation_start=trading_days[train_end + 1],
                validation_end=trading_days[validation_end],
                test_start=trading_days[validation_end + 1],
                test_end=trading_days[test_end - 1],
            )
        )
        start += config.step_size
    canonical = json.dumps(
        {
            "tradingDays": [item.isoformat() for item in trading_days],
            "config": config.model_dump(mode="json"),
            "splits": [item.model_dump(mode="json") for item in splits],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return WalkForwardPlan(
        trading_days=trading_days,
        config=config,
        splits=tuple(splits),
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )


def split_walk_forward_observations(
    candidate: CandidateFactorRecord,
    plan: WalkForwardPlan,
    observations: tuple[FactorReturnObservation, ...],
) -> WalkForwardDataset:
    """对每个滚动窗口复用边界检查，确保窗口之间不共享越界标签。"""
    if candidate.factor.status is not FactorStatus.CANDIDATE:
        raise FactorEvaluationError("only CANDIDATE factors can use walk-forward validation")
    windows = tuple(split_factor_observations(candidate, split, observations) for split in plan.splits)
    canonical = json.dumps(
        {
            "factorId": candidate.factor.factor_id,
            "factorVersion": candidate.factor.version,
            "dataVersionId": candidate.data_version_id,
            "planHash": plan.canonical_content_hash,
            "windowHashes": [item.canonical_content_hash for item in windows],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return WalkForwardDataset(
        factor_id=candidate.factor.factor_id,
        factor_version=candidate.factor.version,
        data_version_id=candidate.data_version_id,
        plan=plan,
        windows=windows,
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )


def evaluate_quantile_performance(
    candidate: CandidateFactorRecord,
    window: EvaluationWindow,
    config: QuantileEvaluationConfig,
    observations: tuple[FactorReturnObservation, ...],
) -> QuantileEvaluationReport:
    """计算首尾分层收益及最高分组的替换率，不把研究结果升级为生产资格。"""
    grouped = _group_cross_sections(candidate, window, observations)
    previous_top_members: frozenset[str] | None = None
    daily: list[DailyQuantilePerformance] = []
    for as_of_date in sorted(grouped):
        cross_section = grouped[as_of_date]
        if len(cross_section) < config.quantile_count:
            raise FactorEvaluationError("evaluation cross-section is smaller than the configured quantile count")
        buckets = _quantile_buckets(cross_section, config.quantile_count)
        bottom = buckets[1]
        top = buckets[config.quantile_count]
        top_members = frozenset(row.security_id for row in top)
        replacement_rate = None
        if previous_top_members is not None:
            replacement_rate = _quantize(
                Decimal(1) - Decimal(len(previous_top_members & top_members)) / Decimal(len(previous_top_members | top_members))
            )
        bottom_return = _quantize(_mean([row.realized_return for row in bottom]))
        top_return = _quantize(_mean([row.realized_return for row in top]))
        daily.append(
            DailyQuantilePerformance(
                as_of_date=as_of_date,
                bottom_quantile_return=bottom_return,
                top_quantile_return=top_return,
                long_short_return=_quantize(top_return - bottom_return),
                top_quantile_member_count=len(top_members),
                top_quantile_replacement_rate=replacement_rate,
            )
        )
        previous_top_members = top_members
    stable_daily = tuple(daily)
    canonical = json.dumps(
        {
            "factorId": candidate.factor.factor_id,
            "factorVersion": candidate.factor.version,
            "dataVersionId": candidate.data_version_id,
            "window": window.model_dump(mode="json"),
            "config": config.model_dump(mode="json"),
            "daily": [item.model_dump(mode="json") for item in stable_daily],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return QuantileEvaluationReport(
        factor_id=candidate.factor.factor_id,
        factor_version=candidate.factor.version,
        data_version_id=candidate.data_version_id,
        evaluation_window=window,
        config=config,
        daily_performance=stable_daily,
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )


def evaluate_factor_correlation(
    window: EvaluationWindow,
    observations: tuple[FactorValueObservation, ...],
) -> FactorCorrelationReport:
    """在同日同证券交集上计算各因子 Pearson 相关性。"""
    if not observations:
        raise FactorEvaluationError("factor correlation requires observations")
    keyed: dict[tuple[date, str], dict[str, FactorValueObservation]] = defaultdict(dict)
    for observation in observations:
        if not window.start_date <= observation.as_of_date <= window.end_date:
            raise FactorEvaluationError("correlation observation is outside the frozen evaluation window")
        if observation.feature_available_at > window.cutoff_at:
            raise FactorEvaluationError("correlation feature was unavailable at the frozen evaluation cutoff")
        key = (observation.as_of_date, observation.security_id)
        if observation.factor_id in keyed[key]:
            raise FactorEvaluationError("a factor may appear only once per security and day")
        keyed[key][observation.factor_id] = observation
    factor_ids = sorted({factor_id for values in keyed.values() for factor_id in values})
    correlations: list[FactorCorrelation] = []
    for index, left_factor_id in enumerate(factor_ids):
        for right_factor_id in factor_ids[index + 1 :]:
            pairs = [
                (values[left_factor_id].factor_value, values[right_factor_id].factor_value)
                for values in keyed.values()
                if left_factor_id in values and right_factor_id in values
            ]
            if len(pairs) < 2:
                raise FactorEvaluationError("factor correlation requires two paired observations")
            left = [pair[0] for pair in pairs]
            right = [pair[1] for pair in pairs]
            correlations.append(
                FactorCorrelation(
                    left_factor_id=left_factor_id,
                    right_factor_id=right_factor_id,
                    observation_count=len(pairs),
                    correlation=_quantize(_pearson(left, right)),
                )
            )
    stable = tuple(correlations)
    canonical = json.dumps(
        {
            "window": window.model_dump(mode="json"),
            "correlations": [item.model_dump(mode="json") for item in stable],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return FactorCorrelationReport(
        evaluation_window=window,
        correlations=stable,
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )


def evaluate_factor_stability(report: FactorEvaluationReport) -> FactorStabilityReport:
    """从每日 IC 报告计算均值、标准差、ICIR和正 IC 比率。"""
    daily = report.daily_information_coefficients
    values = [item.information_coefficient for item in daily]
    mean = _mean(values)
    variance = _mean([(value - mean) ** 2 for value in values])
    stddev = variance.sqrt()
    icir = None if stddev == 0 else mean / stddev
    positive_rate = Decimal(sum(value > 0 for value in values)) / Decimal(len(values))
    payload = {
        "factorId": report.factor_id,
        "factorVersion": report.factor_version,
        "dataVersionId": report.data_version_id,
        "observationDayCount": len(values),
        "meanInformationCoefficient": format(_quantize(mean), "f"),
        "informationCoefficientStddev": format(_quantize(stddev), "f"),
        "informationCoefficientIr": None if icir is None else format(_quantize(icir), "f"),
        "positiveInformationCoefficientRate": format(_quantize(positive_rate), "f"),
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return FactorStabilityReport(
        factor_id=report.factor_id,
        factor_version=report.factor_version,
        data_version_id=report.data_version_id,
        observation_day_count=len(values),
        mean_information_coefficient=_quantize(mean),
        information_coefficient_stddev=_quantize(stddev),
        information_coefficient_ir=None if icir is None else _quantize(icir),
        positive_information_coefficient_rate=_quantize(positive_rate),
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )


def _group_cross_sections(
    candidate: CandidateFactorRecord,
    window: EvaluationWindow,
    observations: tuple[FactorReturnObservation, ...],
) -> dict[date, list[FactorReturnObservation]]:
    if candidate.factor.status is not FactorStatus.CANDIDATE:
        raise FactorEvaluationError("only CANDIDATE factors can be evaluated")
    if not observations:
        raise FactorEvaluationError("factor evaluation requires observations")
    grouped: dict[date, list[FactorReturnObservation]] = defaultdict(list)
    for observation in observations:
        if not window.start_date <= observation.as_of_date <= window.end_date:
            raise FactorEvaluationError("observation as_of_date is outside the frozen evaluation window")
        if observation.feature_available_at > window.cutoff_at:
            raise FactorEvaluationError("feature was unavailable at the frozen evaluation cutoff")
        grouped[observation.as_of_date].append(observation)
    for cross_section in grouped.values():
        cross_section.sort(key=lambda row: row.security_id)
        if len({row.security_id for row in cross_section}) != len(cross_section):
            raise FactorEvaluationError("a security may appear only once in each evaluation cross-section")
    return grouped


def _quantile_buckets(
    cross_section: list[FactorReturnObservation], quantile_count: int
) -> dict[int, list[FactorReturnObservation]]:
    ranks = _average_ranks([row.factor_value for row in cross_section])
    row_buckets: dict[int, list[FactorReturnObservation]] = defaultdict(list)
    count = Decimal(len(cross_section))
    for row, rank in zip(cross_section, ranks, strict=True):
        bucket = int((rank * quantile_count / count).to_integral_value(rounding="ROUND_CEILING"))
        row_buckets[bucket].append(row)
    if 1 not in row_buckets or quantile_count not in row_buckets:
        raise FactorEvaluationError("quantile assignment produced an empty endpoint bucket")
    return row_buckets


def _pearson(left: list[Decimal], right: list[Decimal]) -> Decimal:
    count = Decimal(len(left))
    left_mean = sum(left, Decimal(0)) / count
    right_mean = sum(right, Decimal(0)) / count
    numerator = sum(
        ((x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=True)), Decimal(0)
    )
    left_sum = sum(((value - left_mean) ** 2 for value in left), Decimal(0))
    right_sum = sum(((value - right_mean) ** 2 for value in right), Decimal(0))
    if left_sum == 0 or right_sum == 0:
        raise FactorEvaluationError("information coefficient is undefined for a constant cross-section")
    return numerator / (left_sum * right_sum).sqrt()


def _average_ranks(values: list[Decimal]) -> list[Decimal]:
    positions: dict[Decimal, list[int]] = defaultdict(list)
    for position, value in enumerate(sorted(values), start=1):
        positions[value].append(position)
    ranks = {value: sum(group) / Decimal(len(group)) for value, group in positions.items()}
    return [ranks[value] for value in values]


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / Decimal(len(values))


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_PRECISION, rounding=ROUND_HALF_EVEN)
