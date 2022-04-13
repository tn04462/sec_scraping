from datetime import datetime
from psycopg.rows import dict_row
from psycopg.errors import ProgrammingError, UniqueViolation, ForeignKeyViolation
from psycopg_pool import ConnectionPool
from json import load
from functools import reduce
from os import path
import pandas as pd
import logging

from configparser import ConfigParser
from _constants import FORM_TYPES_INFO

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


config = ConfigParser()
config.read("./config.cfg")
if config.getboolean("environment", "production") is False:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


# make Database class a singleton
class DilutionDB:
    def __init__(self, connectionString):
        self.connectionString = connectionString
        self.pool = ConnectionPool(
            self.connectionString, kwargs={"row_factory": dict_row}
        )
        self.conn = self.pool.connection
        self.tracked_tickers = self._get_tracked_tickers_from_config()

    def _get_tracked_tickers_from_config(self):
        # add try except when needed for good error message
        return [
            t.strip()
            for t in config["general"]["tracked_tickers"].strip("[]").split(",")
        ]

    def execute_sql_file(self, path):
        with self.conn() as c:
            with open(path, "r") as sql:
                res = c.execute(sql.read())
                try:
                    for row in res:
                        logging.DEBUG(row)
                except ProgrammingError:
                    pass

    def _delete_all_tables(self):
        with self.conn() as c:
            with open("./sql/db_delete_all_tables.sql", "r") as sql:
                c.execute(sql.read())

    def _create_tables(self):
        with self.conn() as c:
            with open("./sql/dilution_db_schema.sql", "r") as sql:
                c.execute(sql.read())

    def create_form_types(self):
        with self.conn() as c:
            for name, values in FORM_TYPES_INFO.items():
                category = values["category"]
                c.execute(
                    "INSERT INTO form_types(form_type, category) VALUES(%s, %s)",
                    [name, category]
                )
                print(category)

    def create_form_type(self, form_type, category):
        with self.conn() as c:
            c.execute(
                "INSERT INTO form_types(form_type, category) VALUES(%s, %s)",
                [form_type, category],
            )

    def read(self, query, values):
        with self.conn() as c:
            res = c.execute(query, values)
            rows = [row for row in res]
            return rows

    def create_sics(self):
        sics_path = path.normpath(
            path.join(path.dirname(path.abspath(__file__)), ".", "resources/sics.csv")
        )
        sics = pd.read_csv(sics_path)
        with self.conn() as c:
            with c.cursor().copy(
                "COPY sics(sic, industry, sector, division) FROM STDIN"
            ) as copy:
                for val in sics.values:
                    copy.write_row(val)

    def create_sic(self, sic, sector, industry, division):
        with self.conn() as c:
            c.execute(
                "INSERT INTO sics(sic, industry, sector, division) VALUES(%s, %s, %s, %s)",
                [sic, sector, industry, division],
            )

    def create_company(self, cik, sic, symbol, name, description, sic_description=None):
        if len(cik) < 10:
            raise ValueError("cik needs to be in 10 digit form")
        with self.conn() as c:
            try:
                id = c.execute(
                    "INSERT INTO companies(cik, sic, symbol, name_, description_) VALUES(%s, %s, %s, %s, %s) RETURNING id",
                    [cik, sic, symbol, name, description],
                )
                return id.fetchone()["id"]
            except UniqueViolation:
                # logger.debug(f"couldnt create {symbol}:company, already present in db.")
                # logger.debug(f"querying and returning the company_id instead of creating it")
                c.rollback()
                id = c.execute(
                    "SELECT id from companies WHERE symbol = %s AND cik = %s",
                    [symbol, cik],
                )
                return id.fetchone()["id"]
            except Exception as e:
                if "fk_sic" in str(e):
                    if sic_description is None:
                        raise ValueError(
                            f"couldnt create missing sic without sic_description, create_company called with: {locals()}"
                        )
                    try:
                        self.create_sic(
                            sic, "unclassified", sic_description, "unclassified"
                        )
                    except Exception as e:
                        logger.debug(
                            f"failed to add missing sic in create_company: e{e}"
                        )
                        raise e
                    id = self.create_company(cik, sic, symbol, name, description)
                    return id
                else:
                    raise e

    def create_outstanding_shares(self, company_id, instant, amount):
        with self.conn() as c:
            try:
                c.execute(
                    "INSERT INTO outstanding_shares(company_id, instant, amount) VALUES(%s, %s, %s)",
                    [company_id, instant, amount],
                )
            except UniqueViolation as e:
                logger.debug(e)
                pass
            except Exception as e:
                raise e

    def create_net_cash_and_equivalents(self, company_id, instant, amount):
        with self.conn() as c:
            try:
                c.execute(
                    "INSERT INTO net_cash_and_equivalents(company_id, instant, amount) VALUES(%s, %s, %s)",
                    [company_id, instant, amount],
                )
            except UniqueViolation as e:
                logger.debug(e)
                pass
            except Exception as e:
                raise e

    def create_net_cash_and_equivalents_excluding_restricted_noncurrent(
        self, company_id, instant, amount
    ):
        with self.conn() as c:
            try:
                c.execute(
                    "INSERT INTO net_cash_and_equivalents_excluding_restricted_noncurrent(company_id, instant, amount) VALUES(%s, %s, %s)",
                    [company_id, instant, amount],
                )
            except UniqueViolation as e:
                logger.debug(e)
                pass
            except Exception as e:
                raise e

    def create_filing_link(
        self, company_id, filing_html, form_type, filing_date, description, file_number
    ):
        with self.conn() as c:
            try:
                c.execute(
                    "INSERT INTO filing_links(company_id, filing_html, form_type, filing_date, description_, file_number) VALUES(%s, %s, %s, %s, %s, %s)",
                    [
                        company_id,
                        filing_html,
                        form_type,
                        filing_date,
                        description,
                        file_number,
                    ],
                )
            except ForeignKeyViolation as e:
                if "fk_form_type" in str(e):
                    self.create_form_type(form_type, "unspecified")
                else:
                    raise e

    def create_cash_operating(self, company_id, from_date, to_date, amount):
        with self.conn() as c:
            try:
                c.execute(
                    "INSERT INTO cash_operating(company_id, from_date, to_date, amount) VALUES(%s, %s, %s, %s)",
                    [company_id, from_date, to_date, amount],
                )
            except UniqueViolation as e:
                logger.debug(e)
                pass
            except Exception as e:
                raise e

    def create_cash_financing(self, company_id, from_date, to_date, amount):
        with self.conn() as c:
            try:
                c.execute(
                    "INSERT INTO cash_financing(company_id, from_date, to_date, amount) VALUES(%s, %s, %s, %s)",
                    [company_id, from_date, to_date, amount],
                )
            except UniqueViolation as e:
                logger.debug(e)
                pass
            except Exception as e:
                raise e

    def create_cash_investing(self, company_id, from_date, to_date, amount):
        with self.conn() as c:
            try:
                c.execute(
                    "INSERT INTO cash_investing(company_id, from_date, to_date, amount) VALUES(%s, %s, %s, %s)",
                    [company_id, from_date, to_date, amount],
                )
            except UniqueViolation as e:
                logger.debug(e)
                pass
            except Exception as e:
                raise e
    
    def create_cash_burn_summary(
        self,
        company_id,
        burn_rate,
        burn_rate_date,
        net_cash,
        net_cash_date,
        days_of_cash,
        days_of_cash_date
    ):
        with self.conn() as c:
            c.execute("INSERT INTO cash_burn_summary("
                "company_id, burn_rate, burn_rate_date, net_cash, net_cash_date, days_of_cash, days_of_cash_date) "
                "VALUES (%(c_id)s, %(br)s, %(brd)s, %(nc)s, %(ncd)s, %(doc)s, %(docd)s) "
                "ON CONFLICT ON CONSTRAINT unique_company_id "
                "DO UPDATE SET "
                "burn_rate = %(br)s,"
                "burn_rate_date = %(brd)s,"
                "net_cash = %(nc)s,"
                "net_cash_date = %(ncd)s,"
                "days_of_cash = %(doc)s,"
                "days_of_cash_date = %(docd)s "
                "WHERE cash_burn_summary.company_id = %(c_id)s "
                "AND cash_burn_summary.burn_rate_date <= %(brd)s "
                "AND cash_burn_summary.net_cash_date <= %(ncd)s "
                "AND cash_burn_summary.days_of_cash_date <= %(docd)s"
                ,
                {"c_id": company_id,
                "br": burn_rate,
                "brd": burn_rate_date,
                "nc": net_cash,
                "ncd": net_cash_date,
                "doc": days_of_cash,
                "docd": days_of_cash_date})

    def create_cash_burn_rate(
        self,
        company_id,
        burn_rate_operating,
        burn_rate_financing,
        burn_rate_investing,
        burn_rate_total,
        from_date,
        to_date,
    ):
        """UPSERT cash_burn_rate for a specific company. replaces with newer values on from_date conflict"""
        with self.conn() as c:
            try:
                c.execute(
                    (
                        "INSERT INTO cash_burn_rate("
                        "company_id, burn_rate_operating, burn_rate_financing,"
                        "burn_rate_investing, burn_rate_total, from_date, to_date) "
                        "VALUES(%(c_id)s, %(br_o)s, %(br_f)s, %(br_i)s, %(br_t)s, %(from_date)s, %(to_date)s) "
                        "ON CONFLICT ON CONSTRAINT unique_from_date "
                        "DO UPDATE SET "
                        "burn_rate_operating = %(br_o)s,"
                        "burn_rate_financing = %(br_f)s,"
                        "burn_rate_investing = %(br_i)s,"
                        "burn_rate_total = %(br_t)s,"
                        "to_date = %(to_date)s "
                        "WHERE cash_burn_rate.company_id = %(c_id)s "
                        "AND cash_burn_rate.from_date = %(from_date)s "
                        "AND cash_burn_rate.to_date < %(to_date)s"
                    ),
                    {
                        "c_id": company_id,
                        "br_o": burn_rate_operating,
                        "br_f": burn_rate_financing,
                        "br_i": burn_rate_investing,
                        "br_t": burn_rate_total,
                        "from_date": from_date,
                        "to_date": to_date,
                    },
                )
            except UniqueViolation as e:
                logger.debug(e)
                if (
                    "Unique-Constraint »cash_burn_rate_company_id_from_date_key«"
                    in str(e)
                ):
                    raise e
            except Exception as e:
                raise e
    
    def init_cash_burn_summary(self, company_id):
        '''take the newest cash burn rate and net cash, calc days of cash left and UPSERT into summary'''
        with self.conn() as c:
            net_cash = self.read(
                "SELECT * FROM net_cash_and_equivalents WHERE company_id = %s "
                "ORDER BY instant DESC LIMIT 1", [company_id]
                )[0]
            cash_burn = self.read(
                "SELECT * FROM cash_burn_rate WHERE company_id = %s "
                "ORDER BY to_date DESC LIMIT 1", [company_id]
                )[0]
            days_of_cash_date = datetime.now()
            cash_date = pd.to_datetime(net_cash["instant"]).date()
            burn_rate = cash_burn["burn_rate_total"]
            if burn_rate >= 0:
                days_of_cash = "infinity"
            else:
                abs_br = abs(burn_rate)
                prorated_cash_left = net_cash["amount"] - (abs_br*(datetime.now().date() - cash_date).days)
                if prorated_cash_left < 0:
                    days_of_cash = abs(prorated_cash_left)/burn_rate
                else:
                    days_of_cash = prorated_cash_left/burn_rate
            self.create_cash_burn_summary(
                company_id,
                burn_rate,
                cash_burn["to_date"],
                net_cash["amount"],
                net_cash["instant"],
                round(days_of_cash,2),
                days_of_cash_date
            )                
                

    def init_cash_burn_rate(self, company_id):
        """calculate cash burn rate from db data and UPSERT into cash_burn_rate"""
        operating = self._calc_cash_burn_operating(company_id)
        investing = self._calc_cash_burn_investing(company_id)
        financing = self._calc_cash_burn_financing(company_id)
        # merge the cash burns into one dataframe
        cash_burn = reduce(
            lambda l, r: pd.merge(l, r, on=["from_date", "to_date"], how="outer"),
            [operating, investing, financing],
        )
        # remove overlapping intervals form_date, to_date keeping longest and assure they are date
        cash_burn_cleaned = self._clean_df_cash_burn(cash_burn)
        # write to db
        for r in cash_burn_cleaned.iloc:
            try:
                self.create_cash_burn_rate(
                    company_id,
                    r.burn_rate_operating,
                    r.burn_rate_financing,
                    r.burn_rate_investing,
                    r.burn_rate_total,
                    r.from_date,
                    r.to_date,
                )
            except UniqueViolation as e:
                logger.debug(e)
            except Exception as e:
                logger.debug(e)
                raise e

    def _clean_df_cash_burn(self, cash_burn: pd.DataFrame):
        cash_burn["burn_rate_total"] = cash_burn[
            ["burn_rate_operating", "burn_rate_investing"]
        ].sum(axis=1)
        cleaned_idx = (
            cash_burn.groupby(["from_date"])["to_date"].transform(max)
            == cash_burn["to_date"]
        )
        cash_burn_cleaned = cash_burn[cleaned_idx]
        cash_burn_cleaned["from_date"].apply(lambda x: x.date())
        cash_burn_cleaned["to_date"].apply(lambda x: x.date())
        return cash_burn_cleaned

    def _calculate_df_cash_burn(self, cash_used: pd.DataFrame):
        df = cash_used.copy()
        df["from_date"] = pd.to_datetime(df["from_date"])
        df["to_date"] = pd.to_datetime(df["to_date"])
        df["period"] = (df["to_date"] - df["from_date"]).apply(lambda x: int(x.days))
        df["burn_rate"] = df["amount"] / df["period"]
        return df[["from_date", "to_date", "burn_rate"]]

    def _calc_cash_burn_operating(self, company_id):
        cash_used = self.read(
            "SELECT from_date, to_date, amount FROM cash_operating WHERE company_id = %s",
            [company_id],
        )
        df = pd.DataFrame(cash_used)
        cash_burn = self._calculate_df_cash_burn(df).rename(
            {"burn_rate": "burn_rate_operating"}, axis=1
        )
        return cash_burn

    def _calc_cash_burn_investing(self, company_id):
        cash_used = self.read(
            "SELECT from_date, to_date, amount FROM cash_investing WHERE company_id = %s",
            [company_id],
        )
        df = pd.DataFrame(cash_used)
        cash_burn = self._calculate_df_cash_burn(df).rename(
            {"burn_rate": "burn_rate_investing"}, axis=1
        )
        return cash_burn

    def _calc_cash_burn_financing(self, company_id):
        cash_used = self.read(
            "SELECT from_date, to_date, amount FROM cash_financing WHERE company_id = %s",
            [company_id],
        )
        df = pd.DataFrame(cash_used)
        cash_burn = self._calculate_df_cash_burn(df).rename(
            {"burn_rate": "burn_rate_financing"}, axis=1
        )
        return cash_burn



    # def create_tracked_companies(self):
    #     base_path = config["polygon"]["overview_files_path"]
    #     for ticker in self.tracked_tickers:
    #         company_overview_file_path = path.join(base_path, f"{ticker}.json")
    #         with open(company_overview_file_path, "r") as company:
    #             corp = load(company)
    #             try:
    #                 self.create_company(corp["cik"], corp["sic_code"], ticker, corp["name"], corp["description"])
    #             except UniqueViolation:
    #                 logger.debug("couldnt create {}:company, already present in db.", ticker)
    #                 pass
    #             except Exception as e:
    #                 if "fk_sic" in str(e):
    #                     self.create_sic(corp["sic_code"], "unclassfied", corp["sic_description"], "unclassified")
    #                     self.create_company(corp["cik"], corp["sic_code"], ticker, corp["name"], corp["description"])
    #                 else:
    #                     raise e


if __name__ == "__main__":

    db = DilutionDB(config["dilution_db"]["connectionString"])
    # fake_args1 = [1, 0, 0, 0, 0, "2010-04-01", "2011-02-27"]
    # fake_args2 = [1, 0, 0, 0, 0, "2010-04-01", "2011-04-27"]
    # db.init_cash_burn_summary(1)
    print(db.read("SELECT * FROM cash_burn_summary", []))
    # db.init_cash_burn_rate(1)
    

    # db.create_cash_burn_rate(*fake_args2)
    # with db.conn() as c:
    #     res = c.execute("SELECT * FROM companies JOIN sics ON companies.sic = sics.sic")
    #     for r in res:
    #         print(r)
    # db._delete_all_tables()
    # db._create_tables()
    # db.create_sics()
    # db.create_tracked_companies()
