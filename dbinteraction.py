import sqlite3
from sqlite3 import Error
import pprint

def dbexec(query, arg=None, f=True, db="db/store.db", mult=False):
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        if arg:
            c.execute(query, arg)
        else:
            c.execute(query)
        
        if f:
            az=None
            if mult:
                az = c.fetchall()
            else:
                az = c.fetchone()
                az=az[0]
            if az!=None:
                return(az)
            else:
                return None

    except Error as e:
        print("\033[91mUne erreur est survenue pendant la gestion de la requête SQL: {}\033[0m".format(e))
        return "err"
    finally:
        conn.commit()
        conn.close()