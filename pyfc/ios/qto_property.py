from dataclasses import dataclass
from typing import Any, Callable

from pyfc.models.ifc_types import IfcEntityType
from pyfc.models.value import IfcUnitType
from pyfc.utils import convert


@dataclass
class QtoConfig:
    """
    Configuration class for Qto properties.
    Contains the name of the property and its value.
    """

    qto_type: IfcEntityType
    ifc_attr: str
    convert_func: Callable[[Any], float | None]
    error_msg_value_type: str


def _convert_count_value(value: Any) -> float | None:
    int_value = convert.as_int(value)
    if int_value is not None:
        return int_value
    float_value = convert.as_float(value)
    if float_value is not None:
        return float_value
    return None


def _convert_time_value(value: Any) -> float | None:
    return convert.as_float(value)


QUANTITY_CONFIG: dict[IfcUnitType, QtoConfig] = {
    IfcUnitType.LENGTH: QtoConfig(
        qto_type=IfcEntityType.QUANTITY_LENGTH,
        ifc_attr="LengthValue",
        convert_func=convert.as_float,
        error_msg_value_type="Real",
    ),
    IfcUnitType.AREA: QtoConfig(
        qto_type=IfcEntityType.QUANTITY_AREA,
        ifc_attr="AreaValue",
        convert_func=convert.as_float,
        error_msg_value_type="Real",
    ),
    IfcUnitType.VOLUME: QtoConfig(
        qto_type=IfcEntityType.QUANTITY_VOLUME,
        ifc_attr="VolumeValue",
        convert_func=convert.as_float,
        error_msg_value_type="Real",
    ),
    IfcUnitType.MASS: QtoConfig(
        qto_type=IfcEntityType.QUANTITY_WEIGHT,
        ifc_attr="WeightValue",
        convert_func=convert.as_float,
        error_msg_value_type="Real",
    ),
    IfcUnitType.COUNT: QtoConfig(
        qto_type=IfcEntityType.QUANTITY_COUNT,
        ifc_attr="CountValue",
        convert_func=_convert_count_value,
        error_msg_value_type="Integer or Real",
    ),
    IfcUnitType.TIME: QtoConfig(
        qto_type=IfcEntityType.QUANTITY_TIME,
        ifc_attr="TimeValue",
        convert_func=_convert_time_value,
        error_msg_value_type="Real",
    ),
}
