from sqlglot import TokenType
import typing as t

from sqlglot import exp
from sqlglot.dialects.dialect import build_formatted_time
from sqlglot.dialects.mysql import MySQL
from sqlglot.helper import seq_get


class SingleStore(MySQL):
    SUPPORTS_ORDER_BY_ALL = True

    TIME_MAPPING: t.Dict[str, str] = {
        "D": "%u",  # Day of week (1-7)
        "DD": "%d",  # day of month (01-31)
        "DY": "%a",  # abbreviated name of day
        "HH": "%I",  # Hour of day (01-12)
        "HH12": "%I",  # alias for HH
        "HH24": "%H",  # Hour of day (00-23)
        "MI": "%M",  # Minute (00-59)
        "MM": "%m",  # Month (01-12; January = 01)
        "MON": "%b",  # Abbreviated name of month
        "MONTH": "%B",  # Name of month
        "SS": "%S",  # Second (00-59)
        "RR": "%y",  # 15
        "YY": "%y",  # 15
        "YYYY": "%Y",  # 2015
        "FF6": "%f",  # only 6 digits are supported in python formats
    }

    class Tokenizer(MySQL.Tokenizer):
        BYTE_STRINGS = [("e'", "'"), ("E'", "'")]

        KEYWORDS = {
            **MySQL.Tokenizer.KEYWORDS,
            "BSON": TokenType.JSONB,
            "GEOGRAPHYPOINT": TokenType.GEOGRAPHYPOINT,
            ":>": TokenType.COLON_GT,
            "!:>": TokenType.NCOLON_GT,
            "::$": TokenType.DCOLONDOLLAR,
            "::%": TokenType.DCOLONPERCENT,
        }

    class Parser(MySQL.Parser):
        FUNCTIONS = {
            **MySQL.Parser.FUNCTIONS,
            "TO_DATE": build_formatted_time(exp.TsOrDsToDate, "singlestore"),
            "TO_TIMESTAMP": build_formatted_time(exp.StrToTime, "singlestore"),
            "TO_CHAR": build_formatted_time(exp.ToChar, "singlestore"),
            "STR_TO_DATE": build_formatted_time(exp.StrToDate, "mysql"),
            "DATE_FORMAT": build_formatted_time(exp.TimeToStr, "mysql"),
            "TIME_FORMAT": lambda args: exp.TimeToStr(
                # The first argument is converted to TIME(6)
                # This is needed because exp.TimeToStr is converted to DATE_FORMAT
                # which interprets the first argument as DATETIME and fails to parse
                # string literals like '12:05:47' without a date part.
                this=exp.Cast(
                    this=seq_get(args, 0),
                    to=exp.DataType.build(
                        exp.DataType.Type.TIME,
                        expressions=[exp.DataTypeParam(this=exp.Literal.number(6))],
                    ),
                ),
                format=MySQL.format_time(seq_get(args, 1)),
            ),
        }

    class Generator(MySQL.Generator):
        TRANSFORMS = {
            **MySQL.Generator.TRANSFORMS,
            exp.TsOrDsToDate: lambda self, e: self.func("TO_DATE", e.this, self.format_time(e)),
            exp.StrToTime: lambda self, e: self.func("TO_TIMESTAMP", e.this, self.format_time(e)),
            exp.ToChar: lambda self, e: self.func("TO_CHAR", e.this, self.format_time(e)),
            exp.StrToDate: lambda self, e: self.func(
                "STR_TO_DATE",
                e.this,
                self.format_time(
                    e,
                    inverse_time_mapping=MySQL.INVERSE_TIME_MAPPING,
                    inverse_time_trie=MySQL.INVERSE_TIME_TRIE,
                ),
            ),
            exp.TimeToStr: lambda self, e: self.func(
                "DATE_FORMAT",
                e.this,
                self.format_time(
                    e,
                    inverse_time_mapping=MySQL.INVERSE_TIME_MAPPING,
                    inverse_time_trie=MySQL.INVERSE_TIME_TRIE,
                ),
            ),
        }

        # https://docs.singlestore.com/cloud/reference/sql-reference/restricted-keywords/list-of-restricted-keywords/
        RESERVED_KEYWORDS = {
            "abs",
            "absolute",
            "access",
            "account",
            "acos",
            "action",
            "add",
            "adddate",
            "addtime",
            "admin",
            "aes_decrypt",
            "aes_encrypt",
            "after",
            "against",
            "aggregate",
            "aggregates",
            "aggregator",
            "aggregator_id",
            "aggregator_plan_hash",
            "aggregators",
            "algorithm",
            "all",
            "also",
            "alter",
            "always",
            "analyse",
            "analyze",
            "and",
            "anti_join",
            "any",
            "any_value",
            "approx_count_distinct",
            "approx_count_distinct_accumulate",
            "approx_count_distinct_combine",
            "approx_count_distinct_estimate",
            "approx_geography_intersects",
            "approx_percentile",
            "arghistory",
            "arrange",
            "arrangement",
            "array",
            "as",
            "asc",
            "ascii",
            "asensitive",
            "asin",
            "asm",
            "assertion",
            "assignment",
            "ast",
            "asymmetric",
            "async",
            "at",
            "atan",
            "atan2",
            "attach",
            "attribute",
            "authorization",
            "auto",
            "auto_increment",
            "auto_reprovision",
            "autostats",
            "autostats_cardinality_mode",
            "autostats_enabled",
            "autostats_histogram_mode",
            "autostats_sampling",
            "availability",
            "avg",
            "avg_row_length",
            "avro",
            "azure",
            "background",
            "_background_threads_for_cleanup",
            "backup",
            "backup_history",
            "backup_id",
            "backward",
            "batch",
            "batches",
            "batch_interval",
            "_batch_size_limit",
            "before",
            "begin",
            "between",
            "bigint",
            "bin",
            "binary",
            "_binary",
            "bit",
            "bit_and",
            "bit_count",
            "bit_or",
            "bit_xor",
            "blob",
            "bool",
            "boolean",
            "bootstrap",
            "both",
            "_bt",
            "btree",
            "bucket_count",
            "by",
            "byte",
            "byte_length",
            "cache",
            "call",
            "call_for_pipeline",
            "called",
            "capture",
            "cascade",
            "cascaded",
            "case",
            "cast",
            "catalog",
            "ceil",
            "ceiling",
            "chain",
            "change",
            "char",
            "character",
            "characteristics",
            "character_length",
            "char_length",
            "charset",
            "check",
            "checkpoint",
            "_check_can_connect",
            "_check_consistency",
            "checksum",
            "_checksum",
            "class",
            "clear",
            "client",
            "client_found_rows",
            "close",
            "cluster",
            "clustered",
            "cnf",
            "coalesce",
            "coercibility",
            "collate",
            "collation",
            "collect",
            "column",
            "columnar",
            "columns",
            "columnstore",
            "columnstore_segment_rows",
            "comment",
            "comments",
            "commit",
            "committed",
            "_commit_log_tail",
            "committed",
            "compact",
            "compile",
            "compressed",
            "compression",
            "concat",
            "concat_ws",
            "concurrent",
            "concurrently",
            "condition",
            "configuration",
            "connection",
            "connection_id",
            "connections",
            "config",
            "constraint",
            "constraints",
            "content",
            "continue",
            "_continue_replay",
            "conv",
            "conversion",
            "convert",
            "convert_tz",
            "copy",
            "_core",
            "cos",
            "cost",
            "cot",
            "count",
            "create",
            "credentials",
            "cross",
            "cube",
            "csv",
            "cume_dist",
            "curdate",
            "current",
            "current_catalog",
            "current_date",
            "current_role",
            "current_schema",
            "current_security_groups",
            "current_security_roles",
            "current_time",
            "current_timestamp",
            "current_user",
            "cursor",
            "curtime",
            "cycle",
            "data",
            "database",
            "databases",
            "date",
            "date_add",
            "datediff",
            "date_format",
            "date_sub",
            "date_trunc",
            "datetime",
            "day",
            "day_hour",
            "day_microsecond",
            "day_minute",
            "dayname",
            "dayofmonth",
            "dayofweek",
            "dayofyear",
            "day_second",
            "deallocate",
            "dec",
            "decimal",
            "declare",
            "decode",
            "default",
            "defaults",
            "deferrable",
            "deferred",
            "defined",
            "definer",
            "degrees",
            "delayed",
            "delay_key_write",
            "delete",
            "delimiter",
            "delimiters",
            "dense_rank",
            "desc",
            "describe",
            "detach",
            "deterministic",
            "dictionary",
            "differential",
            "directory",
            "disable",
            "discard",
            "_disconnect",
            "disk",
            "distinct",
            "distinctrow",
            "distributed_joins",
            "div",
            "do",
            "document",
            "domain",
            "dot_product",
            "double",
            "drop",
            "_drop_profile",
            "dual",
            "dump",
            "duplicate",
            "dynamic",
            "earliest",
            "each",
            "echo",
            "election",
            "else",
            "elseif",
            "elt",
            "enable",
            "enclosed",
            "encoding",
            "encrypted",
            "end",
            "engine",
            "engines",
            "enum",
            "errors",
            "escape",
            "escaped",
            "estimate",
            "euclidean_distance",
            "event",
            "events",
            "except",
            "exclude",
            "excluding",
            "exclusive",
            "execute",
            "exists",
            "exit",
            "exp",
            "explain",
            "extended",
            "extension",
            "external",
            "external_host",
            "external_port",
            "extract",
            "extractor",
            "extractors",
            "extra_join",
            "_failover",
            "failed_login_attempts",
            "failure",
            "false",
            "family",
            "fault",
            "fetch",
            "field",
            "fields",
            "file",
            "files",
            "fill",
            "first",
            "first_value",
            "fix_alter",
            "fixed",
            "float",
            "float4",
            "float8",
            "floor",
            "flush",
            "following",
            "for",
            "force",
            "force_compiled_mode",
            "force_interpreter_mode",
            "foreground",
            "foreign",
            "format",
            "forward",
            "found_rows",
            "freeze",
            "from",
            "from_base64",
            "from_days",
            "from_unixtime",
            "fs",
            "_fsync",
            "full",
            "fulltext",
            "function",
            "functions",
            "gc",
            "gcs",
            "get_format",
            "_gc",
            "_gcx",
            "generate",
            "geography",
            "geography_area",
            "geography_contains",
            "geography_distance",
            "geography_intersects",
            "geography_latitude",
            "geography_length",
            "geography_longitude",
            "geographypoint",
            "geography_point",
            "geography_within_distance",
            "geometry",
            "geometry_area",
            "geometry_contains",
            "geometry_distance",
            "geometry_filter",
            "geometry_intersects",
            "geometry_length",
            "geometrypoint",
            "geometry_point",
            "geometry_within_distance",
            "geometry_x",
            "geometry_y",
            "global",
            "_global_version_timestamp",
            "grant",
            "granted",
            "grants",
            "greatest",
            "group",
            "grouping",
            "groups",
            "group_concat",
            "gzip",
            "handle",
            "handler",
            "hard_cpu_limit_percentage",
            "hash",
            "has_temp_tables",
            "having",
            "hdfs",
            "header",
            "heartbeat_no_logging",
            "hex",
            "highlight",
            "high_priority",
            "hold",
            "holding",
            "host",
            "hosts",
            "hour",
            "hour_microsecond",
            "hour_minute",
            "hour_second",
            "identified",
            "identity",
            "if",
            "ifnull",
            "ignore",
            "ilike",
            "immediate",
            "immutable",
            "implicit",
            "import",
            "in",
            "including",
            "increment",
            "incremental",
            "index",
            "indexes",
            "inet_aton",
            "inet_ntoa",
            "inet6_aton",
            "inet6_ntoa",
            "infile",
            "inherit",
            "inherits",
            "_init_profile",
            "init",
            "initcap",
            "initialize",
            "initially",
            "inject",
            "inline",
            "inner",
            "inout",
            "input",
            "insensitive",
            "insert",
            "insert_method",
            "instance",
            "instead",
            "instr",
            "int",
            "int1",
            "int2",
            "int3",
            "int4",
            "int8",
            "integer",
            "_internal_dynamic_typecast",
            "interpreter_mode",
            "intersect",
            "interval",
            "into",
            "invoker",
            "is",
            "isnull",
            "isolation",
            "iterate",
            "join",
            "json",
            "json_agg",
            "json_array_contains_double",
            "json_array_contains_json",
            "json_array_contains_string",
            "json_array_push_double",
            "json_array_push_json",
            "json_array_push_string",
            "json_delete_key",
            "json_extract_double",
            "json_extract_json",
            "json_extract_string",
            "json_extract_bigint",
            "json_get_type",
            "json_length",
            "json_set_double",
            "json_set_json",
            "json_set_string",
            "json_splice_double",
            "json_splice_json",
            "json_splice_string",
            "kafka",
            "key",
            "key_block_size",
            "keys",
            "kill",
            "killall",
            "label",
            "lag",
            "language",
            "large",
            "last",
            "last_day",
            "last_insert_id",
            "last_value",
            "lateral",
            "latest",
            "lc_collate",
            "lc_ctype",
            "lcase",
            "lead",
            "leading",
            "leaf",
            "leakproof",
            "least",
            "leave",
            "leaves",
            "left",
            "length",
            "level",
            "license",
            "like",
            "limit",
            "lines",
            "listen",
            "llvm",
            "ln",
            "load",
            "loaddata_where",
            "_load",
            "local",
            "localtime",
            "localtimestamp",
            "locate",
            "location",
            "lock",
            "log",
            "log10",
            "log2",
            "long",
            "longblob",
            "longtext",
            "loop",
            "lower",
            "low_priority",
            "lpad",
            "_ls",
            "ltrim",
            "lz4",
            "management",
            "_management_thread",
            "mapping",
            "master",
            "match",
            "materialized",
            "max",
            "maxvalue",
            "max_concurrency",
            "max_errors",
            "max_partitions_per_batch",
            "max_queue_depth",
            "max_retries_per_batch_partition",
            "max_rows",
            "mbc",
            "md5",
            "mpl",
            "median",
            "mediumblob",
            "mediumint",
            "mediumtext",
            "member",
            "memory",
            "memory_percentage",
            "_memsql_table_id_lookup",
            "memsql",
            "memsql_deserialize",
            "memsql_imitating_kafka",
            "memsql_serialize",
            "merge",
            "metadata",
            "microsecond",
            "middleint",
            "min",
            "min_rows",
            "minus",
            "minute",
            "minute_microsecond",
            "minute_second",
            "minvalue",
            "mod",
            "mode",
            "model",
            "modifies",
            "modify",
            "month",
            "monthname",
            "months_between",
            "move",
            "mpl",
            "names",
            "named",
            "namespace",
            "national",
            "natural",
            "nchar",
            "next",
            "no",
            "node",
            "none",
            "no_query_rewrite",
            "noparam",
            "not",
            "nothing",
            "notify",
            "now",
            "nowait",
            "no_write_to_binlog",
            "no_query_rewrite",
            "norely",
            "nth_value",
            "ntile",
            "null",
            "nullcols",
            "nullif",
            "nulls",
            "numeric",
            "nvarchar",
            "object",
            "octet_length",
            "of",
            "off",
            "offline",
            "offset",
            "offsets",
            "oids",
            "on",
            "online",
            "only",
            "open",
            "operator",
            "optimization",
            "optimize",
            "optimizer",
            "optimizer_state",
            "option",
            "options",
            "optionally",
            "or",
            "order",
            "ordered_serialize",
            "orphan",
            "out",
            "out_of_order",
            "outer",
            "outfile",
            "over",
            "overlaps",
            "overlay",
            "owned",
            "owner",
            "pack_keys",
            "paired",
            "parser",
            "parquet",
            "partial",
            "partition",
            "partition_id",
            "partitioning",
            "partitions",
            "passing",
            "password",
            "password_lock_time",
            "parser",
            "pause",
            "_pause_replay",
            "percent_rank",
            "percentile_cont",
            "percentile_disc",
            "periodic",
            "persisted",
            "pi",
            "pipeline",
            "pipelines",
            "pivot",
            "placing",
            "plan",
            "plans",
            "plancache",
            "plugins",
            "pool",
            "pools",
            "port",
            "position",
            "pow",
            "power",
            "preceding",
            "precision",
            "prepare",
            "prepared",
            "preserve",
            "primary",
            "prior",
            "privileges",
            "procedural",
            "procedure",
            "procedures",
            "process",
            "processlist",
            "profile",
            "profiles",
            "program",
            "promote",
            "proxy",
            "purge",
            "quarter",
            "queries",
            "query",
            "query_timeout",
            "queue",
            "quote",
            "radians",
            "rand",
            "range",
            "rank",
            "read",
            "_read",
            "reads",
            "real",
            "reassign",
            "rebalance",
            "recheck",
            "record",
            "recursive",
            "redundancy",
            "redundant",
            "ref",
            "reference",
            "references",
            "refresh",
            "regexp",
            "reindex",
            "relative",
            "release",
            "reload",
            "rely",
            "remote",
            "remove",
            "rename",
            "repair",
            "_repair_table",
            "repeat",
            "repeatable",
            "_repl",
            "_reprovisioning",
            "replace",
            "replica",
            "replicate",
            "replicating",
            "replication",
            "durability",
            "require",
            "resource",
            "resource_pool",
            "reset",
            "restart",
            "restore",
            "restrict",
            "result",
            "_resurrect",
            "retry",
            "return",
            "returning",
            "returns",
            "reverse",
            "revoke",
            "rg_pool",
            "right",
            "right_anti_join",
            "right_semi_join",
            "right_straight_join",
            "rlike",
            "role",
            "roles",
            "rollback",
            "rollup",
            "round",
            "routine",
            "row",
            "row_count",
            "row_format",
            "row_number",
            "rows",
            "rowstore",
            "rule",
            "rpad",
            "_rpc",
            "rtrim",
            "running",
            "s3",
            "safe",
            "save",
            "savepoint",
            "scalar",
            "schema",
            "schemas",
            "schema_binding",
            "scroll",
            "search",
            "second",
            "second_microsecond",
            "sec_to_time",
            "security",
            "select",
            "semi_join",
            "_send_threads",
            "sensitive",
            "separator",
            "sequence",
            "sequences",
            "serial",
            "serializable",
            "series",
            "service_user",
            "server",
            "session",
            "session_user",
            "set",
            "setof",
            "security_lists_intersect",
            "sha",
            "sha1",
            "sha2",
            "shard",
            "sharded",
            "sharded_id",
            "share",
            "show",
            "shutdown",
            "sigmoid",
            "sign",
            "signal",
            "similar",
            "simple",
            "site",
            "signed",
            "sin",
            "skip",
            "skipped_batches",
            "sleep",
            "_sleep",
            "smallint",
            "snapshot",
            "_snapshot",
            "_snapshots",
            "soft_cpu_limit_percentage",
            "some",
            "soname",
            "sparse",
            "spatial",
            "spatial_check_index",
            "specific",
            "split",
            "sql",
            "sql_big_result",
            "sql_buffer_result",
            "sql_cache",
            "sql_calc_found_rows",
            "sqlexception",
            "sql_mode",
            "sql_no_cache",
            "sql_no_logging",
            "sql_small_result",
            "sqlstate",
            "sqlwarning",
            "sqrt",
            "ssl",
            "stable",
            "standalone",
            "start",
            "starting",
            "state",
            "statement",
            "statistics",
            "stats",
            "status",
            "std",
            "stddev",
            "stddev_pop",
            "stddev_samp",
            "stdin",
            "stdout",
            "stop",
            "storage",
            "str_to_date",
            "straight_join",
            "strict",
            "string",
            "strip",
            "subdate",
            "substr",
            "substring",
            "substring_index",
            "success",
            "sum",
            "super",
            "symmetric",
            "sync_snapshot",
            "sync",
            "_sync",
            "_sync2",
            "_sync_partitions",
            "_sync_snapshot",
            "synchronize",
            "sysid",
            "system",
            "table",
            "table_checksum",
            "tables",
            "tablespace",
            "tags",
            "tan",
            "target_size",
            "task",
            "temp",
            "template",
            "temporary",
            "temptable",
            "_term_bump",
            "terminate",
            "terminated",
            "test",
            "text",
            "then",
            "time",
            "timediff",
            "time_bucket",
            "time_format",
            "timeout",
            "timestamp",
            "timestampadd",
            "timestampdiff",
            "timezone",
            "time_to_sec",
            "tinyblob",
            "tinyint",
            "tinytext",
            "to",
            "to_base64",
            "to_char",
            "to_date",
            "to_days",
            "to_json",
            "to_number",
            "to_seconds",
            "to_timestamp",
            "tracelogs",
            "traditional",
            "trailing",
            "transform",
            "transaction",
            "_transactions_experimental",
            "treat",
            "trigger",
            "triggers",
            "trim",
            "true",
            "trunc",
            "truncate",
            "trusted",
            "two_phase",
            "_twopcid",
            "type",
            "types",
            "ucase",
            "unbounded",
            "uncommitted",
            "undefined",
            "undo",
            "unencrypted",
            "unenforced",
            "unhex",
            "unhold",
            "unicode",
            "union",
            "unique",
            "_unittest",
            "unix_timestamp",
            "unknown",
            "unlisten",
            "_unload",
            "unlock",
            "unlogged",
            "unpivot",
            "unsigned",
            "until",
            "update",
            "upgrade",
            "upper",
            "usage",
            "use",
            "user",
            "users",
            "using",
            "utc_date",
            "utc_time",
            "utc_timestamp",
            "_utf8",
            "vacuum",
            "valid",
            "validate",
            "validator",
            "value",
            "values",
            "varbinary",
            "varchar",
            "varcharacter",
            "variables",
            "variadic",
            "variance",
            "var_pop",
            "var_samp",
            "varying",
            "vector_sub",
            "verbose",
            "version",
            "view",
            "void",
            "volatile",
            "voting",
            "wait",
            "_wake",
            "warnings",
            "week",
            "weekday",
            "weekofyear",
            "when",
            "where",
            "while",
            "whitespace",
            "window",
            "with",
            "without",
            "within",
            "_wm_heartbeat",
            "work",
            "workload",
            "wrapper",
            "write",
            "xact_id",
            "xor",
            "year",
            "year_month",
            "yes",
            "zerofill",
            "zone",
        }
