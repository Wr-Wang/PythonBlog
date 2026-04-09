"""

东八区（Asia/Shanghai）时间工具。



语法要点：

- zoneinfo.ZoneInfo：PEP 615，使用 IANA 时区库（Windows 需安装 tzdata 包）。

- datetime.now(tz)：带时区的当前时间；replace(tzinfo=None) 去掉 tz 得到 naive，与 DATETIME2 存储习惯一致。

"""

from datetime import datetime  # 标准库

from zoneinfo import ZoneInfo  # 标准库（Python 3.9+）：IANA 时区



TZ_SHANGHAI = ZoneInfo("Asia/Shanghai")  # 中国标准时间，无夏令时





def now_shanghai_naive() -> datetime:

    """返回「当前东八区墙上时间」的 naive datetime，供 SQLAlchemy 默认值使用。"""

    return datetime.now(TZ_SHANGHAI).replace(tzinfo=None)  # 存库不含 +08:00 信息，约定即为本地业务时间





def format_dt_yyyy_mm_dd_hh_mm_ss_fff(dt: datetime | None) -> str:

    """后台列表/详情用：yyyy-MM-dd HH:mm:ss.fff（毫秒 3 位）。"""

    if dt is None:

        return ""

    # 库中 naive 约定为东八区墙上时间，不做时区转换

    ms = dt.microsecond // 1000

    return f"{dt.strftime('%Y-%m-%d %H:%M:%S')}.{ms:03d}"


