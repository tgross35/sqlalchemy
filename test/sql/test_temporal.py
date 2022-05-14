"""Tests for temporal table structure, including system and
application versioning"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Period
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import schema
from sqlalchemy import SystemTimePeriod
from sqlalchemy import Table
from sqlalchemy import testing
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import ArgumentError
from sqlalchemy.sql.sqltypes import DATE
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.sqltypes import VARCHAR
from sqlalchemy.testing import assert_raises_message
from sqlalchemy.testing import AssertsCompiledSQL
from sqlalchemy.testing import eq_
from sqlalchemy.testing import fixtures
from sqlalchemy.testing import is_
from sqlalchemy.testing import is_not_none


class PeriodTest(fixtures.TestBase, AssertsCompiledSQL):
    """Test the basic period construct"""

    __dialect__ = "default"

    @testing.combinations(lambda x: x, lambda x: x.name)
    def test_period(self, fn):
        """Test basic period construct specifying object and str columns"""
        m = MetaData()
        start_ts = Column("start_ts", TIMESTAMP)
        end_ts = Column("end_ts", TIMESTAMP)
        t = Table(
            "t",
            m,
            start_ts,
            end_ts,
            Period("test_period", fn(start_ts), fn(end_ts)),
        )
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE t ("
            "start_ts TIMESTAMP, "
            "end_ts TIMESTAMP, "
            "PERIOD FOR test_period (start_ts, end_ts))",
        )

    def test_period_pk_col_arg(self):
        """Test setting a primary key on a PERIOD via column/period args"""
        m = MetaData()
        t = Table(
            "t",
            m,
            Column("id", Integer, primary_key=True),
            Column("start_ts", TIMESTAMP),
            Column("end_ts", TIMESTAMP),
            Period("test_period", "start_ts", "end_ts", primary_key=True),
        )
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE t ("
            "id INTEGER NOT NULL, "
            "start_ts TIMESTAMP, "
            "end_ts TIMESTAMP, "
            "PERIOD FOR test_period (start_ts, end_ts), "
            "PRIMARY KEY (id, test_period WITHOUT OVERLAPS))",
        )

    @testing.combinations(
        (PrimaryKeyConstraint, "PRIMARY KEY"), (UniqueConstraint, "UNIQUE")
    )
    def test_period_constraints_str_init(self, constraint, keytypeddl):
        """Test setting a primary key or a unique key on a PERIOD via a
        constraint
        """
        m = MetaData()
        t = Table(
            "t",
            m,
            Column("id", Integer, nullable=False),
            Column("start_ts", TIMESTAMP),
            Column("end_ts", TIMESTAMP),
            Period("test_period", "start_ts", "end_ts"),
            constraint("id", "test_period"),
        )
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE t ("
            "id INTEGER NOT NULL, "
            "start_ts TIMESTAMP, "
            "end_ts TIMESTAMP, "
            "PERIOD FOR test_period (start_ts, end_ts), "
            f"{keytypeddl} (id, test_period WITHOUT OVERLAPS))",
        )

    @testing.combinations(
        (PrimaryKeyConstraint, "PRIMARY KEY"), (UniqueConstraint, "UNIQUE")
    )
    def test_period_constraints_obj_init(self, constraint, keytypeddl):
        """Test setting a primary key or a unique key on a PERIOD via a
        constraint where an object is passed to the initializer
        """
        m = MetaData()
        id_col = Column("id", Integer, nullable=False)
        period_col = Period("test_period", "start_ts", "end_ts")
        t = Table(
            "t",
            m,
            id_col,
            Column("start_ts", TIMESTAMP),
            Column("end_ts", TIMESTAMP),
            period_col,
            constraint(id_col, period_col),
        )
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE t ("
            "id INTEGER NOT NULL, "
            "start_ts TIMESTAMP, "
            "end_ts TIMESTAMP, "
            "PERIOD FOR test_period (start_ts, end_ts), "
            f"{keytypeddl} (id, test_period WITHOUT OVERLAPS))",
        )

    def test_period_system(self):
        m = MetaData()
        t = Table(
            "t",
            m,
            Column("start_ts", TIMESTAMP),
            Column("end_ts", TIMESTAMP),
            Period("test_period", "start_ts", "end_ts", system=True),
        )
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE t (start_ts TIMESTAMP, end_ts TIMESTAMP)",
        )

    def test_period_copy(self):
        period = Period("test_period", "start_ts", "end_ts")
        m = MetaData()
        t = Table(  # noqa
            "t",
            m,
            Column("start_ts", TIMESTAMP),
            Column("end_ts", TIMESTAMP),
        )

        p_copy = period._copy()

        t1 = Table(
            "t1",
            m,
            Column("start_ts", TIMESTAMP),
            Column("end_ts", TIMESTAMP),
            p_copy,
        )
        is_not_none(t1.periods.test_period)

    def test_raise_on_column_not_in_table(self):
        m = MetaData()

        def fn(**kw):
            col1 = Column("start_ts", TIMESTAMP)
            col2 = Column("end_ts", TIMESTAMP)
            t1 = Table(  # noqa
                "t",
                m,
                Period("test_period", col1, col2),
            )

        text = "Given column object 'start_ts' does not belong to Table 't'"
        assert_raises_message(ArgumentError, text, fn)

    def test_raise_on_column_not_found(self):
        m = MetaData()

        def fn(**kw):
            t1 = Table(  # noqa
                "t",
                m,
                Column("start_ts", TIMESTAMP),
                Column("end_ts", TIMESTAMP),
                Period("test_period", **kw),
            )

        text = "Cannot find column 'not_here' in Table 't'"
        assert_raises_message(
            ArgumentError, text, fn, start="start_ts", end="not_here"
        )
        assert_raises_message(
            ArgumentError, text, fn, start="not_here", end="end_ts"
        )

    def test_raise_on_period_in_other_table(self):
        m = MetaData()
        period = Period("test_period", "start_ts", "end_ts")
        t1 = Table(  # noqa
            "t1",
            m,
            Column("start_ts", TIMESTAMP),
            Column("end_ts", TIMESTAMP),
            period,
        )

        def fn(**kw):
            t2 = Table(  # noqa
                "t2",
                m,
                Column("start_ts", TIMESTAMP),
                Column("end_ts", TIMESTAMP),
                period,
            )

        text = "Period object 'test_period' already assigned to Table 't1'"
        assert_raises_message(ArgumentError, text, fn)

    def test_to_metadata(self):
        period = Period("test_period", "start_ts", "end_ts")
        start = Column("start_ts", TIMESTAMP)
        end = Column("end_ts", TIMESTAMP)
        m = MetaData()
        t = Table(
            "t",
            m,
            start,
            end,
            period,
        )
        is_(t._system_versioning_period, None)
        is_(period, t.periods.test_period)
        eq_(period.name, "test_period")
        eq_(period.start, start)
        eq_(period.end, end)

        # Verify specifying period with objects
        start1 = Column("start_ts", TIMESTAMP)
        end1 = Column("end_ts", TIMESTAMP)
        period1 = Period("test_period", start1, end1)
        m1 = MetaData()
        t1 = Table(
            "t1",
            m1,
            start1,
            end1,
            period1,
        )
        is_(t1.periods.test_period, period1)
        is_(period1.start, start1)
        is_(period1.end, end1)


class SystemVersioningTest(fixtures.TestBase, AssertsCompiledSQL):
    """Test possible constructs related to system versioning.

    Tests come from MariaDB's implementation examples
    https://mariadb.com/kb/en/system-versioned-tables/
    And from "Temporal features in SQL:2011"
    https://cs.ulb.ac.be/public/_media/teaching/infoh415/
    tempfeaturessql2011.pdf"""

    __dialect__ = "default"

    # @testing.requires.system_versioned_tables_support
    def test_create_table_versioning_no_columns(self):
        m = MetaData()
        t = Table("t", m, Column("x", Integer), SystemTimePeriod())
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE t (x INTEGER) WITH SYSTEM VERSIONING",
        )

    # @testing.requires.system_versioned_tables_support
    @testing.combinations(lambda x: x, lambda x: x.name)
    def test_create_table_versioning_columns_specified(self, fn):
        m = MetaData()
        start_ts = Column("start_ts", TIMESTAMP)
        end_ts = Column("end_ts", TIMESTAMP)
        t = Table(
            "t",
            m,
            Column("x", Integer),
            start_ts,
            end_ts,
            SystemTimePeriod(fn(start_ts), fn(end_ts)),
        )
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE t ("
            "x INTEGER, "
            "start_ts TIMESTAMP GENERATED ALWAYS AS ROW START, "
            "end_ts TIMESTAMP GENERATED ALWAYS AS ROW END, "
            "PERIOD FOR SYSTEM_TIME (start_ts, end_ts)"
            ") WITH SYSTEM VERSIONING",
        )

    def test_column_with_system_versioning(self):
        m = MetaData()
        t = Table(
            "t",
            m,
            Column("x", Integer, system_versioning=True),
            Column("y", Integer),
        )
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE t ("
            "x INTEGER WITH SYSTEM VERSIONING, "
            "y INTEGER)",
        )

    def test_column_without_system_versioning(self):
        m = MetaData()
        t = Table(
            "t",
            m,
            Column("x", Integer),
            Column("y", Integer, system_versioning=False),
            SystemTimePeriod(),
        )
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE t ("
            "x INTEGER, "
            "y INTEGER WITHOUT SYSTEM VERSIONING"
            ") WITH SYSTEM VERSIONING",
        )

    def test_bitemporal_table(self):
        """Test creating the example table in the document
        "Temporal features in SQL:2011", with both SV and AV. FK constraint
        is not implemented for now."""

        m = MetaData()
        t = Table(
            "emp",
            m,
            Column("eno", Integer),
            Column("estart", DATE),
            Column("eend", DATE),
            Column("edept", Integer),
            Column("sys_start", TIMESTAMP),
            Column("sys_end", TIMESTAMP),
            Column("ename", VARCHAR(30)),
            Period("eperiod", "estart", "eend"),
            SystemTimePeriod("sys_start", "sys_end"),
            PrimaryKeyConstraint("eno", "eperiod"),
            # ForeignKeyConstraint(
            #     ("EDept", "EPeriod"),
            #     ("Dept.DNo", "Dept.DPeriod"),
            # ),
        )
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE emp ("
            "eno INTEGER NOT NULL, "
            "estart DATE, "
            "eend DATE, "
            "edept INTEGER, "
            "sys_start TIMESTAMP GENERATED ALWAYS AS ROW START, "
            "sys_end TIMESTAMP GENERATED ALWAYS AS ROW END, "
            "ename VARCHAR(30), "
            "PERIOD FOR eperiod (estart, eend), "
            "PERIOD FOR SYSTEM_TIME (sys_start, sys_end), "
            "PRIMARY KEY (eno, eperiod WITHOUT OVERLAPS)"
            # "FOREIGN KEY (Edept, PERIOD EPeriod)"
            # "REFERENCES Dept (DNo, PERIOD DPeriod)"
            ") WITH SYSTEM VERSIONING",
        )

    def test_to_metadata(self):
        # Test system period with no given columns
        sysperiod = SystemTimePeriod()
        m = MetaData()
        t = Table("t", m, Column("x", Integer), sysperiod)
        is_(t._system_versioning_period, sysperiod)

        # Test period with given columns
        start = Column("start_ts", TIMESTAMP)
        end = Column("end_ts", TIMESTAMP)
        sysperiod1 = SystemTimePeriod(start, end)
        m1 = MetaData()
        t1 = Table(
            "t1",
            m1,
            start,
            end,
            sysperiod1,
        )

        is_(t1._system_versioning_period, sysperiod1)
        eq_(sysperiod1.name, "SYSTEM_TIME")
        eq_(sysperiod1.start, start)
        eq_(sysperiod1.end, end)
