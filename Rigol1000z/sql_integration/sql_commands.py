# From answer found at:
# https://stackoverflow.com/questions/18621513/python-insert-numpy-array-into-sqlite3-database

import sqlite3

import io
from typing import Set, List, Tuple, Dict
import time
from datetime import datetime

# Remote libraries
import numpy as np  # type: ignore

DB_PATH = f"./response_data.db"

# Define table names
CAPTURE_TABLE = "capture"
WAVEFORM_TABLE = "waveform"


class DBInterface:
    def __init__(self):
        self.connection = sqlite3.connect(
            database=DB_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )

    def __del__(self):
        self.connection.close()

    def ensure_database_initialized(self):
        c = self.connection.cursor()

        # Create table if first measurement
        c.execute('''
        CREATE TABLE IF NOT EXISTS {0}
        (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            description         TEXT, 
            capture_period      REAL,
            capture_datetime    TIMESTAMP         
        )
        '''.format(CAPTURE_TABLE))

        # Create table if first measurement
        c.execute('''
        CREATE TABLE IF NOT EXISTS {0}
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_capture      INTEGER,
            channel_name        TEXT,
            vertical_offset      INTEGER,
            vertical_scale       TEXT,
            description         TEXT,
            wf                  BLOB,
            FOREIGN KEY(fk_capture) REFERENCES {1}(id)
        )
        '''.format(
            WAVEFORM_TABLE,
            CAPTURE_TABLE
        ))

        self.connection.commit()

    def write_capture_to_db(self, capture_period: float, capture_datetime: datetime, capture_description: str = ""):
        """
        Basic description of function
        for more info on numpy function docs read: https://numpydoc.readthedocs.io/en/latest/format.html

        Parameters
        ----------
         :
            Description of parameter ''
         :
            Description of parameter ''

        Returns
        -------

            Description of return value
        """

        c = self.connection.cursor()

        c.execute(
            '''
            insert into {0}
            (
                description,
                capture_period,
                capture_datetime
            ) values
                (?,?,?)
            '''.format(
                CAPTURE_TABLE
            ),
            (
                capture_description,
                capture_period,
                capture_datetime
            )
        )
        inserted_item = c.lastrowid
        self.connection.commit()

        return inserted_item

    def write_waveform_to_db(
            self,
            measurement_fk: int,
            wf: bytes,
            channel_name: str,
            vertical_offset: int,
            vertical_scale: str,
            description: str
    ):
        """
        Basic description of function
        for more info on numpy function docs read: https://numpydoc.readthedocs.io/en/latest/format.html

        Parameters
        ----------
         :
            Description of parameter ''
         :
            Description of parameter ''

        Returns
        -------

            Description of return value
        """

        c = self.connection.cursor()

        c.execute(
            '''
            insert into {0}(
                fk_capture,
                wf,
                channel_name,
                vertical_offset,
                vertical_scale,
                description
            )values (?,?,?,?,?,?)
            '''.format(WAVEFORM_TABLE),
            (
                measurement_fk,
                wf,
                channel_name,
                vertical_offset,
                vertical_scale,
                description,
            )
        )
        inserted_item = c.lastrowid
        self.connection.commit()

        return inserted_item

    def get_capture_from_id(self, capture_id: int) -> Tuple[float, str, datetime]:
        c = self.connection.cursor()

        c.execute(
            f"select "
            f"capture_period, description, capture_datetime "
            f"from {CAPTURE_TABLE} "
            f"where id=?",
            (capture_id,)
        )
        return c.fetchone()

    def get_waveforms_from_capture(self, capture_id: int) -> List[Tuple[int, str, int, str, str, bytes]]:
        c = self.connection.cursor()

        c.execute(
            f"select "
            f"w.id, w.channel_name, w.vertical_offset, w.vertical_scale, w.description, w.wf "
            f"from "
            f"{CAPTURE_TABLE} c, {WAVEFORM_TABLE} w "
            f"where "
            f"(w.fk_capture=c.id) and (c.id=?)",
            (capture_id,)
        )
        return c.fetchall()

    def get_all_captures_with_description(self):
        pass


# def get_all_freq_inps() -> Set[str]:
#    with sqlite3.connect(db_Name) as conn:
#        c = conn.cursor()
#
#        c.execute("select DISTINCT inp_freq from measurements")
#        return {v[0] for v in c.fetchall()}
#
#
# def get_all_measurement_ids_at_freq_inp(freq_inp: str) -> Set[int]:
#    with sqlite3.connect(db_Name) as conn:
#        c = conn.cursor()
#
#        c.execute("select id from measurements where inp_freq=?", (str(freq_inp),))
#        return {v[0] for v in c.fetchall()}
#
#
# def get_measurement_with_id(measurement_id: int):
#    with sqlite3.connect(db_Name) as conn:
#        c = conn.cursor()
#
#        c.execute("select capture_period, inp_wf, out_wf from measurements where id=?", (measurement_id,))
#        return c.fetchone()


db = DBInterface()
db.ensure_database_initialized()
