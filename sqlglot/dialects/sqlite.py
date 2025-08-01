from __future__ import annotations

import typing as t

from sqlglot import exp, generator, parser, tokens, transforms
from sqlglot.dialects.dialect import (
    Dialect,
    NormalizationStrategy,
    any_value_to_max_sql,
    arrow_json_extract_sql,
    concat_to_dpipe_sql,
    count_if_to_sum,
    no_ilike_sql,
    no_pivot_sql,
    no_tablesample_sql,
    no_trycast_sql,
    rename_func,
    strposition_sql,
)
from sqlglot.generator import unsupported_args
from sqlglot.tokens import TokenType


def _build_strftime(args: t.List) -> exp.Anonymous | exp.TimeToStr:
    if len(args) == 1:
        args.append(exp.CurrentTimestamp())
    if len(args) == 2:
        return exp.TimeToStr(this=exp.TsOrDsToTimestamp(this=args[1]), format=args[0])
    return exp.Anonymous(this="STRFTIME", expressions=args)


def _transform_create(expression: exp.Expression) -> exp.Expression:
    """Move primary key to a column and enforce auto_increment on primary keys."""
    schema = expression.this

    if isinstance(expression, exp.Create) and isinstance(schema, exp.Schema):
        defs = {}
        primary_key = None

        for e in schema.expressions:
            if isinstance(e, exp.ColumnDef):
                defs[e.name] = e
            elif isinstance(e, exp.PrimaryKey):
                primary_key = e

        if primary_key and len(primary_key.expressions) == 1:
            column = defs[primary_key.expressions[0].name]
            column.append(
                "constraints", exp.ColumnConstraint(kind=exp.PrimaryKeyColumnConstraint())
            )
            schema.expressions.remove(primary_key)
        else:
            for column in defs.values():
                auto_increment = None
                for constraint in column.constraints:
                    if isinstance(constraint.kind, exp.PrimaryKeyColumnConstraint):
                        break
                    if isinstance(constraint.kind, exp.AutoIncrementColumnConstraint):
                        auto_increment = constraint
                if auto_increment:
                    column.constraints.remove(auto_increment)

    return expression


def _generated_to_auto_increment(expression: exp.Expression) -> exp.Expression:
    if not isinstance(expression, exp.ColumnDef):
        return expression

    generated = expression.find(exp.GeneratedAsIdentityColumnConstraint)

    if generated:
        t.cast(exp.ColumnConstraint, generated.parent).pop()

        not_null = expression.find(exp.NotNullColumnConstraint)
        if not_null:
            t.cast(exp.ColumnConstraint, not_null.parent).pop()

        expression.append(
            "constraints", exp.ColumnConstraint(kind=exp.AutoIncrementColumnConstraint())
        )

    return expression


class SQLite(Dialect):
    # https://sqlite.org/forum/forumpost/5e575586ac5c711b?raw
    NORMALIZATION_STRATEGY = NormalizationStrategy.CASE_INSENSITIVE
    SUPPORTS_SEMI_ANTI_JOIN = False
    TYPED_DIVISION = True
    SAFE_DIVISION = True

    class Tokenizer(tokens.Tokenizer):
        IDENTIFIERS = ['"', ("[", "]"), "`"]
        HEX_STRINGS = [("x'", "'"), ("X'", "'"), ("0x", ""), ("0X", "")]

        NESTED_COMMENTS = False

        KEYWORDS = {
            **tokens.Tokenizer.KEYWORDS,
            "ATTACH": TokenType.ATTACH,
            "DETACH": TokenType.DETACH,
        }

        KEYWORDS.pop("/*+")

        COMMANDS = {*tokens.Tokenizer.COMMANDS, TokenType.REPLACE}

    class Parser(parser.Parser):
        STRING_ALIASES = True
        ALTER_RENAME_REQUIRES_COLUMN = False
        JOINS_HAVE_EQUAL_PRECEDENCE = True

        FUNCTIONS = {
            **parser.Parser.FUNCTIONS,
            "EDITDIST3": exp.Levenshtein.from_arg_list,
            "STRFTIME": _build_strftime,
            "DATETIME": lambda args: exp.Anonymous(this="DATETIME", expressions=args),
            "TIME": lambda args: exp.Anonymous(this="TIME", expressions=args),
        }

        STATEMENT_PARSERS = {
            **parser.Parser.STATEMENT_PARSERS,
            TokenType.ATTACH: lambda self: self._parse_attach_detach(),
            TokenType.DETACH: lambda self: self._parse_attach_detach(is_attach=False),
        }

        def _parse_unique(self) -> exp.UniqueColumnConstraint:
            # Do not consume more tokens if UNIQUE is used as a standalone constraint, e.g:
            # CREATE TABLE foo (bar TEXT UNIQUE REFERENCES baz ...)
            if self._curr.text.upper() in self.CONSTRAINT_PARSERS:
                return self.expression(exp.UniqueColumnConstraint)

            return super()._parse_unique()

        def _parse_attach_detach(self, is_attach=True) -> exp.Attach | exp.Detach:
            self._match(TokenType.DATABASE)
            this = self._parse_expression()

            return (
                self.expression(exp.Attach, this=this)
                if is_attach
                else self.expression(exp.Detach, this=this)
            )

    class Generator(generator.Generator):
        JOIN_HINTS = False
        TABLE_HINTS = False
        QUERY_HINTS = False
        NVL2_SUPPORTED = False
        JSON_PATH_BRACKETED_KEY_SUPPORTED = False
        SUPPORTS_CREATE_TABLE_LIKE = False
        SUPPORTS_TABLE_ALIAS_COLUMNS = False
        SUPPORTS_TO_NUMBER = False
        SUPPORTS_WINDOW_EXCLUDE = True
        EXCEPT_INTERSECT_SUPPORT_ALL_CLAUSE = False
        SUPPORTS_MEDIAN = False
        JSON_KEY_VALUE_PAIR_SEP = ","

        SUPPORTED_JSON_PATH_PARTS = {
            exp.JSONPathKey,
            exp.JSONPathRoot,
            exp.JSONPathSubscript,
        }

        TYPE_MAPPING = {
            **generator.Generator.TYPE_MAPPING,
            exp.DataType.Type.BOOLEAN: "INTEGER",
            exp.DataType.Type.TINYINT: "INTEGER",
            exp.DataType.Type.SMALLINT: "INTEGER",
            exp.DataType.Type.INT: "INTEGER",
            exp.DataType.Type.BIGINT: "INTEGER",
            exp.DataType.Type.FLOAT: "REAL",
            exp.DataType.Type.DOUBLE: "REAL",
            exp.DataType.Type.DECIMAL: "REAL",
            exp.DataType.Type.CHAR: "TEXT",
            exp.DataType.Type.NCHAR: "TEXT",
            exp.DataType.Type.VARCHAR: "TEXT",
            exp.DataType.Type.NVARCHAR: "TEXT",
            exp.DataType.Type.BINARY: "BLOB",
            exp.DataType.Type.VARBINARY: "BLOB",
        }
        TYPE_MAPPING.pop(exp.DataType.Type.BLOB)

        TOKEN_MAPPING = {
            TokenType.AUTO_INCREMENT: "AUTOINCREMENT",
        }

        TRANSFORMS = {
            **generator.Generator.TRANSFORMS,
            exp.AnyValue: any_value_to_max_sql,
            exp.Chr: rename_func("CHAR"),
            exp.Concat: concat_to_dpipe_sql,
            exp.CountIf: count_if_to_sum,
            exp.Create: transforms.preprocess([_transform_create]),
            exp.CurrentDate: lambda *_: "CURRENT_DATE",
            exp.CurrentTime: lambda *_: "CURRENT_TIME",
            exp.CurrentTimestamp: lambda *_: "CURRENT_TIMESTAMP",
            exp.ColumnDef: transforms.preprocess([_generated_to_auto_increment]),
            exp.DateStrToDate: lambda self, e: self.sql(e, "this"),
            exp.If: rename_func("IIF"),
            exp.ILike: no_ilike_sql,
            exp.JSONExtractScalar: arrow_json_extract_sql,
            exp.Levenshtein: unsupported_args("ins_cost", "del_cost", "sub_cost", "max_dist")(
                rename_func("EDITDIST3")
            ),
            exp.LogicalOr: rename_func("MAX"),
            exp.LogicalAnd: rename_func("MIN"),
            exp.Pivot: no_pivot_sql,
            exp.Rand: rename_func("RANDOM"),
            exp.Select: transforms.preprocess(
                [
                    transforms.eliminate_distinct_on,
                    transforms.eliminate_qualify,
                    transforms.eliminate_semi_and_anti_joins,
                ]
            ),
            exp.StrPosition: lambda self, e: strposition_sql(self, e, func_name="INSTR"),
            exp.TableSample: no_tablesample_sql,
            exp.TimeStrToTime: lambda self, e: self.sql(e, "this"),
            exp.TimeToStr: lambda self, e: self.func("STRFTIME", e.args.get("format"), e.this),
            exp.TryCast: no_trycast_sql,
            exp.TsOrDsToTimestamp: lambda self, e: self.sql(e, "this"),
        }

        # SQLite doesn't generally support CREATE TABLE .. properties
        # https://www.sqlite.org/lang_createtable.html
        PROPERTIES_LOCATION = {
            prop: exp.Properties.Location.UNSUPPORTED
            for prop in generator.Generator.PROPERTIES_LOCATION
        }

        # There are a few exceptions (e.g. temporary tables) which are supported or
        # can be transpiled to SQLite, so we explicitly override them accordingly
        PROPERTIES_LOCATION[exp.LikeProperty] = exp.Properties.Location.POST_SCHEMA
        PROPERTIES_LOCATION[exp.TemporaryProperty] = exp.Properties.Location.POST_CREATE

        LIMIT_FETCH = "LIMIT"

        def jsonextract_sql(self, expression: exp.JSONExtract) -> str:
            if expression.expressions:
                return self.function_fallback_sql(expression)
            return arrow_json_extract_sql(self, expression)

        def dateadd_sql(self, expression: exp.DateAdd) -> str:
            modifier = expression.expression
            modifier = modifier.name if modifier.is_string else self.sql(modifier)
            unit = expression.args.get("unit")
            modifier = f"'{modifier} {unit.name}'" if unit else f"'{modifier}'"
            return self.func("DATE", expression.this, modifier)

        def cast_sql(self, expression: exp.Cast, safe_prefix: t.Optional[str] = None) -> str:
            if expression.is_type("date"):
                return self.func("DATE", expression.this)

            return super().cast_sql(expression)

        def generateseries_sql(self, expression: exp.GenerateSeries) -> str:
            parent = expression.parent
            alias = parent and parent.args.get("alias")

            if isinstance(alias, exp.TableAlias) and alias.columns:
                column_alias = alias.columns[0]
                alias.set("columns", None)
                sql = self.sql(
                    exp.select(exp.alias_("value", column_alias)).from_(expression).subquery()
                )
            else:
                sql = self.function_fallback_sql(expression)

            return sql

        def datediff_sql(self, expression: exp.DateDiff) -> str:
            unit = expression.args.get("unit")
            unit = unit.name.upper() if unit else "DAY"

            sql = f"(JULIANDAY({self.sql(expression, 'this')}) - JULIANDAY({self.sql(expression, 'expression')}))"

            if unit == "MONTH":
                sql = f"{sql} / 30.0"
            elif unit == "YEAR":
                sql = f"{sql} / 365.0"
            elif unit == "HOUR":
                sql = f"{sql} * 24.0"
            elif unit == "MINUTE":
                sql = f"{sql} * 1440.0"
            elif unit == "SECOND":
                sql = f"{sql} * 86400.0"
            elif unit == "MILLISECOND":
                sql = f"{sql} * 86400000.0"
            elif unit == "MICROSECOND":
                sql = f"{sql} * 86400000000.0"
            elif unit == "NANOSECOND":
                sql = f"{sql} * 8640000000000.0"
            else:
                self.unsupported(f"DATEDIFF unsupported for '{unit}'.")

            return f"CAST({sql} AS INTEGER)"

        # https://www.sqlite.org/lang_aggfunc.html#group_concat
        def groupconcat_sql(self, expression: exp.GroupConcat) -> str:
            this = expression.this
            distinct = expression.find(exp.Distinct)

            if distinct:
                this = distinct.expressions[0]
                distinct_sql = "DISTINCT "
            else:
                distinct_sql = ""

            if isinstance(expression.this, exp.Order):
                self.unsupported("SQLite GROUP_CONCAT doesn't support ORDER BY.")
                if expression.this.this and not distinct:
                    this = expression.this.this

            separator = expression.args.get("separator")
            return f"GROUP_CONCAT({distinct_sql}{self.format_args(this, separator)})"

        def least_sql(self, expression: exp.Least) -> str:
            if len(expression.expressions) > 1:
                return rename_func("MIN")(self, expression)

            return self.sql(expression, "this")

        def transaction_sql(self, expression: exp.Transaction) -> str:
            this = expression.this
            this = f" {this}" if this else ""
            return f"BEGIN{this} TRANSACTION"

        def isascii_sql(self, expression: exp.IsAscii) -> str:
            return f"(NOT {self.sql(expression.this)} GLOB CAST(x'2a5b5e012d7f5d2a' AS TEXT))"

        @unsupported_args("this")
        def currentschema_sql(self, expression: exp.CurrentSchema) -> str:
            return "'main'"

        def ignorenulls_sql(self, expression: exp.IgnoreNulls) -> str:
            self.unsupported("SQLite does not support IGNORE NULLS.")
            return self.sql(expression.this)

        def respectnulls_sql(self, expression: exp.RespectNulls) -> str:
            return self.sql(expression.this)
