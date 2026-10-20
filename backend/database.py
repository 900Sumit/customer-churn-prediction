import json
import logging
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

logger = logging.getLogger("churnlab.db")

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # Keeps the existing prediction API importable before install.
    psycopg = None
    dict_row = None

try:
    from psycopg_pool import ConnectionPool
except ImportError:
    ConnectionPool = None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS prediction_history (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source TEXT NOT NULL DEFAULT 'single',
    input_data JSONB NOT NULL,
    result_data JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS prediction_history_user_created_idx
    ON prediction_history (user_id, created_at DESC);
"""

# ---------------------------------------------------------------------------
# Connection configuration
# ---------------------------------------------------------------------------

_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 2.0


def database_url():
    return os.getenv("DATABASE_URL", "").strip()


def ssl_database_url(url):
    """Require TLS without changing credentials or an already-secure mode."""
    ssl_match = re.search(r"([?&])sslmode=([^&]*)", url, flags=re.IGNORECASE)
    if ssl_match:
        ssl_mode = ssl_match.group(2).lower()
        if ssl_mode in {"require", "verify-ca", "verify-full"}:
            return url
        return url[:ssl_match.start(2)] + "require" + url[ssl_match.end(2):]

    separator = "&" if "?" in url else "?"
    return f"{url}{separator}sslmode=require"


def is_configured():
    return bool(database_url()) and psycopg is not None


# ---------------------------------------------------------------------------
# Connection pool (lazy singleton)
# ---------------------------------------------------------------------------

_pool = None


def _get_pool():
    """Return the shared connection pool, creating it on first call."""
    global _pool
    if _pool is not None:
        return _pool

    if not is_configured():
        return None

    conninfo = ssl_database_url(database_url())

    if ConnectionPool is not None:
        _pool = ConnectionPool(
            conninfo=conninfo,
            min_size=1,
            max_size=10,
            timeout=15.0,
            open=True,
            kwargs={"row_factory": dict_row},
        )
        logger.info("database_pool_created min=1 max=10")
    else:
        # psycopg_pool not installed — fall back to direct connections
        logger.info("database_pool_unavailable using_direct_connections=true")

    return _pool


def close_pool():
    """Shut down the pool cleanly (call on app shutdown)."""
    global _pool
    if _pool is not None and ConnectionPool is not None:
        try:
            _pool.close(timeout=3.0)
        except Exception:
            pass
        _pool = None


import atexit
atexit.register(close_pool)


@contextmanager
def connection():
    """Yield a database connection with cold-start retry.

    Uses the connection pool when available; falls back to a direct
    psycopg.connect when psycopg_pool is not installed.
    """
    if psycopg is None:
        raise RuntimeError("psycopg is not installed. Run pip install -r requirements.txt.")
    url = database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not configured in backend/.env or the process environment.")

    pool = _get_pool()

    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            if pool is not None:
                with pool.connection() as conn:
                    yield conn
                    return
            else:
                with psycopg.connect(ssl_database_url(url), row_factory=dict_row) as conn:
                    yield conn
                    return
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                logger.warning(
                    "database_connection_retry attempt=%d delay=%.1fs error=%s",
                    attempt + 1, _RETRY_DELAY_SECONDS, type(exc).__name__,
                )
                time.sleep(_RETRY_DELAY_SECONDS)

    # All retries exhausted
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Schema and health
# ---------------------------------------------------------------------------

def test_connection():
    """Open the configured database and execute a minimal query."""
    with connection() as conn:
        conn.execute("SELECT 1").fetchone()
    return True


def initialize_schema():
    if not database_url():
        return False
    with connection() as conn:
        conn.execute(SCHEMA_SQL)
        conn.commit()
    return True


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def save_prediction(user_id, input_data, result_data, source="single"):
    with connection() as conn:
        row = conn.execute(
            """
            INSERT INTO prediction_history (user_id, source, input_data, result_data)
            VALUES (%s, %s, %s::jsonb, %s::jsonb)
            RETURNING id, created_at
            """,
            (user_id, source, json.dumps(input_data), json.dumps(result_data)),
        ).fetchone()
        conn.commit()
        return row


def save_predictions(user_id, records, source="csv"):
    """Persist a batch in one TLS connection and transaction."""
    if not records:
        return 0

    with connection() as conn:
        # psycopg3 exposes executemany() on cursors, not connections.
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO prediction_history (user_id, source, input_data, result_data)
                VALUES (%s, %s, %s::jsonb, %s::jsonb)
                """,
                [
                    (user_id, source, json.dumps(input_data), json.dumps(result_data))
                    for input_data, result_data in records
                ],
            )
        conn.commit()
    return len(records)


# ---------------------------------------------------------------------------
# Read operations — all queries are scoped to user_id
# ---------------------------------------------------------------------------

def _history_filters(user_id, query=None, risk=None, prediction=None, source=None, date_from=None, date_to=None):
    clauses = ["user_id = %s"]
    values = [user_id]

    if query:
        pattern = f"%{query}%"
        clauses.append("(input_data::text ILIKE %s OR result_data::text ILIKE %s OR source ILIKE %s)")
        values.extend([pattern, pattern, pattern])
    if risk:
        clauses.append("result_data->>'Risk_Level' = %s")
        values.append(risk)
    if prediction:
        clauses.append("result_data->>'Ensemble_Prediction' = %s")
        values.append(prediction)
    if source:
        clauses.append("source = %s")
        values.append(source)
    if date_from:
        clauses.append("created_at >= %s::date")
        values.append(date_from)
    if date_to:
        clauses.append("created_at < (%s::date + INTERVAL '1 day')")
        values.append(date_to)

    return " AND ".join(clauses), values


def list_predictions(user_id, limit=100, offset=0, query=None, risk=None, prediction=None, source=None, date_from=None, date_to=None):
    where_sql, values = _history_filters(user_id, query, risk, prediction, source, date_from, date_to)
    with connection() as conn:
        return conn.execute(
            f"""
            SELECT id, created_at, source, input_data, result_data
            FROM prediction_history
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            [*values, limit, offset],
        ).fetchall()


def count_predictions(user_id, query=None, risk=None, prediction=None, source=None, date_from=None, date_to=None):
    where_sql, values = _history_filters(user_id, query, risk, prediction, source, date_from, date_to)
    with connection() as conn:
        return conn.execute(
            f"SELECT COUNT(*) AS total FROM prediction_history WHERE {where_sql}",
            values,
        ).fetchone()["total"]


def aggregate_predictions(user_id):
    with connection() as conn:
        summary = conn.execute(
            """
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE result_data->>'Ensemble_Prediction' = 'Churn')::int AS churn,
                COUNT(*) FILTER (WHERE result_data->>'Ensemble_Prediction' = 'No Churn')::int AS non_churn,
                COALESCE(AVG((result_data->>'Ensemble_Churn_Probability')::numeric), 0)::float AS average_probability
            FROM prediction_history
            WHERE user_id = %s
            """,
            (user_id,),
        ).fetchone()

        risk_distribution = conn.execute(
            """
            SELECT result_data->>'Risk_Level' AS risk_level, COUNT(*)::int AS count
            FROM prediction_history
            WHERE user_id = %s
            GROUP BY result_data->>'Risk_Level'
            ORDER BY result_data->>'Risk_Level'
            """,
            (user_id,),
        ).fetchall()

        date_trends = conn.execute(
            """
            SELECT created_at::date::text AS date,
                   COUNT(*)::int AS total,
                   COUNT(*) FILTER (WHERE result_data->>'Ensemble_Prediction' = 'Churn')::int AS churn,
                   COUNT(*) FILTER (WHERE result_data->>'Ensemble_Prediction' = 'No Churn')::int AS non_churn
            FROM prediction_history
            WHERE user_id = %s
            GROUP BY created_at::date
            ORDER BY created_at::date
            """,
            (user_id,),
        ).fetchall()

        segment_analysis = conn.execute(
            """
            SELECT COALESCE(input_data->>'Contract', 'Unknown') AS segment,
                   COUNT(*)::int AS total,
                   COUNT(*) FILTER (WHERE result_data->>'Ensemble_Prediction' = 'Churn')::int AS churn,
                   COALESCE(AVG((result_data->>'Ensemble_Churn_Probability')::numeric), 0)::float AS average_probability
            FROM prediction_history
            WHERE user_id = %s
            GROUP BY COALESCE(input_data->>'Contract', 'Unknown')
            ORDER BY total DESC, segment
            """,
            (user_id,),
        ).fetchall()

        source_distribution = conn.execute(
            """
            SELECT source, COUNT(*)::int AS count
            FROM prediction_history
            WHERE user_id = %s
            GROUP BY source
            ORDER BY source
            """,
            (user_id,),
        ).fetchall()

        return {
            **summary,
            "risk_distribution": risk_distribution,
            "date_trends": date_trends,
            "segment_analysis": segment_analysis,
            "source_distribution": source_distribution,
        }
