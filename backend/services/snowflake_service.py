"""
Snowflake database service for connections and operations
"""
import os
import snowflake.connector
from flask import current_app, g
from logging import getLogger

logger = getLogger(__name__)

def get_snowflake_connection():
    """
    Establishes a connection to Snowflake or returns the existing connection from the application context.
    """
    if 'snowflake_conn' not in g:
        try:
            g.snowflake_conn = snowflake.connector.connect(
                user=current_app.config['SNOWFLAKE_USER'],
                password=current_app.config['SNOWFLAKE_PASSWORD'],
                account=current_app.config['SNOWFLAKE_ACCOUNT'],
                warehouse=current_app.config['SNOWFLAKE_WAREHOUSE'],
                database=current_app.config['SNOWFLAKE_DATABASE'],
                schema=current_app.config['SNOWFLAKE_SCHEMA']
            )
        except snowflake.connector.Error as e:
            logger.error(f"Snowflake connection error: {e}")
            raise e
    return g.snowflake_conn

def close_snowflake_connection(e=None):
    """
    Closes the Snowflake connection at the end of the request.
    """
    conn = g.pop('snowflake_conn', None)
    if conn is not None:
        conn.close()

def init_app(app):
    """
    Register the teardown function with the Flask app.
    """
    app.teardown_appcontext(close_snowflake_connection)

def get_inventory_history():
    """
    Fetches inventory history from Snowflake.
    """
    conn = get_snowflake_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT RECORD_ID, PRODUCT_ID, STOCK_LEVEL, SNAPSHOT_DATE::string as snapshot_date, REORDER_THRESHOLD FROM AWSHACK725.PUBLIC.INVENTORY_HISTORY;")
        rows = cur.fetchall()
        # Convert to list of dicts
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows] 