import sqlite3

import io
from typing import Set, List, Tuple, Dict
import time
from datetime import datetime

# Remote libraries
import numpy as np  # type: ignore

DB_PATH = f"./response_data.db"

# Define table names
PROJECT_TABLE = "project"
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

        # Create capture table
        c.execute('''
        CREATE TABLE IF NOT EXISTS {0}
        (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT,
            description         TEXT    
        )
        '''.format(PROJECT_TABLE))

        # region unique_keys

        c.execute(
            f'insert or replace into {PROJECT_TABLE} (id, name, description) values (?,?,?)',
            (-1, "UNASSIGNED_PROJECT",
             "This is the default project that gets assigned to projects that don't have a project assigned.")
        )

        c.execute(
            f'insert or replace into {PROJECT_TABLE} (id, name, description) values (?,?,?)',
            (-2, "TESTING_PROJECT", "This is the project that captures used in tests should be attached to.")
        )

        # endregion

        # Create capture table
        c.execute('''
        CREATE TABLE IF NOT EXISTS {0}
        (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            description         TEXT, 
            capture_period      REAL,
            capture_datetime    TIMESTAMP,
            fk_project          INTEGER,
            FOREIGN KEY(fk_project) REFERENCES {1}(id)
        )
        '''.format(CAPTURE_TABLE, PROJECT_TABLE))

        # Create waveform table
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

    # region capture read and writes

    def write_capture_to_db(
            self,
            capture_period: float,
            capture_datetime: datetime,
            capture_description: str = "",
            part_of_project: int = -1
    )->int:
        c = self.connection.cursor()

        c.execute(
            '''
            insert into {0}
            (
                description,
                capture_period,
                capture_datetime,
                fk_project
            ) values
                (?,?,?,?)
            '''.format(
                CAPTURE_TABLE
            ),
            (
                capture_description,
                capture_period,
                capture_datetime,
                part_of_project
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

    # endregion
    # region waveform read and writes
    def write_waveform_to_db(
            self,
            measurement_fk: int,
            wf: bytes,
            channel_name: str,
            vertical_offset: int,
            vertical_scale: str,
            description: str
    ):
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

    def get_waveform_from_id(self, waveform_id: int) -> Tuple[str, int, str, str, bytes]:
        c = self.connection.cursor()

        c.execute(
            f"select "
            f"channel_name, vertical_offset, vertical_scale, description, wf "
            f"from {WAVEFORM_TABLE} "
            f"where id=?",
            (waveform_id,)
        )
        return c.fetchone()

    def get_waveforms_from_capture_id(self, capture_id: int) -> List[Tuple[int, str, int, str, str, bytes]]:
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

    # endregion


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
